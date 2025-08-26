# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen SelectorGroupChat 範例程式

基於 AutoGen 的 SelectorGroupChat 實現多智能體協作工作流程，
取代原有的 LangGraph 架構，使用 AutoGen 原生的訊息傳遞機制。
"""

import asyncio
import json
import os
import sys
from typing import Sequence, Dict, Any, Optional
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# AutoGen 核心導入
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_agentchat.ui import Console

# 專案內部導入
from src.logging import init_logging, get_logger
from src.config import load_yaml_config

# 導入重新組織後的模組
from src.autogen_system.agents.agents_v3 import (
    CoordinatorAgentV3,
    PlannerAgentV3,
    ResearcherAgentV3,
    CoderAgentV3,
    ReporterAgentV3,
)
from src.autogen_system.controllers.message_framework import (
    ResearchWorkflowMessage,
    PlanMessage,
    ResearchResultMessage,
    CodeExecutionMessage,
    ReportMessage,
    parse_workflow_message,
)
from src.autogen_system.tools.tools_integration import initialize_all_tools

# 初始化日誌
init_logging()
logger = get_logger(__name__)


class WorkflowState:
    """工作流程狀態管理"""

    def __init__(self):
        self.current_plan: Optional[Dict[str, Any]] = None
        self.research_results: Dict[str, Any] = {}
        self.code_results: Dict[str, Any] = {}
        self.completed_steps: set = set()
        self.workflow_complete: bool = False
        self.error_messages: list = []

    def update_plan(self, plan: Dict[str, Any]):
        """更新執行計劃"""
        self.current_plan = plan
        logger.info(f"工作流程計劃已更新: {len(plan.get('steps', []))} 個步驟")

    def mark_step_complete(self, step_id: str, result: Any):
        """標記步驟完成"""
        self.completed_steps.add(step_id)
        logger.info(f"步驟 {step_id} 已完成")

    def is_workflow_complete(self) -> bool:
        """檢查工作流程是否完成"""
        if not self.current_plan:
            return False

        total_steps = len(self.current_plan.get("steps", []))
        completed_count = len(self.completed_steps)

        return completed_count >= total_steps or self.workflow_complete

    def get_next_step(self) -> Optional[Dict[str, Any]]:
        """獲取下一個待執行的步驟"""
        if not self.current_plan:
            return None

        for step in self.current_plan.get("steps", []):
            step_id = step.get("id", str(step.get("step_type", "")))
            if step_id not in self.completed_steps:
                return step

        return None


def selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
    """
    智能體選擇函數

    基於 builder.py 中 continue_to_running_research_team() 的邏輯，
    根據當前訊息歷史和工作流程狀態決定下一個應該發言的智能體。

    Args:
        messages: 對話歷史訊息

    Returns:
        str | None: 下一個智能體的名稱，或 None 讓模型自動選擇
    """
    if not messages:
        return "CoordinatorAgentV3"

    last_message = messages[-1]
    last_speaker = last_message.source

    logger.info(f"selector_func: 上一個發言者 = {last_speaker}")

    try:
        # 解析最後一條訊息以獲取工作流程信息
        workflow_msg = parse_workflow_message(last_message.content)
        logger.info(f"workflow_msg: {workflow_msg}")

        # 0. 使用者發言 -> 協調者, last_message.content 是 user 輸入的訊息 "請研究人工智慧在教育領域的最新應用"
        if last_speaker == "user":
            logger.info("0. Selector: 使用者發言，轉到協調者")
            return "CoordinatorAgentV3"

        # 1. 協調者 -> 規劃者（初始階段）, last_message.content 是 coordinator 的訊息 "任務分析/工作流程策略/資源需求/時間預估"
        if last_speaker == "CoordinatorAgentV3":
            logger.info("1. Selector: 協調者完成初始分析，轉到規劃者")
            return "PlannerAgentV3"

        # 2. 規劃者邏輯, last_message.content 是 planner 的訊息 "計劃內容/資源需求"
        elif last_speaker == "PlannerAgentV3":
            if workflow_msg and workflow_msg.message_type == "plan":
                plan_data = workflow_msg.data

                # 如果沒有計劃步驟，重新規劃
                if not plan_data.get("steps"):
                    logger.info("2. Selector: 計劃為空，保持在規劃者")
                    return "PlannerAgentV3"

                # 檢查是否所有步驟都已完成
                completed_steps = plan_data.get("completed_steps", [])
                total_steps = plan_data.get("steps", [])
                logger.info(f"completed_steps: {completed_steps}")
                logger.info(f"total_steps: {total_steps}")

                if len(completed_steps) >= len(total_steps):
                    logger.info("2. Selector: 所有步驟已完成，轉到報告者")
                    return "ReporterAgentV3"

                # 找到下一個未完成的步驟
                for step in total_steps:
                    step_id = step.get("id", step.get("step_type"))
                    logger.info(f"step_id: {step_id}")
                    if step_id not in completed_steps:
                        step_type = step.get("step_type", "").lower()
                        logger.info(f"step_type: {step_type}")

                        if "research" in step_type or "search" in step_type:
                            logger.info(f"2. Selector: 需要執行研究步驟 {step_id}，轉到研究者")
                            return "ResearcherAgentV3"
                        elif "code" in step_type or "processing" in step_type:
                            logger.info(
                                f"2. Selector: 需要執行程式碼步驟 {step_id}，轉到程式設計師"
                            )
                            return "CoderAgentV3"
                        else:
                            logger.info(f"2. Selector: 未知步驟類型 {step_type}，轉到研究者")
                            return "ResearcherAgentV3"

                # 如果沒有找到未完成步驟，轉到報告者
                logger.info("2. Selector: 找不到未完成步驟，轉到報告者")
                return "ReporterAgentV3"

        # 3. 研究者完成 -> 檢查是否需要繼續
        elif last_speaker == "ResearcherAgentV3":
            if workflow_msg and workflow_msg.message_type == "research_result":
                # 檢查是否還有研究步驟
                if "more_research_needed" in last_message.content:
                    logger.info("3. Selector: 需要更多研究，保持在研究者")
                    return "ResearcherAgentV3"
                else:
                    logger.info("3. Selector: 研究完成，轉回規劃者檢查下一步")
                    return "PlannerAgentV3"

        # 4. 程式設計師完成 -> 檢查是否需要繼續
        elif last_speaker == "CoderAgentV3":
            if workflow_msg and workflow_msg.message_type == "code_execution":
                # 檢查是否還有程式碼步驟
                if "more_coding_needed" in last_message.content:
                    logger.info("4. Selector: 需要更多程式碼工作，保持在程式設計師")
                    return "CoderAgentV3"
                else:
                    logger.info("4. Selector: 程式碼執行完成，轉回規劃者檢查下一步")
                    return "PlannerAgentV3"

        # 5. 報告者完成 -> 結束工作流程, 檢查訊息內容是否包含終止標記
        elif last_speaker == "ReporterAgentV3":
            # 檢查是否包含終止標記
            has_termination_marker = (
                "WORKFLOW_COMPLETE" in last_message.content or "TERMINATE" in last_message.content
            )

            if has_termination_marker:
                logger.info("5. Selector: 報告者真正完成工作流程，包含終止標記，準備結束")
                logger.info(
                    f"   終止標記: {'WORKFLOW_COMPLETE' if 'WORKFLOW_COMPLETE' in last_message.content else 'TERMINATE'}"
                )
                return None  # 讓 AutoGen 處理結束邏輯
            else:
                logger.info("5. Selector: 報告者發言，但未包含終止標記，繼續執行")
                logger.info("   提示：報告者需要在報告結尾包含 'WORKFLOW_COMPLETE' 或 'TERMINATE'")
                # 如果報告者沒有明確表示完成，讓模型自動選擇下一個
                return None

        # 6. 默認邏輯：如果無法判斷，讓模型自動選擇
        logger.info("6. Selector: 使用默認邏輯，讓模型自動選擇")
        return None

    except Exception as e:
        logger.error(f"Selector 函數執行錯誤: {e}")
        return None


async def create_agents(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    創建所有智能體

    Args:
        config: 配置字典

    Returns:
        Dict[str, Any]: 智能體字典
    """
    logger.info("開始創建智能體...")

    # 先初始化工具
    logger.info("初始化工具系統...")
    await initialize_all_tools()

    # 創建智能體實例
    coordinator = await CoordinatorAgentV3.create(config)
    planner = await PlannerAgentV3.create(config)
    researcher = await ResearcherAgentV3.create(config)
    coder = await CoderAgentV3.create(config)
    reporter = await ReporterAgentV3.create(config)

    agents = {
        "coordinator": coordinator,
        "planner": planner,
        "researcher": researcher,
        "coder": coder,
        "reporter": reporter,
    }

    logger.info(f"智能體創建完成，共 {len(agents)} 個")
    return agents


