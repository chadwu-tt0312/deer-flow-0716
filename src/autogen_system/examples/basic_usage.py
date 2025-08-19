# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 系統基本使用範例

展示如何使用新的 AutoGen 系統替代原有的 LangGraph 工作流。
"""

import asyncio
from autogen_system import (
    WorkflowController,
    LedgerOrchestrator,
    AgentFactory,
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
        name="Coordinator",
        role=AgentRole.COORDINATOR,
        system_message="你是研究工作流的協調者。",
        llm_config=llm_config,
    )

    planner_config = AgentConfig(
        name="Planner",
        role=AgentRole.PLANNER,
        system_message="你負責制定研究計劃。",
        llm_config=llm_config,
    )

    researcher_config = AgentConfig(
        name="Researcher",
        role=AgentRole.RESEARCHER,
        system_message="你負責進行資訊收集和研究。",
        llm_config=llm_config,
        tools=["web_search", "crawl_tool"],
    )

    reporter_config = AgentConfig(
        name="Reporter",
        role=AgentRole.REPORTER,
        system_message="你負責撰寫研究報告。",
        llm_config=llm_config,
    )

    # 3. 創建工作流配置
    workflow_config = WorkflowConfig(
        name="simple_research",
        workflow_type=WorkflowType.RESEARCH,
        agents=[coordinator_config, planner_config, researcher_config, reporter_config],
        max_iterations=5,
    )

    # 4. 創建智能體實例
    agents = {
        "Coordinator": AgentFactory.create_coordinator(coordinator_config),
        "Planner": AgentFactory.create_planner(planner_config),
        "Researcher": AgentFactory.create_researcher(researcher_config),
        "Reporter": AgentFactory.create_reporter(reporter_config),
    }

    # 5. 創建並啟動工作流控制器
    controller = WorkflowController(
        config=workflow_config, agents=agents, use_ledger_orchestrator=True
    )

    # 6. 執行研究任務
    task = "請研究人工智慧在醫療領域的最新應用趨勢"

    print(f"🚀 啟動研究任務: {task}")

    result = await controller.start_ledger_workflow(task)

    print(f"✅ 任務完成，狀態: {result['status']}")

    return result


async def standalone_orchestrator_example():
    """獨立使用 LedgerOrchestrator 的範例"""

    # 簡化的智能體配置
    agents = {
        "Coordinator": AgentFactory.create_coordinator(
            AgentConfig(name="Coordinator", role=AgentRole.COORDINATOR, system_message="協調者")
        ),
        "Researcher": AgentFactory.create_researcher(
            AgentConfig(name="Researcher", role=AgentRole.RESEARCHER, system_message="研究員")
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
