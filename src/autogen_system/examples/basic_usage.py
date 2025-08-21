# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 系統基本使用範例

展示如何使用新的 AutoGen 系統替代原有的 LangGraph 工作流。
"""

import asyncio
import sys
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.autogen_system.controllers.workflow_controller import WorkflowController
from src.autogen_system.controllers.ledger_orchestrator import LedgerOrchestrator
from src.autogen_system.agents.base_agent import AgentFactory
from src.autogen_system.config.agent_config import (
    AgentConfig,
    WorkflowConfig,
    LLMConfig,
    AgentRole,
    WorkflowType,
)


async def simple_research_workflow():
    """簡單的研究工作流範例"""

    # 1. 配置 LLM
    llm_config = LLMConfig(model="gpt-4o-mini", temperature=0.7, max_tokens=1500)

    # 2. 創建智能體配置
    coordinator_config = AgentConfig(
        name="CoordinatorAgent",
        role=AgentRole.COORDINATOR,
        system_message="你是研究工作流的協調者。",
        llm_config=llm_config,
    )

    planner_config = AgentConfig(
        name="PlannerAgent",
        role=AgentRole.PLANNER,
        system_message="你負責制定研究計劃。",
        llm_config=llm_config,
    )

    researcher_config = AgentConfig(
        name="ResearcherAgent",
        role=AgentRole.RESEARCHER,
        system_message="你負責進行資訊收集和研究。",
        llm_config=llm_config,
        tools=["web_search", "crawl_tool"],
    )

    coder_config = AgentConfig(
        name="CoderAgent",
        role=AgentRole.CODER,
        system_message="你負責程式碼分析和執行。",
        llm_config=llm_config,
        tools=["python_repl"],
    )

    reporter_config = AgentConfig(
        name="ReporterAgent",
        role=AgentRole.REPORTER,
        system_message="你負責撰寫研究報告。",
        llm_config=llm_config,
    )

    # 3. 創建工作流配置
    workflow_config = WorkflowConfig(
        name="simple_research",
        workflow_type=WorkflowType.RESEARCH,
        agents=[
            coordinator_config,
            planner_config,
            researcher_config,
            coder_config,
            reporter_config,
        ],
        max_iterations=5,
    )

    # 4. 創建智能體實例
    agents = {
        "CoordinatorAgent": AgentFactory.create_coordinator(coordinator_config),
        "PlannerAgent": AgentFactory.create_planner(planner_config),
        "ResearcherAgent": AgentFactory.create_researcher(researcher_config),
        "CoderAgent": AgentFactory.create_coder(coder_config),
        "ReporterAgent": AgentFactory.create_reporter(reporter_config),
    }

    # 5. 使用 LedgerOrchestrator 執行工作流
    orchestrator = LedgerOrchestrator(config=workflow_config, agents=agents, max_rounds=10)

    # 6. 執行研究任務
    task = "請研究人工智慧在醫療領域的最新應用趨勢"

    print(f"🚀 啟動研究任務: {task}")

    # 初始化任務
    await orchestrator.initialize_task(task)

    # 執行幾輪智能體選擇
    for round_num in range(5):
        next_agent = await orchestrator.select_next_agent()
        if next_agent is None:
            print("✅ 工作流完成")
            break

        print(f"🔄 第 {round_num + 1} 輪: {next_agent.name}")

        # 模擬智能體回應
        mock_response = f"{next_agent.name} 已完成分配的任務"
        orchestrator.add_conversation_message(next_agent.name, mock_response)

    # 獲取最終狀態
    status = orchestrator.get_status()
    print(f"✅ 任務完成，狀態: {status}")

    return status


async def standalone_orchestrator_example():
    """獨立使用 LedgerOrchestrator 的範例"""

    # 簡化的智能體配置
    agents = {
        "CoordinatorAgent": AgentFactory.create_coordinator(
            AgentConfig(
                name="CoordinatorAgent", role=AgentRole.COORDINATOR, system_message="協調者"
            )
        ),
        "PlannerAgent": AgentFactory.create_planner(
            AgentConfig(name="PlannerAgent", role=AgentRole.PLANNER, system_message="計劃者")
        ),
        "ResearcherAgent": AgentFactory.create_researcher(
            AgentConfig(name="ResearcherAgent", role=AgentRole.RESEARCHER, system_message="研究員")
        ),
        "ReporterAgent": AgentFactory.create_reporter(
            AgentConfig(name="ReporterAgent", role=AgentRole.REPORTER, system_message="報告者")
        ),
    }

    # 創建編排器
    orchestrator = LedgerOrchestrator(
        config=WorkflowConfig(name="standalone", workflow_type=WorkflowType.RESEARCH),
        agents=agents,
        max_rounds=5,
    )

    # 初始化任務
    await orchestrator.initialize_task("分析區塊鏈技術的發展趨勢")

    # 手動執行幾輪
    for i in range(3):
        next_agent = await orchestrator.select_next_agent()
        if next_agent:
            print(f"第 {i + 1} 輪: {next_agent.name}")
            # 模擬回應
            orchestrator.add_conversation_message(
                next_agent.name, f"我是 {next_agent.name}，已完成分配的任務。"
            )
        else:
            break

    return orchestrator.get_status()


if __name__ == "__main__":
    print("📚 AutoGen 系統使用範例")

    print("\n1️⃣ 完整工作流範例:")
    result1 = asyncio.run(simple_research_workflow())

    print("\n2️⃣ 獨立編排器範例:")
    result2 = asyncio.run(standalone_orchestrator_example())

    print(f"\n📊 編排器狀態: {result2}")
    print("\n🎉 範例執行完成!")