async def run_workflow_example(task: str, config_path: str = "conf_autogen.yaml"):
    """
    執行工作流程範例

    Args:
        task: 要執行的任務描述
        config_path: 配置檔案路徑
    """
    logger.info(f"🚀 開始執行 AutoGen SelectorGroupChat 工作流程")
    logger.info(f"📋 任務: {task}")

    try:
        # 載入配置
        config = load_yaml_config(config_path)
        logger.info("✅ 配置載入成功")

        # 創建智能體
        agents = await create_agents(config)

        # 創建智能體列表（使用底層的 AssistantAgent）
        agent_list = [
            agents["coordinator"].get_agent(),  # 獲取底層的 AssistantAgent
            agents["planner"].get_agent(),
            agents["researcher"].get_agent(),
            agents["coder"].get_agent(),
            agents["reporter"].get_agent(),
        ]

        # 創建終止條件
        termination = TextMentionTermination("WORKFLOW_COMPLETE")

        # 獲取模型客戶端（使用協調者的模型）
        model_client = agents["coordinator"]._model_client

        # 創建 SelectorGroupChat
        # 注意：參數名稱可能因版本而異，嘗試不同的參數名稱
        try:
            team = SelectorGroupChat(
                participants=agent_list,  # 嘗試 participants 參數
                model_client=model_client,
                termination_condition=termination,
                selector_func=selector_func,
                max_turns=50,
            )
        except TypeError:
            # 如果 participants 不對，嘗試其他參數名稱
            try:
                team = SelectorGroupChat(
                    agent_list,  # 嘗試位置參數
                    model_client=model_client,
                    termination_condition=termination,
                    selector_func=selector_func,
                    max_turns=50,
                )
            except TypeError:
                # 最後嘗試最簡化的初始化
                team = SelectorGroupChat(
                    participants=agent_list,
                    selector_func=selector_func,
                )

        logger.info("✅ SelectorGroupChat 創建成功")

        # 執行工作流程
        logger.info("🎯 開始執行任務...")
        await Console(team.run_stream(task=task))

        logger.info("🎉 工作流程執行完成")

    except Exception as e:
        logger.error(f"❌ 工作流程執行失敗: {e}")
        raise


async def main():
    """主函數"""
    # 檢查環境變數
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        logger.error("❌ 請設定 AZURE_OPENAI_ENDPOINT 環境變數")
        return

    # 範例任務
    # task = """
    # 請研究人工智慧在教育領域的最新應用，包括：
    # 1. 搜尋相關的最新研究論文和技術報告
    # 2. 分析主要的應用場景和技術特點
    # 3. 整理相關數據並進行簡單的統計分析
    # 4. 生成一份詳細的研究報告
    # """
    task = "請研究人工智慧在教育領域的最新應用"

    # 執行工作流程
    await run_workflow_example(task)


if __name__ == "__main__":
    # 確保日誌目錄存在
    os.makedirs("logs", exist_ok=True)

    # 執行主函數
    asyncio.run(main())
