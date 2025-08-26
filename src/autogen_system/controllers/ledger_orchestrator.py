# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
基於 Ledger 的工作流編排器 - 整合版本

參考 AutoGen Magentic One 的 LedgerOrchestrator 實現，
提供智能的工作流編排和智能體選擇機制。
支持 AutoGen 框架和模板檔案。
"""

import json
import asyncio
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

# AutoGen 核心模型
try:
    from autogen_core.models import (
        SystemMessage,
        UserMessage,
        AssistantMessage,
        LLMMessage,
        ChatCompletionClient,
    )
    from autogen_core import CancellationToken
    from autogen_agentchat.messages import TextMessage
    from autogen_agentchat.agents import BaseChatAgent

    HAS_AUTOGEN = True
except ImportError:
    # 降級到基本類型
    ChatCompletionClient = type("MockChatCompletionClient", (), {})
    CancellationToken = type("MockCancellationToken", (), {})
    TextMessage = type("MockTextMessage", (), {})
    BaseChatAgent = type("MockBaseChatAgent", (), {})
    HAS_AUTOGEN = False

from ..config.agent_config import AgentRole, WorkflowConfig
from ..agents.base_agent import BaseResearchAgent
from src.logging import get_logger
from src.prompts.template import env

# 嘗試導入線程管理功能
try:
    from src.logging import (
        setup_thread_logging,
        set_thread_context,
        get_current_thread_id,
        get_current_thread_logger,
    )

    HAS_THREAD_LOGGING = True
except ImportError:
    HAS_THREAD_LOGGING = False

# 嘗試導入配置功能
try:
    from src.config.configuration import Configuration

    HAS_CONFIGURATION = True
except ImportError:
    HAS_CONFIGURATION = False

# 導入 Command 系統
try:
    from ..core.command import AutoGenCommand, CommandHandler, parse_flow_control_to_command

    HAS_COMMAND_SYSTEM = True
except ImportError:
    HAS_COMMAND_SYSTEM = False

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

    # AutoGen 特定字段
    flow_control_info: Dict[str, Any] = field(default_factory=dict)
    message_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """工作流執行結果"""

    success: bool
    final_message: Optional[Union[str, TextMessage]] = None
    error_message: str = ""
    total_rounds: int = 0
    completed_steps: List[str] = field(default_factory=list)
    facts_learned: List[str] = field(default_factory=list)


class LedgerOrchestrator:
    """
    基於 Ledger 的研究工作流編排器 - 整合版本

    參考 AutoGen Magentic One 的設計模式，使用 JSON 格式的 Ledger
    來追蹤任務進度並選擇下一個發言的智能體。
    支持 AutoGen 框架和模板檔案。
    """

    def _get_system_message_template(self) -> str:
        """取得系統消息模板"""
        template = env.get_template("ledger_orchestrator.md")
        return template.render(CURRENT_TIME=datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"))

    def _apply_ledger_template(self, **kwargs) -> str:
        """應用 Ledger 分析模板"""
        try:
            template = env.get_template("ledger_orchestrator.md")
            # 從模板中提取 Ledger Analysis 部分
            full_template = template.render(
                CURRENT_TIME=datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"), **kwargs
            )

            # 提取 Ledger Analysis Template 部分
            lines = full_template.split("\n")
            in_ledger_section = False
            ledger_lines = []

            for line in lines:
                if "## Ledger Analysis Template" in line:
                    in_ledger_section = True
                    continue
                elif in_ledger_section and line.startswith("## ") and "Ledger Analysis" not in line:
                    break
                elif in_ledger_section:
                    ledger_lines.append(line)

            return "\n".join(ledger_lines)
        except Exception as e:
            raise ValueError(f"應用 ledger 模板失敗: {e}")

    def _apply_plan_template(self, **kwargs) -> str:
        """應用計劃創建模板"""
        try:
            template = env.get_template("ledger_orchestrator.md")
            full_template = template.render(
                CURRENT_TIME=datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"), **kwargs
            )

            # 提取 Plan Creation Template 部分
            lines = full_template.split("\n")
            in_plan_section = False
            plan_lines = []

            for line in lines:
                if "## Plan Creation Template" in line:
                    in_plan_section = True
                    continue
                elif in_plan_section and line.startswith("## ") and "Plan Creation" not in line:
                    break
                elif in_plan_section:
                    plan_lines.append(line)

            return "\n".join(plan_lines)
        except Exception as e:
            raise ValueError(f"應用計劃模板失敗: {e}")

    def _apply_facts_update_template(self, **kwargs) -> str:
        """應用事實更新模板"""
        try:
            template = env.get_template("ledger_orchestrator.md")
            full_template = template.render(
                CURRENT_TIME=datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"), **kwargs
            )

            # 提取 Facts Update Template 部分
            lines = full_template.split("\n")
            in_facts_section = False
            facts_lines = []

            for line in lines:
                if "## Facts Update Template" in line:
                    in_facts_section = True
                    continue
                elif in_facts_section and line.startswith("## ") and "Facts Update" not in line:
                    break
                elif in_facts_section:
                    facts_lines.append(line)

            return "\n".join(facts_lines)
        except Exception as e:
            raise ValueError(f"應用事實更新模板失敗: {e}")

    def __init__(
        self,
        config: WorkflowConfig,
        agents: Union[Dict[str, BaseResearchAgent], Dict[str, BaseChatAgent]],
        max_rounds: int = 20,
        max_stalls_before_replan: int = 3,
        max_replans: int = 3,
        model_client: Optional[ChatCompletionClient] = None,
    ):
        """
        初始化編排器

        Args:
            config: 工作流配置
            agents: 智能體字典（支持 BaseResearchAgent 和 BaseChatAgent）
            max_rounds: 最大輪數
            max_stalls_before_replan: 重新規劃前的最大停滯次數
            max_replans: 最大重新規劃次數
            model_client: AutoGen ChatCompletionClient（可選）
        """
        self.config = config
        self.agents = agents
        self.max_rounds = max_rounds
        self.max_stalls_before_replan = max_stalls_before_replan
        self.max_replans = max_replans
        self.model_client = model_client

        # 狀態追蹤
        self.task = ""
        self.facts = ""
        self.plan = ""
        self.conversation_history: List[Union[Dict[str, Any], TextMessage]] = []
        self.ledger_history: List[LedgerEntry] = []

        # 控制變數
        self.round_count = 0
        self.stall_counter = 0
        self.replan_counter = 0
        self.should_replan = False

        # 線程管理
        self._current_thread_id: Optional[str] = None
        self._thread_logger = None

        # Command 系統
        self.command_handler = CommandHandler() if HAS_COMMAND_SYSTEM else None
        self.current_command: Optional[AutoGenCommand] = None

        # 檢測智能體類型
        self._is_autogen_system = HAS_AUTOGEN and any(
            isinstance(agent, BaseChatAgent) for agent in agents.values()
        )

        logger.info(f"初始化 LedgerOrchestrator: {config.name}")
        if self._is_autogen_system:
            logger.info("檢測到 AutoGen 智能體，啟用 AutoGen 模式")
        else:
            logger.info("使用傳統智能體模式")

    def _setup_thread_context(self, thread_id: str):
        """設置線程上下文"""
        self._current_thread_id = thread_id

        if HAS_THREAD_LOGGING:
            try:
                self._thread_logger = setup_thread_logging(thread_id)
                set_thread_context(thread_id)

                if self._thread_logger:
                    self._thread_logger.info(f"LedgerOrchestrator 線程上下文設置完成: {thread_id}")

            except Exception as e:
                logger.warning(f"線程日誌設置失敗，使用標準 logger: {e}")
                self._thread_logger = logger
        else:
            self._thread_logger = logger

    def get_team_description(self) -> str:
        """取得團隊描述"""
        descriptions = []
        for agent_name, agent in self.agents.items():
            if self._is_autogen_system and hasattr(agent, "description"):
                # AutoGen 智能體
                description = getattr(agent, "description", "智能體")
            else:
                # 傳統智能體
                role_info = agent.get_role_info()
                description = role_info.get("description", "智能體")
            descriptions.append(f"{agent_name}: {description}")
        return "\n".join(descriptions)

    def get_agent_names(self) -> List[str]:
        """取得智能體名稱列表"""
        return list(self.agents.keys())

    def add_conversation_message(self, sender: str, content: str, message_type: str = "message"):
        """添加對話消息（兼容兩種模式）"""
        if self._is_autogen_system:
            # AutoGen 模式
            message = TextMessage(content=content, source=sender)
            self.conversation_history.append(message)
        else:
            # 傳統模式
            message = {
                "timestamp": datetime.now(),
                "sender": sender,
                "content": content,
                "type": message_type,
            }
            self.conversation_history.append(message)

        if self._thread_logger:
            self._thread_logger.debug(f"添加消息: {sender} -> {content[:100]}...")

    def get_recent_conversation(self, last_n: int = 5) -> str:
        """取得最近的對話內容"""
        recent_messages = (
            self.conversation_history[-last_n:]
            if len(self.conversation_history) > last_n
            else self.conversation_history
        )

        formatted_messages = []
        for msg in recent_messages:
            if self._is_autogen_system and isinstance(msg, TextMessage):
                # AutoGen 消息
                source = getattr(msg, "source", "Unknown")
                content = getattr(msg, "content", str(msg))
                formatted_messages.append(f"[{source}]: {content}")
            else:
                # 傳統消息
                formatted_messages.append(f"[{msg['sender']}]: {msg['content']}")

        return "\n".join(formatted_messages)

    def extract_flow_control_info(
        self, message: Union[Dict[str, Any], TextMessage]
    ) -> Dict[str, Any]:
        """
        從智能體消息中提取流程控制信息
        """
        flow_info = {}

        try:
            if self._is_autogen_system and isinstance(message, TextMessage):
                # AutoGen 消息
                # 檢查是否有 metadata 屬性
                if hasattr(message, "metadata") and message.metadata:
                    flow_info = message.metadata

                # 檢查內容中是否有 [FLOW_CONTROL] 標記
                elif hasattr(message, "content") and "[FLOW_CONTROL]" in message.content:
                    pattern = r"\[FLOW_CONTROL\](.*?)\[/FLOW_CONTROL\]"
                    matches = re.findall(pattern, message.content, re.DOTALL)

                    if matches:
                        try:
                            flow_info = json.loads(matches[0])
                        except json.JSONDecodeError as e:
                            if self._thread_logger:
                                self._thread_logger.warning(f"流程控制信息解析失敗: {e}")
            else:
                # 傳統消息
                if isinstance(message, dict) and "flow_control" in message:
                    flow_info = message["flow_control"]

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.warning(f"提取流程控制信息失敗: {e}")

        return flow_info

    async def initialize_task(self, task: str, thread_id: Optional[str] = None):
        """初始化任務"""
        self.task = task

        # 設置線程上下文
        if thread_id:
            self._setup_thread_context(thread_id)

        if self._thread_logger:
            self._thread_logger.info(f"初始化任務: {task}")
        else:
            logger.info(f"初始化任務: {task}")

        # 收集初始事實
        self.facts = await self._gather_initial_facts(task)

        # 制定初始計劃
        self.plan = await self._create_initial_plan(task)

        # 記錄初始狀態
        self.add_conversation_message("Orchestrator", f"任務: {task}", "task_init")
        self.add_conversation_message("Orchestrator", f"初始事實: {self.facts}", "facts")
        self.add_conversation_message("Orchestrator", f"執行計劃: {self.plan}", "plan")

        if self._thread_logger:
            self._thread_logger.info("任務初始化完成")
        else:
            logger.info("任務初始化完成")

    async def _gather_initial_facts(self, task: str) -> str:
        """收集初始事實（簡化版本）"""
        # 在實際實現中，這裡會調用 LLM 來分析任務並收集事實
        # 現在先返回基本的任務分析
        return f"任務分析: {task}\n需要進行研究和分析工作。"

    async def _create_initial_plan(self, task: str) -> str:
        """創建初始計劃（簡化版本）"""
        # 在實際實現中，這裡會調用 LLM 生成詳細計劃
        # 現在使用模板生成計劃提示，但仍返回簡化版本
        team_description = self.get_team_description()
        facts = await self._gather_initial_facts(task)

        # 生成計劃模板（供未來 LLM 調用使用）
        plan_prompt = self._apply_plan_template(
            task=task, team_description=team_description, facts=facts
        )

        if self._thread_logger:
            self._thread_logger.debug(f"計劃提示模板已生成: {len(plan_prompt)} 字符")
        else:
            logger.debug(f"計劃提示模板已生成: {len(plan_prompt)} 字符")

        # 目前返回簡化版本的計劃
        return f"""執行計劃:
1. 協調者分析任務需求
2. 計劃者制定詳細執行步驟  
3. 研究者收集相關資訊
4. 程式設計師執行技術分析（如需要）
5. 報告者整理並生成最終報告"""

    def _analyze_agent_response(self, agent_name: str, response_content: str) -> Dict[str, Any]:
        """分析智能體回應內容，提取關鍵資訊"""
        analysis = {"key_points": [], "status": "unknown", "next_requirements": [], "summary": ""}

        # 根據智能體類型分析回應內容
        if agent_name == "coordinator":
            # 分析協調者的回應
            if "研究" in response_content or "分析" in response_content:
                analysis["status"] = "analysis_complete"
                analysis["key_points"].append("任務需求已分析")
            if "計劃" in response_content or "步驟" in response_content:
                analysis["status"] = "planning_ready"
                analysis["next_requirements"].append("需要制定詳細執行計劃")

        elif agent_name == "planner":
            # 分析計劃者的回應
            if "步驟" in response_content or "計劃" in response_content:
                analysis["status"] = "plan_ready"
                analysis["key_points"].append("執行計劃已制定")
                analysis["next_requirements"].append("需要開始實際研究工作")
            if "研究" in response_content:
                analysis["key_points"].append("研究策略已確定")

        elif agent_name == "researcher":
            # 分析研究者的回應
            if "發現" in response_content or "資料" in response_content:
                analysis["status"] = "research_complete"
                analysis["key_points"].append("研究資料已收集")
                analysis["next_requirements"].append("需要整合資訊生成報告")
            if "程式" in response_content or "代碼" in response_content:
                analysis["next_requirements"].append("需要程式碼分析")

        elif agent_name == "coder":
            # 分析程式設計師的回應
            if "分析" in response_content or "處理" in response_content:
                analysis["status"] = "code_analysis_complete"
                analysis["key_points"].append("程式碼分析已完成")
                analysis["next_requirements"].append("需要生成綜合報告")

        elif agent_name == "reporter":
            # 分析報告者的回應
            if "報告" in response_content or "完成" in response_content:
                analysis["status"] = "report_complete"
                analysis["key_points"].append("最終報告已生成")

        # 生成摘要
        if analysis["key_points"]:
            analysis["summary"] = "；".join(analysis["key_points"])

        return analysis

    async def update_ledger(self) -> LedgerEntry:
        """更新 Ledger 狀態"""
        # 準備 prompt
        team_description = self.get_team_description()
        agent_names = self.get_agent_names()
        conversation_history = self.get_recent_conversation(10)

        ledger_prompt = self._apply_ledger_template(
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

        if self._thread_logger:
            self._thread_logger.info(
                f"Ledger 更新: {ledger_entry.next_speaker} - {ledger_entry.instruction_or_question}"
            )
        else:
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
                "next_speaker": "coordinator",  # 使用配置中的智能體鍵名
                "instruction_or_question": f"請分析以下研究任務並確定執行方向: {self.task}",
                "reasoning": "任務剛開始，需要協調者進行初始分析",
                "current_step": "任務協調",
                "completed_steps": [],
                "facts_learned": [],
            }

        # 檢查最近的消息確定下一步
        last_message = self.conversation_history[-1]

        if self._is_autogen_system and isinstance(last_message, TextMessage):
            # AutoGen 消息
            last_sender = getattr(last_message, "source", "Unknown")
            last_content = getattr(last_message, "content", str(last_message))
        else:
            # 傳統消息
            last_sender = last_message["sender"]
            last_content = last_message["content"]

        # 分析最後一個智能體的回應內容
        response_analysis = self._analyze_agent_response(last_sender, last_content)

        if last_sender == "coordinator":
            # 基於協調者的回應內容生成指令
            if response_analysis["status"] == "analysis_complete":
                instruction = "基於協調者的分析，請制定詳細的執行計劃，包括具體的研究步驟和時間安排"
            elif response_analysis["status"] == "planning_ready":
                instruction = "基於協調者的分析，請制定詳細的執行計劃"
            else:
                instruction = "基於協調者的分析，請制定詳細的執行計劃"

            return {
                "is_request_satisfied": False,
                "is_in_loop": False,
                "is_progress_being_made": True,
                "next_speaker": "planner",  # 使用配置中的智能體鍵名
                "instruction_or_question": instruction,
                "reasoning": f"協調完成：{response_analysis['summary']}",
                "instructions": "基於協調者的分析，請制定詳細的執行計劃",
                "current_step": "計劃制定",
                "completed_steps": ["任務協調"],
                "facts_learned": response_analysis["key_points"],
            }

        elif last_sender == "planner":
            # 基於計劃者的回應內容生成指令
            if response_analysis["status"] == "plan_ready":
                instruction = "請根據制定的計劃開始收集相關資訊和進行研究，確保按照計劃的步驟執行"
            else:
                instruction = "請根據計劃開始收集相關資訊和進行研究"

            return {
                "is_request_satisfied": False,
                "is_in_loop": False,
                "is_progress_being_made": True,
                "next_speaker": "researcher",  # 使用配置中的智能體鍵名
                "instruction_or_question": instruction,
                "reasoning": f"計劃已制定：{response_analysis['summary']}",
                "current_step": "資訊收集",
                "completed_steps": ["任務協調", "計劃制定"],
                "facts_learned": ["任務需求已分析", "執行計劃已制定"]
                + response_analysis["key_points"],
            }

        elif last_sender == "researcher":
            # 基於研究者的回應內容生成指令
            research_summary = f"基於研究者的發現：{last_content[:100]}..."

            # 檢查是否需要程式碼分析
            if "程式" in self.task or "代碼" in self.task or "code" in self.task.lower():
                instruction = f"{research_summary} 請對相關程式碼進行分析和處理，整合研究發現"
                return {
                    "is_request_satisfied": False,
                    "is_in_loop": False,
                    "is_progress_being_made": True,
                    "next_speaker": "coder",  # 使用配置中的智能體鍵名
                    "instruction_or_question": instruction,
                    "reasoning": f"研究完成，需要技術分析：{response_analysis['summary']}",
                    "current_step": "程式碼分析",
                    "completed_steps": ["任務協調", "計劃制定", "資訊收集"],
                    "facts_learned": ["任務需求已分析", "執行計劃已制定", "研究資料已收集"]
                    + response_analysis["key_points"],
                }
            else:
                instruction = f"{research_summary} 請基於收集的資訊生成最終報告"
                return {
                    "is_request_satisfied": False,
                    "is_in_loop": False,
                    "is_progress_being_made": True,
                    "next_speaker": "reporter",  # 使用配置中的智能體鍵名
                    "instruction_or_question": instruction,
                    "reasoning": f"研究完成，可以生成報告：{response_analysis['summary']}",
                    "current_step": "報告生成",
                    "completed_steps": ["任務協調", "計劃制定", "資訊收集"],
                    "facts_learned": ["任務需求已分析", "執行計劃已制定", "研究資料已收集"]
                    + response_analysis["key_points"],
                }

        elif last_sender == "coder":
            # 基於程式設計師的回應內容生成指令
            code_analysis = f"基於程式碼分析結果：{last_content[:100]}..."
            instruction = f"{code_analysis} 請整合研究結果和程式碼分析，生成最終報告"

            return {
                "is_request_satisfied": False,
                "is_in_loop": False,
                "is_progress_being_made": True,
                "next_speaker": "reporter",  # 使用配置中的智能體鍵名
                "instruction_or_question": instruction,
                "reasoning": f"技術分析完成，需要生成綜合報告：{response_analysis['summary']}",
                "current_step": "報告生成",
                "completed_steps": ["任務協調", "計劃制定", "資訊收集", "程式碼分析"],
                "facts_learned": [
                    "任務需求已分析",
                    "執行計劃已制定",
                    "研究資料已收集",
                    "程式碼已分析",
                ]
                + response_analysis["key_points"],
            }

        elif last_sender == "reporter":
            return {
                "is_request_satisfied": True,
                "is_in_loop": False,
                "is_progress_being_made": True,
                "next_speaker": "",
                "instruction_or_question": "任務已完成",
                "reasoning": f"報告已生成，任務完成：{response_analysis['summary']}",
                "current_step": "任務完成",
                "completed_steps": ["任務協調", "計劃制定", "資訊收集", "程式碼分析", "報告生成"],
                "facts_learned": [
                    "任務需求已分析",
                    "執行計劃已制定",
                    "研究資料已收集",
                    "程式碼已分析",
                    "最終報告已生成",
                ]
                + response_analysis["key_points"],
            }

        # 預設情況
        return {
            "is_request_satisfied": False,
            "is_in_loop": False,
            "is_progress_being_made": True,
            "next_speaker": "coordinator",  # 使用配置中的智能體鍵名
            "instruction_or_question": "請繼續協調任務進展",
            "reasoning": "需要協調者介入",
            "current_step": "協調中",
            "completed_steps": [],
            "facts_learned": [],
        }

    async def select_next_agent(self) -> Optional[Union[BaseResearchAgent, BaseChatAgent]]:
        """選擇下一個智能體"""
        self.round_count += 1

        # 檢查輪數限制
        if self.round_count > self.max_rounds:
            if self._thread_logger:
                self._thread_logger.warning("達到最大輪數限制")
            else:
                logger.warning("達到最大輪數限制")
            return None

        # 更新 Ledger
        ledger_entry = await self.update_ledger()

        # 任務完成
        if ledger_entry.is_request_satisfied:
            if self._thread_logger:
                self._thread_logger.info("任務已完成")
            else:
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
            if self._is_autogen_system:
                instruction_message = TextMessage(
                    content=f"指令給 {next_agent_name}: {ledger_entry.instruction_or_question}",
                    source="Orchestrator",
                )
                self.add_conversation_message(
                    "Orchestrator",
                    f"指令給 {next_agent_name}: {ledger_entry.instruction_or_question}",
                    "instruction",
                )
            else:
                self.add_conversation_message(
                    "Orchestrator",
                    f"指令給 {next_agent_name}: {ledger_entry.instruction_or_question}",
                    "instruction",
                )

            return next_agent

        if self._thread_logger:
            self._thread_logger.warning(f"找不到智能體: {next_agent_name}")
        else:
            logger.warning(f"找不到智能體: {next_agent_name}")
        return None

    async def _handle_replan(self):
        """處理重新規劃"""
        self.replan_counter += 1

        if self.replan_counter > self.max_replans:
            if self._thread_logger:
                self._thread_logger.warning("超過最大重新規劃次數，終止任務")
            else:
                logger.warning("超過最大重新規劃次數，終止任務")
            return

        if self._thread_logger:
            self._thread_logger.info(f"第 {self.replan_counter} 次重新規劃")
        else:
            logger.info(f"第 {self.replan_counter} 次重新規劃")

        # 更新事實和計劃
        await self._update_facts_and_plan()

        # 重置狀態
        self.stall_counter = 0

        # 記錄重新規劃
        if self._is_autogen_system:
            replan_message = TextMessage(
                content=f"重新規劃 #{self.replan_counter}：檢測到工作流停滯，重新評估任務進展",
                source="Orchestrator",
            )
            self.add_conversation_message(
                "Orchestrator", f"重新規劃 #{self.replan_counter}", "replan"
            )
        else:
            self.add_conversation_message(
                "Orchestrator", f"重新規劃 #{self.replan_counter}", "replan"
            )
            self.add_conversation_message("Orchestrator", f"更新後的計劃: {self.plan}", "plan")

    async def _update_facts_and_plan(self):
        """更新事實和計劃"""
        # 更新事實
        recent_conversation = self.get_recent_conversation(10)

        # 生成事實更新模板（供未來 LLM 調用使用）
        facts_update_prompt = self._apply_facts_update_template(
            task=self.task, current_facts=self.facts, recent_conversation=recent_conversation
        )

        if self._thread_logger:
            self._thread_logger.debug(f"事實更新提示模板已生成: {len(facts_update_prompt)} 字符")
        else:
            logger.debug(f"事實更新提示模板已生成: {len(facts_update_prompt)} 字符")

        # 這裡應該調用 LLM 更新事實，現在簡化處理
        self.facts += f"\n更新的事實（基於最新對話）: {recent_conversation}"

        # 更新計劃
        team_description = self.get_team_description()
        plan_update_prompt = self._apply_plan_template(
            task=self.task, team_description=team_description, facts=self.facts
        )

        if self._thread_logger:
            self._thread_logger.debug(f"計劃更新提示模板已生成: {len(plan_update_prompt)} 字符")
        else:
            logger.debug(f"計劃更新提示模板已生成: {len(plan_update_prompt)} 字符")

        # 這裡應該調用 LLM 重新制定計劃，現在簡化處理
        self.plan += f"\n更新的計劃（第 {self.replan_counter} 次修正）"

    async def _get_agent_instruction(
        self, agent: Union[BaseResearchAgent, BaseChatAgent], task: str, round_num: int
    ) -> str:
        """
        根據智能體角色和任務狀態生成具體的指令

        Args:
            agent: 智能體實例
            task: 當前任務
            round_num: 當前輪數

        Returns:
            str: 給智能體的具體指令
        """
        if self._is_autogen_system:
            # AutoGen 智能體
            role = getattr(agent, "role", "unknown")
            name = getattr(agent, "name", "Unknown")
        else:
            # 傳統智能體
            role = agent.role
            name = agent.name

        # 根據角色和輪數生成不同的指令
        if role == AgentRole.COORDINATOR:
            if round_num == 0:
                return f"請分析任務 '{task}' 並制定整體執行策略。你需要協調其他智能體完成這個任務。"
            else:
                return f"基於前面的進展，請評估任務完成度並決定下一步行動。任務：{task}"

        elif role == AgentRole.PLANNER:
            if round_num == 0:
                return f"請為任務 '{task}' 制定詳細的執行計劃，包括具體步驟和時間安排。"
            else:
                return f"請根據前面的執行結果，調整和優化執行計劃。任務：{task}"

        elif role == AgentRole.RESEARCHER:
            if round_num == 0:
                return f"請開始研究任務 '{task}'，收集相關的資訊和資料。"
            else:
                return f"請繼續深入研究任務 '{task}'，補充更多詳細資訊和最新發展。"

        elif role == AgentRole.CODER:
            if round_num == 0:
                return f"請分析任務 '{task}' 的技術需求，提供相關的程式碼範例或技術解決方案。"
            else:
                return f"請根據前面的研究結果，提供更深入的技術分析和程式碼實作。任務：{task}"

        elif role == AgentRole.REPORTER:
            if round_num == 0:
                return f"請開始準備任務 '{task}' 的報告大綱和結構。"
            else:
                return f"請整合前面所有的研究成果，生成關於 '{task}' 的完整報告。"

        else:
            # 預設指令
            return f"請處理任務：{task}"

    async def execute_workflow(
        self,
        task: str,
        initial_message: Optional[Union[str, TextMessage]] = None,
        thread_id: Optional[str] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> WorkflowResult:
        """
        執行完整的工作流（AutoGen 模式）

        Args:
            task: 任務描述
            initial_message: 初始用戶消息
            thread_id: 線程 ID
            cancellation_token: 取消令牌

        Returns:
            WorkflowResult: 執行結果
        """
        if not self._is_autogen_system:
            raise ValueError("execute_workflow 僅支持 AutoGen 模式")

        # 設置線程上下文
        if thread_id:
            self._setup_thread_context(thread_id)

        # 初始化任務
        self.task = task

        if self._thread_logger:
            self._thread_logger.info(f"開始執行工作流: {task}")
        else:
            logger.info(f"開始執行工作流: {task}")

        try:
            # 添加初始消息
            if initial_message:
                if isinstance(initial_message, TextMessage):
                    self.conversation_history.append(initial_message)
                else:
                    task_message = TextMessage(content=initial_message, source="user")
                    self.conversation_history.append(task_message)
            else:
                # 創建任務初始化消息
                task_message = TextMessage(content=task, source="user")
                self.conversation_history.append(task_message)

            final_message = None

            # 主執行循環
            while self.round_count < self.max_rounds:
                # 選擇下一個智能體
                next_agent = await self.select_next_agent()

                if next_agent is None:
                    # 任務完成或達到限制
                    break

                # 準備智能體輸入消息
                if self.ledger_history:
                    latest_ledger = self.ledger_history[-1]
                    agent_input = TextMessage(
                        content=latest_ledger.instruction_or_question, source="Orchestrator"
                    )
                else:
                    agent_input = TextMessage(content=task, source="user")

                # 調用智能體
                if self._thread_logger:
                    self._thread_logger.info(f"調用智能體: {next_agent.name}")

                try:
                    agent_response = await next_agent.on_messages(
                        [agent_input], cancellation_token=cancellation_token
                    )

                    # 記錄智能體回應
                    self.conversation_history.append(agent_response)
                    final_message = agent_response

                    if self._thread_logger:
                        self._thread_logger.info(
                            f"智能體 {next_agent.name} 回應: {agent_response.content[:100]}..."
                        )

                except Exception as e:
                    error_msg = f"智能體 {next_agent.name} 執行失敗: {e}"
                    if self._thread_logger:
                        self._thread_logger.error(error_msg)

                    return WorkflowResult(
                        success=False, error_message=error_msg, total_rounds=self.round_count
                    )

            # 構建結果
            completed_steps = []
            facts_learned = []

            if self.ledger_history:
                latest_ledger = self.ledger_history[-1]
                completed_steps = latest_ledger.completed_steps
                facts_learned = latest_ledger.facts_learned

                success = latest_ledger.is_request_satisfied
            else:
                success = False

            if self._thread_logger:
                self._thread_logger.info(
                    f"工作流執行完成，成功: {success}, 輪數: {self.round_count}"
                )

            return WorkflowResult(
                success=success,
                final_message=final_message,
                total_rounds=self.round_count,
                completed_steps=completed_steps,
                facts_learned=facts_learned,
            )

        except Exception as e:
            error_msg = f"工作流執行失敗: {e}"
            if self._thread_logger:
                self._thread_logger.error(error_msg)
            else:
                logger.error(error_msg)

            return WorkflowResult(
                success=False, error_message=error_msg, total_rounds=self.round_count
            )

    def get_status(self) -> Dict[str, Any]:
        """取得當前狀態"""
        latest_ledger = self.ledger_history[-1] if self.ledger_history else None

        status = {
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
            "is_autogen_system": self._is_autogen_system,
            "thread_id": self._current_thread_id,
        }

        # 添加 Command 系統信息
        if HAS_COMMAND_SYSTEM and self.command_handler:
            status["command_system"] = {
                "enabled": True,
                "current_command": self.current_command.to_dict() if self.current_command else None,
                "is_complete": self.command_handler.is_workflow_complete(),
                "next_target": self.command_handler.get_next_target(),
                "command_count": len(self.command_handler.command_history),
            }
        else:
            status["command_system"] = {"enabled": False}

        return status

    def process_agent_command(
        self, agent_response: Union[Dict[str, Any], TextMessage]
    ) -> Optional[AutoGenCommand]:
        """
        處理智能體回應並生成 Command（如果適用）

        Args:
            agent_response: 智能體的回應消息

        Returns:
            AutoGenCommand 對象或 None
        """
        if not HAS_COMMAND_SYSTEM:
            return None

        try:
            # 提取流程控制信息
            flow_info = self.extract_flow_control_info(agent_response)

            if flow_info:
                command = parse_flow_control_to_command(flow_info)
                self.current_command = command

                if self.command_handler:
                    # 更新狀態
                    updated_state = self.command_handler.process_command(command)

                    if self._thread_logger:
                        self._thread_logger.info(
                            f"處理 Command: goto={command.goto}, 狀態更新: {list(updated_state.keys())}"
                        )

                return command

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.error(f"處理智能體 Command 失敗: {e}")

        return None

    def clear_history(self):
        """清除歷史記錄"""
        self.conversation_history.clear()
        self.ledger_history.clear()
        self.round_count = 0
        self.stall_counter = 0
        self.replan_counter = 0

        # 清除 Command 歷史
        if self.command_handler:
            self.command_handler.clear_history()
        self.current_command = None

        if self._thread_logger:
            self._thread_logger.info("工作流歷史已清除")
        else:
            logger.info("工作流歷史已清除")
