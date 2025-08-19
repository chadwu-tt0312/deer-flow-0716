# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
基於 Ledger 的工作流編排器

參考 AutoGen Magentic One 的 LedgerOrchestrator 實現，
提供智能的工作流編排和智能體選擇機制。
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..config.agent_config import AgentRole, WorkflowConfig
from ..agents.base_agent import BaseResearchAgent
from src.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LedgerEntry:
    """Ledger 條目，用於追蹤工作流狀態"""

    timestamp: datetime
    is_request_satisfied: bool
    is_in_loop: bool
    is_progress_being_made: bool
    next_speaker: str
    instruction_or_question: str
    reasoning: str = ""
    current_step: str = ""
    completed_steps: List[str] = field(default_factory=list)
    facts_learned: List[str] = field(default_factory=list)


class LedgerOrchestrator:
    """
    基於 Ledger 的研究工作流編排器

    參考 AutoGen Magentic One 的設計模式，使用 JSON 格式的 Ledger
    來追蹤任務進度並選擇下一個發言的智能體。
    """

    # Prompt 模板
    SYSTEM_MESSAGE = """你是一個智能的工作流編排器，負責協調多個智能體完成研究任務。

你的職責：
1. 分析當前任務進度和對話歷史
2. 判斷任務是否完成或遇到問題
3. 選擇下一個最適合的智能體
4. 提供清晰的指令或問題

你必須以 JSON 格式回應，包含以下欄位：
- is_request_satisfied: 任務是否已完成 (boolean)
- is_in_loop: 是否陷入循環 (boolean) 
- is_progress_being_made: 是否有進展 (boolean)
- next_speaker: 下一個發言者名稱 (string)
- instruction_or_question: 給下一個發言者的指令或問題 (string)
- reasoning: 決策理由 (string)
- current_step: 當前執行步驟 (string)
- completed_steps: 已完成步驟列表 (array)
- facts_learned: 已學到的事實列表 (array)"""

    LEDGER_PROMPT = """# 任務分析和智能體選擇

## 當前任務
{task}

## 可用智能體團隊
{team_description}

## 對話歷史
{conversation_history}

請分析當前狀況並決定下一步行動。考慮：
1. 任務是否已經完成？
2. 是否陷入重複循環？
3. 是否在取得進展？
4. 哪個智能體最適合處理下一步？
5. 應該給該智能體什麼具體指令？

智能體名稱選項：{agent_names}

回應格式：JSON"""

    PLAN_PROMPT = """# 制定執行計劃

## 任務
{task}

## 可用智能體
{team_description}

## 已知事實
{facts}

請為這個任務制定一個詳細的執行計劃。計劃應該：
1. 分解任務為具體步驟
2. 指定每個步驟的負責智能體
3. 考慮步驟間的依賴關係
4. 預估完成時間

回應格式：文字描述"""

    FACTS_UPDATE_PROMPT = """# 更新事實資訊

## 原始任務
{task}

## 目前已知事實
{current_facts}

## 最新對話內容
{recent_conversation}

基於最新的對話內容，請更新和補充已知事實。只包含確實可靠的資訊。

回應格式：文字描述"""

    def __init__(
        self,
        config: WorkflowConfig,
        agents: Dict[str, BaseResearchAgent],
        max_rounds: int = 20,
        max_stalls_before_replan: int = 3,
        max_replans: int = 3,
    ):
        """
        初始化編排器

        Args:
            config: 工作流配置
            agents: 智能體字典
            max_rounds: 最大輪數
            max_stalls_before_replan: 重新規劃前的最大停滯次數
            max_replans: 最大重新規劃次數
        """
        self.config = config
        self.agents = agents
        self.max_rounds = max_rounds
        self.max_stalls_before_replan = max_stalls_before_replan
        self.max_replans = max_replans

        # 狀態追蹤
        self.task = ""
        self.facts = ""
        self.plan = ""
        self.conversation_history: List[Dict[str, Any]] = []
        self.ledger_history: List[LedgerEntry] = []

        # 控制變數
        self.round_count = 0
        self.stall_counter = 0
        self.replan_counter = 0
        self.should_replan = False

        logger.info(f"初始化 LedgerOrchestrator: {config.name}")

    def get_team_description(self) -> str:
        """取得團隊描述"""
        descriptions = []
        for agent_name, agent in self.agents.items():
            role_info = agent.get_role_info()
            descriptions.append(f"{agent_name}: {role_info['description']}")
        return "\n".join(descriptions)

    def get_agent_names(self) -> List[str]:
        """取得智能體名稱列表"""
        return list(self.agents.keys())

    def add_conversation_message(self, sender: str, content: str, message_type: str = "message"):
        """添加對話消息"""
        message = {
            "timestamp": datetime.now(),
            "sender": sender,
            "content": content,
            "type": message_type,
        }
        self.conversation_history.append(message)

    def get_recent_conversation(self, last_n: int = 5) -> str:
        """取得最近的對話內容"""
        recent_messages = (
            self.conversation_history[-last_n:]
            if len(self.conversation_history) > last_n
            else self.conversation_history
        )

        formatted_messages = []
        for msg in recent_messages:
            formatted_messages.append(f"[{msg['sender']}]: {msg['content']}")

        return "\n".join(formatted_messages)

    async def initialize_task(self, task: str):
        """初始化任務"""
        self.task = task
        logger.info(f"初始化任務: {task}")

        # 收集初始事實
        self.facts = await self._gather_initial_facts(task)

        # 制定初始計劃
        self.plan = await self._create_initial_plan(task)

        # 記錄初始狀態
        self.add_conversation_message("Orchestrator", f"任務: {task}", "task_init")
        self.add_conversation_message("Orchestrator", f"初始事實: {self.facts}", "facts")
        self.add_conversation_message("Orchestrator", f"執行計劃: {self.plan}", "plan")

        logger.info("任務初始化完成")

    async def _gather_initial_facts(self, task: str) -> str:
        """收集初始事實（簡化版本）"""
        # 在實際實現中，這裡會調用 LLM 來分析任務並收集事實
        # 現在先返回基本的任務分析
        return f"任務分析: {task}\n需要進行研究和分析工作。"

    async def _create_initial_plan(self, task: str) -> str:
        """創建初始計劃（簡化版本）"""
        # 在實際實現中，這裡會調用 LLM 生成詳細計劃
        return f"""執行計劃:
1. 協調者分析任務需求
2. 計劃者制定詳細執行步驟  
3. 研究者收集相關資訊
4. 程式設計師執行技術分析（如需要）
5. 報告者整理並生成最終報告"""

    async def update_ledger(self) -> LedgerEntry:
        """更新 Ledger 狀態"""
        max_retries = 3

        # 準備 prompt
        team_description = self.get_team_description()
        agent_names = self.get_agent_names()
        conversation_history = self.get_recent_conversation(10)

        ledger_prompt = self.LEDGER_PROMPT.format(
            task=self.task,
            team_description=team_description,
            conversation_history=conversation_history,
            agent_names=agent_names,
        )

        # 模擬 LLM 調用（實際實現需要真正的 LLM）
        # 這裡提供一個基於規則的簡化版本
        ledger_data = await self._simulate_ledger_analysis()

        # 創建 LedgerEntry
        ledger_entry = LedgerEntry(
            timestamp=datetime.now(),
            is_request_satisfied=ledger_data["is_request_satisfied"],
            is_in_loop=ledger_data["is_in_loop"],
            is_progress_being_made=ledger_data["is_progress_being_made"],
            next_speaker=ledger_data["next_speaker"],
            instruction_or_question=ledger_data["instruction_or_question"],
            reasoning=ledger_data.get("reasoning", ""),
            current_step=ledger_data.get("current_step", ""),
            completed_steps=ledger_data.get("completed_steps", []),
            facts_learned=ledger_data.get("facts_learned", []),
        )

        self.ledger_history.append(ledger_entry)
        logger.info(
            f"Ledger 更新: {ledger_entry.next_speaker} - {ledger_entry.instruction_or_question}"
        )

        return ledger_entry

    async def _simulate_ledger_analysis(self) -> Dict[str, Any]:
        """模擬 Ledger 分析（簡化版本）"""
        # 這是一個基於規則的簡化實現
        # 實際版本會使用 LLM 進行智能分析

        # 檢查對話歷史決定下一步
        if len(self.conversation_history) <= 3:
            # 初始階段，從協調開始
            return {
                "is_request_satisfied": False,
                "is_in_loop": False,
                "is_progress_being_made": True,
                "next_speaker": "CoordinatorAgent",
                "instruction_or_question": f"請分析以下研究任務並確定執行方向: {self.task}",
                "reasoning": "任務剛開始，需要協調者進行初始分析",
                "current_step": "任務協調",
                "completed_steps": [],
                "facts_learned": [],
            }

        # 檢查最近的消息確定下一步
        last_message = self.conversation_history[-1]
        last_sender = last_message["sender"]

        if last_sender == "CoordinatorAgent":
            return {
                "is_request_satisfied": False,
                "is_in_loop": False,
                "is_progress_being_made": True,
                "next_speaker": "PlannerAgent",
                "instruction_or_question": "基於協調者的分析，請制定詳細的執行計劃",
                "reasoning": "協調完成，需要制定具體計劃",
                "current_step": "計劃制定",
                "completed_steps": ["任務協調"],
                "facts_learned": ["任務需求已分析"],
            }

        elif last_sender == "PlannerAgent":
            return {
                "is_request_satisfied": False,
                "is_in_loop": False,
                "is_progress_being_made": True,
                "next_speaker": "ResearcherAgent",
                "instruction_or_question": "請根據計劃開始收集相關資訊和進行研究",
                "reasoning": "計劃已制定，需要開始實際研究工作",
                "current_step": "資訊收集",
                "completed_steps": ["任務協調", "計劃制定"],
                "facts_learned": ["任務需求已分析", "執行計劃已制定"],
            }

        elif last_sender == "ResearcherAgent":
            # 檢查是否需要程式碼分析
            if "程式" in self.task or "代碼" in self.task or "code" in self.task.lower():
                return {
                    "is_request_satisfied": False,
                    "is_in_loop": False,
                    "is_progress_being_made": True,
                    "next_speaker": "CoderAgent",
                    "instruction_or_question": "請對相關程式碼進行分析和處理",
                    "reasoning": "任務涉及程式碼，需要技術分析",
                    "current_step": "程式碼分析",
                    "completed_steps": ["任務協調", "計劃制定", "資訊收集"],
                    "facts_learned": ["任務需求已分析", "執行計劃已制定", "研究資料已收集"],
                }
            else:
                return {
                    "is_request_satisfied": False,
                    "is_in_loop": False,
                    "is_progress_being_made": True,
                    "next_speaker": "ReporterAgent",
                    "instruction_or_question": "請基於收集的資訊生成最終報告",
                    "reasoning": "研究完成，可以生成報告",
                    "current_step": "報告生成",
                    "completed_steps": ["任務協調", "計劃制定", "資訊收集"],
                    "facts_learned": ["任務需求已分析", "執行計劃已制定", "研究資料已收集"],
                }

        elif last_sender == "CoderAgent":
            return {
                "is_request_satisfied": False,
                "is_in_loop": False,
                "is_progress_being_made": True,
                "next_speaker": "ReporterAgent",
                "instruction_or_question": "請整合研究結果和程式碼分析，生成最終報告",
                "reasoning": "技術分析完成，需要生成綜合報告",
                "current_step": "報告生成",
                "completed_steps": ["任務協調", "計劃制定", "資訊收集", "程式碼分析"],
                "facts_learned": [
                    "任務需求已分析",
                    "執行計劃已制定",
                    "研究資料已收集",
                    "程式碼已分析",
                ],
            }

        elif last_sender == "ReporterAgent":
            return {
                "is_request_satisfied": True,
                "is_in_loop": False,
                "is_progress_being_made": True,
                "next_speaker": "",
                "instruction_or_question": "任務已完成",
                "reasoning": "報告已生成，任務完成",
                "current_step": "任務完成",
                "completed_steps": ["任務協調", "計劃制定", "資訊收集", "程式碼分析", "報告生成"],
                "facts_learned": [
                    "任務需求已分析",
                    "執行計劃已制定",
                    "研究資料已收集",
                    "程式碼已分析",
                    "最終報告已生成",
                ],
            }

        # 預設情況
        return {
            "is_request_satisfied": False,
            "is_in_loop": False,
            "is_progress_being_made": True,
            "next_speaker": "CoordinatorAgent",
            "instruction_or_question": "請繼續協調任務進展",
            "reasoning": "需要協調者介入",
            "current_step": "協調中",
            "completed_steps": [],
            "facts_learned": [],
        }

    async def select_next_agent(self) -> Optional[BaseResearchAgent]:
        """選擇下一個智能體"""
        self.round_count += 1

        # 檢查輪數限制
        if self.round_count > self.max_rounds:
            logger.warning("達到最大輪數限制")
            return None

        # 更新 Ledger
        ledger_entry = await self.update_ledger()

        # 任務完成
        if ledger_entry.is_request_satisfied:
            logger.info("任務已完成")
            return None

        # 檢查是否停滯或循環
        if ledger_entry.is_in_loop or not ledger_entry.is_progress_being_made:
            self.stall_counter += 1

            if self.stall_counter > self.max_stalls_before_replan:
                await self._handle_replan()
                return await self.select_next_agent()  # 重新選擇
        else:
            self.stall_counter = 0  # 重置停滯計數器

        # 選擇下一個智能體
        next_agent_name = ledger_entry.next_speaker
        if next_agent_name in self.agents:
            next_agent = self.agents[next_agent_name]

            # 記錄指令
            self.add_conversation_message(
                "Orchestrator",
                f"指令給 {next_agent_name}: {ledger_entry.instruction_or_question}",
                "instruction",
            )

            return next_agent

        logger.warning(f"找不到智能體: {next_agent_name}")
        return None

    async def _handle_replan(self):
        """處理重新規劃"""
        self.replan_counter += 1

        if self.replan_counter > self.max_replans:
            logger.warning("超過最大重新規劃次數，終止任務")
            return

        logger.info(f"第 {self.replan_counter} 次重新規劃")

        # 更新事實和計劃
        await self._update_facts_and_plan()

        # 重置狀態
        self.stall_counter = 0

        # 記錄重新規劃
        self.add_conversation_message("Orchestrator", f"重新規劃 #{self.replan_counter}", "replan")
        self.add_conversation_message("Orchestrator", f"更新後的計劃: {self.plan}", "plan")

    async def _update_facts_and_plan(self):
        """更新事實和計劃"""
        # 更新事實
        recent_conversation = self.get_recent_conversation(10)
        # 這裡應該調用 LLM 更新事實，現在簡化處理
        self.facts += f"\n更新的事實（基於最新對話）: {recent_conversation}"

        # 更新計劃
        # 這裡應該調用 LLM 重新制定計劃，現在簡化處理
        self.plan += f"\n更新的計劃（第 {self.replan_counter} 次修正）"

    def get_status(self) -> Dict[str, Any]:
        """取得當前狀態"""
        latest_ledger = self.ledger_history[-1] if self.ledger_history else None

        return {
            "task": self.task,
            "round_count": self.round_count,
            "max_rounds": self.max_rounds,
            "stall_counter": self.stall_counter,
            "replan_counter": self.replan_counter,
            "latest_ledger": {
                "is_request_satisfied": latest_ledger.is_request_satisfied
                if latest_ledger
                else False,
                "next_speaker": latest_ledger.next_speaker if latest_ledger else "",
                "current_step": latest_ledger.current_step if latest_ledger else "",
                "completed_steps": latest_ledger.completed_steps if latest_ledger else [],
            }
            if latest_ledger
            else None,
            "conversation_length": len(self.conversation_history),
        }
