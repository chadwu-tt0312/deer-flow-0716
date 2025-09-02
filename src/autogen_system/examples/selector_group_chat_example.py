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
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# AutoGen 核心導入
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_agentchat.ui import Console

# 專案內部導入
from src.deerflow_logging import (
    init_thread_logging,
    get_thread_logger,
    set_thread_context,
)
from src.config import load_yaml_config

# 導入重新組織後的模組
from src.autogen_system.agents.agents_v3 import (
    CoordinatorAgentV3,
    PlannerAgentV3,
    ResearcherAgentV3,
    CoderAgentV3,
    ReporterAgentV3,
    BackgroundInvestigatorAgentV3,
    HumanFeedbackerAgentV3,
)
from src.autogen_system.agents.message_framework import (
    ResearchWorkflowMessage,
    PlanMessage,
    ResearchResultMessage,
    CodeExecutionMessage,
    ReportMessage,
    parse_workflow_message,
)
from src.autogen_system.tools.tools_integration import initialize_all_tools
from src.autogen_system.workflow import create_selector_function, AgentSelector

# 初始化 thread-safe 日誌
init_thread_logging()
# 設定 thread context（這裡使用固定的 thread_id，實際使用時會從請求中獲取）
thread_id = "selector_group_chat_example"
set_thread_context(thread_id)
logger = get_thread_logger()  # 使用當前 thread context

# 設定 AutoGen 和其他第三方庫的日誌級別和處理器
import logging

autogen_logger = logging.getLogger("autogen_agentchat")
autogen_core_logger = logging.getLogger("autogen_core")

# 將 AutoGen 的日誌也重定向到我們的檔案
from src.deerflow_logging.thread_logger import _manager

thread_logger_instance = _manager.get_logger(thread_id)
for handler in thread_logger_instance.handlers:
    if hasattr(handler, "baseFilename"):  # 檔案處理器
        autogen_logger.addHandler(handler)
        autogen_core_logger.addHandler(handler)
        break

autogen_logger.setLevel(logging.INFO)
autogen_core_logger.setLevel(logging.INFO)


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


# 創建全局選擇器實例
_global_selector = None


def get_selector_func(selector_type: str = "basic", **kwargs):
    """
    獲取選擇器函數

    Args:
        selector_type: 選擇器類型 ("basic" 或 "advanced")
        **kwargs: 選擇器初始化參數

    Returns:
        callable: 選擇器函數
    """
    global _global_selector

    if _global_selector is None:
        _global_selector = create_selector_function(
            selector_type=selector_type, enable_debug=True, **kwargs
        )

    return _global_selector


def selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
    """
    智能體選擇函數（重構版本）

    使用新的 AgentSelector 類來決定下一個應該發言的智能體。
    保持與原始函數相同的介面以確保向後兼容性。

    Args:
        messages: 對話歷史訊息

    Returns:
        str | None: 下一個智能體的名稱，或 None 讓模型自動選擇
    """
    try:
        # 獲取選擇器函數
        selector = get_selector_func()
        return selector(messages)
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
    background_investigator = await BackgroundInvestigatorAgentV3.create(config)
    human_feedbacker = await HumanFeedbackerAgentV3.create(config)

    agents = {
        "coordinator": coordinator,
        "planner": planner,
        "researcher": researcher,
        "coder": coder,
        "reporter": reporter,
        "background_investigator": background_investigator,
        "human_feedbacker": human_feedbacker,
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
            agents["background_investigator"].get_agent(),
            agents["human_feedbacker"].get_agent(),
        ]

        # 創建終止條件
        termination = TextMentionTermination("WORKFLOW_COMPLETE")

        # 獲取模型客戶端（使用協調者的模型）
        model_client = agents["coordinator"]._model_client

        # 獲取選擇器函數（可以選擇 "basic" 或 "advanced"）
        selector_function = get_selector_func(selector_type="basic", max_turns=50)

        # 創建 SelectorGroupChat
        # 注意：參數名稱可能因版本而異，嘗試不同的參數名稱
        try:
            team = SelectorGroupChat(
                participants=agent_list,  # 嘗試 participants 參數
                model_client=model_client,
                termination_condition=termination,
                selector_func=selector_function,
                max_turns=50,
            )
        except TypeError:
            # 如果 participants 不對，嘗試其他參數名稱
            try:
                team = SelectorGroupChat(
                    agent_list,  # 嘗試位置參數
                    model_client=model_client,
                    termination_condition=termination,
                    selector_func=selector_function,
                    max_turns=50,
                )
            except TypeError:
                # 最後嘗試最簡化的初始化
                team = SelectorGroupChat(
                    participants=agent_list,
                    selector_func=selector_function,
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
