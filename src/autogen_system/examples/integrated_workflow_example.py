#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
整合工作流示例

展示如何使用整合了 LedgerOrchestrator 的 ConversationManager 和 WorkflowController。
"""

import asyncio
import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from src.logging import get_logger, setup_thread_logging
from src.autogen_system.controllers.ledger_orchestrator import LedgerOrchestrator
from src.autogen_system.controllers.conversation_manager import AutoGenConversationManager
from src.autogen_system.controllers.workflow_controller import (
    create_workflow_controller_with_ledger,
)
from src.autogen_system.agents import CoordinatorAgent, PlannerAgent, ResearcherAgent
from src.autogen_system.adapters.llm_adapter import create_chat_client
from src.autogen_system.config.agent_config import WorkflowConfig

logger = get_logger(__name__)


async def create_integrated_system():
    """創建整合的系統"""
    logger.info("🚀 創建整合系統...")

    # 1. 創建智能體
    logger.info("🤖 創建智能體...")

    # 協調者智能體
    coordinator = CoordinatorAgent(
        name="coordinator",
        model_client=create_chat_client(),
        description="負責協調整個工作流程",
    )

    # 計劃者智能體
    from src.autogen_system.config.agent_config import AgentConfig, AgentRole

    planner_config = AgentConfig(
        name="planner",
        role=AgentRole.PLANNER,
        system_message="負責制定研究計劃",
        max_consecutive_auto_reply=3,
    )
    planner = PlannerAgent(planner_config)

    # 研究者智能體
    researcher_config = AgentConfig(
        name="researcher",
        role=AgentRole.RESEARCHER,
        system_message="負責執行研究任務",
        max_consecutive_auto_reply=3,
    )
    researcher = ResearcherAgent(researcher_config)

    agents = {"coordinator": coordinator, "planner": planner, "researcher": researcher}

    logger.info(f"✅ 已創建 {len(agents)} 個智能體")

    # 2. 創建工作流配置
    logger.info("⚙️ 創建工作流配置...")

    workflow_config = WorkflowConfig(
        name="integrated_research_workflow",
        workflow_type="research",
        max_iterations=10,
        agents=list(agents.keys()),
    )

    # 3. 創建 LedgerOrchestrator
    logger.info("📊 創建 LedgerOrchestrator...")

    ledger_orchestrator = LedgerOrchestrator(
        config=workflow_config,
        agents=agents,
        max_rounds=10,
        max_stalls_before_replan=3,
        max_replans=3,
    )

    # 4. 創建整合的 WorkflowController
    logger.info("🎯 創建整合的 WorkflowController...")

    workflow_controller = create_workflow_controller_with_ledger(ledger_orchestrator)

    # 5. 創建整合的 ConversationManager
    logger.info("💬 創建整合的 ConversationManager...")

    # 創建一個模擬的 ChatCompletionClient
    class MockChatCompletionClient:
        def __init__(self):
            self.name = "mock_client"

    conversation_manager = AutoGenConversationManager(model_client=MockChatCompletionClient())

    # 手動設置 LedgerOrchestrator
    conversation_manager.ledger_orchestrator = ledger_orchestrator

    logger.info("✅ 整合系統創建完成")

    return {
        "agents": agents,
        "ledger_orchestrator": ledger_orchestrator,
        "workflow_controller": workflow_controller,
        "conversation_manager": conversation_manager,
    }


async def demonstrate_integrated_workflow(system):
    """演示整合工作流"""
    logger.info("🎭 開始演示整合工作流...")

    # 1. 演示 LedgerOrchestrator
    logger.info("📊 演示 LedgerOrchestrator...")

    task = "請研究人工智慧在醫療領域的最新應用趨勢"
    await system["ledger_orchestrator"].initialize_task(task)

    logger.info(f"✅ 任務初始化完成: {task}")

    # 2. 演示工作流執行
    logger.info("🔄 演示工作流執行...")

    max_rounds = 3
    for round_num in range(max_rounds):
        logger.info(f"🔄 第 {round_num + 1} 輪開始...")

        # 選擇下一個智能體
        next_agent = await system["ledger_orchestrator"].select_next_agent()

        if next_agent is None:
            logger.info("✅ 任務完成")
            break

        logger.info(f"👤 選擇的智能體: {next_agent.name}")

        # 獲取指令
        if system["ledger_orchestrator"].ledger_history:
            latest_ledger = system["ledger_orchestrator"].ledger_history[-1]
            instruction = latest_ledger.instruction_or_question
        else:
            instruction = f"請處理任務：{task}"

        logger.info(f"📝 指令: {instruction}")

        # 模擬智能體回應
        if hasattr(next_agent, "process_user_input"):
            try:
                response = await next_agent.process_user_input(instruction)
                response_content = response.get("response", str(response))
            except Exception as e:
                response_content = f"智能體執行失敗: {e}"
        else:
            response_content = f"智能體 {next_agent.name} 回應：{instruction}"

        # 記錄回應
        system["ledger_orchestrator"].add_conversation_message(
            next_agent.name, response_content, "agent_response"
        )

        logger.info(f"💬 {next_agent.name}: {response_content[:100]}...")
        logger.info(f"✅ 第 {round_num + 1} 輪完成")

    # 3. 演示 WorkflowController 整合
    logger.info("🎯 演示 WorkflowController 整合...")

    # 同步狀態
    system["workflow_controller"].sync_with_ledger()

    # 獲取 Ledger 狀態
    ledger_status = system["workflow_controller"].get_ledger_status()
    if ledger_status:
        logger.info(f"📊 Ledger 狀態: 輪數={ledger_status.get('round_count', 0)}")
        logger.info(f"📊 任務: {ledger_status.get('task', 'N/A')}")

    # 4. 演示 ConversationManager 整合
    logger.info("💬 演示 ConversationManager 整合...")

    # 獲取對話摘要
    conversation_summary = system["conversation_manager"].get_conversation_summary()
    logger.info(f"📋 對話摘要: 使用 Ledger={conversation_summary.get('using_ledger', False)}")

    if conversation_summary.get("ledger_status"):
        ledger_info = conversation_summary["ledger_status"]
        logger.info(f"📊 Ledger 信息: 輪數={ledger_info.get('round_count', 0)}")

    logger.info("✅ 整合工作流演示完成")


async def main():
    """主函數"""
    logger.info("🚀 整合工作流示例開始")

    try:
        # 設置線程日誌
        setup_thread_logging("integrated_example")

        # 創建整合系統
        system = await create_integrated_system()

        # 演示整合工作流
        await demonstrate_integrated_workflow(system)

        # 顯示最終狀態
        logger.info("📊 最終系統狀態:")
        logger.info(f"  - 智能體數量: {len(system['agents'])}")
        logger.info(
            f"  - 使用 LedgerOrchestrator: {system['workflow_controller'].is_using_ledger()}"
        )
        logger.info(
            f"  - 對話管理器使用 Ledger: {system['conversation_manager'].ledger_orchestrator is not None}"
        )

        logger.info("🎉 整合工作流示例執行完成")

    except Exception as e:
        logger.error(f"❌ 示例執行失敗: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
