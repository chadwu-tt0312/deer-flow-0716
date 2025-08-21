# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 工作流測試腳本

用於測試 WorkflowController 和 LedgerOrchestrator 的基本功能。
"""

import asyncio
import sys
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.autogen_system.config.agent_config import (
    AgentConfig,
    WorkflowConfig,
    LLMConfig,
    AgentRole,
    WorkflowType,
)
from src.autogen_system.agents.base_agent import AgentFactory
from src.autogen_system.controllers.workflow_controller import WorkflowController
from src.autogen_system.controllers.ledger_orchestrator import LedgerOrchestrator


async def test_basic_workflow():
    """測試基本工作流功能"""
    print("🚀 開始測試 AutoGen 工作流系統")

    # 創建 LLM 配置
    llm_config = LLMConfig(model="gpt-4o-mini", temperature=0.7, max_tokens=1000)

    # 創建智能體配置
    agent_configs = [
        AgentConfig(
            name="CoordinatorAgent",
            role=AgentRole.COORDINATOR,
            system_message="你是協調者，負責管理整個研究工作流程。",
            llm_config=llm_config,
        ),
        AgentConfig(
            name="PlannerAgent",
            role=AgentRole.PLANNER,
            system_message="你是計劃者，負責分析需求並制定詳細的執行計劃。",
            llm_config=llm_config,
        ),
        AgentConfig(
            name="ResearcherAgent",
            role=AgentRole.RESEARCHER,
            system_message="你是研究員，負責進行網路搜尋和資訊收集。",
            llm_config=llm_config,
            tools=["web_search", "crawl_tool"],
        ),
        AgentConfig(
            name="CoderAgent",
            role=AgentRole.CODER,
            system_message="你是程式設計師，負責程式碼分析和執行。",
            llm_config=llm_config,
            tools=["python_repl"],
        ),
        AgentConfig(
            name="ReporterAgent",
            role=AgentRole.REPORTER,
            system_message="你是報告撰寫者，負責整理資訊並生成最終報告。",
            llm_config=llm_config,
        ),
    ]

    # 創建工作流配置
    workflow_config = WorkflowConfig(
        name="test_research_workflow",
        workflow_type=WorkflowType.RESEARCH,
        agents=agent_configs,
        max_iterations=3,
    )

    # 創建智能體實例
    agents = {}
    for agent_config in agent_configs:
        if agent_config.role == AgentRole.COORDINATOR:
            agent = AgentFactory.create_coordinator(agent_config)
        elif agent_config.role == AgentRole.PLANNER:
            agent = AgentFactory.create_planner(agent_config)
        elif agent_config.role == AgentRole.RESEARCHER:
            agent = AgentFactory.create_researcher(agent_config)
        elif agent_config.role == AgentRole.CODER:
            agent = AgentFactory.create_coder(agent_config)
        elif agent_config.role == AgentRole.REPORTER:
            agent = AgentFactory.create_reporter(agent_config)
        else:
            continue

        agents[agent_config.name] = agent

    print(f"✅ 已創建 {len(agents)} 個智能體")

    # 測試 LedgerOrchestrator
    print("\n📋 測試 LedgerOrchestrator")

    ledger_orchestrator = LedgerOrchestrator(config=workflow_config, agents=agents, max_rounds=10)

    # 初始化任務
    test_task = "請研究 Python 多執行緒程式設計的最佳實務"
    await ledger_orchestrator.initialize_task(test_task)

    print(f"📝 任務: {test_task}")
    print(f"📊 事實: {ledger_orchestrator.facts}")
    print(f"📋 計劃: {ledger_orchestrator.plan}")

    # 模擬幾輪智能體選擇
    for round_num in range(5):
        print(f"\n🔄 第 {round_num + 1} 輪")

        next_agent = await ledger_orchestrator.select_next_agent()
        if next_agent is None:
            print("✅ 工作流完成")
            break

        print(f"👤 選擇的智能體: {next_agent.name}")

        # 取得最新的 Ledger 條目
        if ledger_orchestrator.ledger_history:
            latest_ledger = ledger_orchestrator.ledger_history[-1]
            print(f"📝 指令: {latest_ledger.instruction_or_question}")
            print(f"🤔 理由: {latest_ledger.reasoning}")

            # 模擬智能體回應
            mock_response = f"{next_agent.name} 已完成指令: {latest_ledger.instruction_or_question}"
            ledger_orchestrator.add_conversation_message(next_agent.name, mock_response)

    # 顯示最終狀態
    status = ledger_orchestrator.get_status()
    print(f"\n📊 最終狀態:")
    print(f"   - 輪數: {status['round_count']}")
    print(f"   - 停滯計數: {status['stall_counter']}")
    print(f"   - 重新規劃次數: {status['replan_counter']}")
    print(f"   - 對話長度: {status['conversation_length']}")

    # 測試完整的 WorkflowController
    print("\n🎯 測試 WorkflowController")

    workflow_controller = WorkflowController()

    try:
        # 創建一個簡單的工作流計劃
        from src.autogen_system.controllers.workflow_controller import (
            WorkflowStep,
            WorkflowPlan,
            StepType,
            ExecutionStatus,
        )

        # 註冊步驟處理器
        async def mock_step_handler(step: WorkflowStep, context: dict) -> dict:
            """模擬步驟處理器"""
            print(f"🔧 執行步驟: {step.name}")
            # 模擬執行時間
            import time

            time.sleep(0.1)
            return {"result": f"步驟 {step.name} 執行完成", "status": "success"}

        workflow_controller.register_step_handler(StepType.RESEARCH, mock_step_handler)

        # 創建測試步驟
        test_steps = [
            WorkflowStep(
                id="test_step_1",
                name="測試步驟1",
                step_type=StepType.RESEARCH,
                description="測試研究步驟",
                agent_type="researcher",
                inputs={"topic": test_task},
                dependencies=[],
                estimated_duration=5,
            )
        ]

        # 創建測試計劃
        test_plan = WorkflowPlan(
            id="test_plan",
            name="測試計劃",
            description="用於測試的工作流計劃",
            steps=test_steps,
            estimated_duration=10,
        )

        # 執行計劃
        result = await workflow_controller.execute_plan(test_plan, {"task": test_task})
        print(f"✅ 工作流結果: {result.get('plan_status', 'unknown')}")
        print(f"📈 計劃狀態: {result.get('plan_status', 'unknown')}")
        print(f"📋 總步驟數: {result.get('total_steps', 0)}")
        print(f"⏱️ 執行時間: {result.get('execution_time', 0):.2f} 秒")

    except Exception as e:
        print(f"❌ 工作流執行失敗: {e}")

    print("\n🎉 測試完成!")


if __name__ == "__main__":
    # 確保有事件循環
    try:
        asyncio.run(test_basic_workflow())
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback

        traceback.print_exc()
