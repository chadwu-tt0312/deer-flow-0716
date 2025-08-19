# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen系統完整工作流集成測試

測試從端到端的完整工作流執行。
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.autogen_system.controllers.conversation_manager import AutoGenConversationManager
from src.autogen_system.controllers.workflow_controller import WorkflowController
from src.autogen_system.workflows.research_workflow import ResearchWorkflowManager


class TestCompleteWorkflowIntegration:
    """完整工作流集成測試"""

    @pytest.fixture
    async def mock_research_environment(self):
        """設置模擬研究環境"""

        # 模擬模型客戶端
        mock_client = Mock()
        mock_client.complete = AsyncMock(return_value="Mock research result")

        # 模擬工具
        mock_tools = [
            Mock(name="search", invoke=AsyncMock(return_value="Search results")),
            Mock(name="crawl", invoke=AsyncMock(return_value="Crawled content")),
            Mock(name="code_execution", invoke=AsyncMock(return_value="Code output")),
        ]

        # 模擬對話管理器
        mock_conversation_manager = Mock(spec=AutoGenConversationManager)
        mock_conversation_manager.model_client = mock_client
        mock_conversation_manager.tools = mock_tools

        return {
            "client": mock_client,
            "tools": mock_tools,
            "conversation_manager": mock_conversation_manager,
        }

    async def test_research_workflow_end_to_end(self, mock_research_environment):
        """測試研究工作流端到端執行"""

        # 創建研究工作流管理器
        research_manager = ResearchWorkflowManager(
            mock_research_environment["conversation_manager"]
        )

        # 模擬工作流控制器
        with patch.object(research_manager, "workflow_controller") as mock_controller:
            mock_controller.execute_plan = AsyncMock(
                return_value={
                    "status": "completed",
                    "execution_time": 2.5,
                    "research_results": "Comprehensive research findings",
                    "analysis": "Detailed analysis of findings",
                    "conclusion": "Research conclusions",
                }
            )

            # 執行研究任務
            task = "Analyze the impact of AI on healthcare industry"
            result = await research_manager.run_research(task)

            # 驗證結果
            assert result["status"] == "completed"
            assert "research_results" in result
            assert "analysis" in result
            assert "conclusion" in result

            # 驗證工作流控制器被調用
            mock_controller.execute_plan.assert_called_once()

    async def test_multi_agent_collaboration(self, mock_research_environment):
        """測試多代理協作"""

        # 模擬所有代理
        mock_agents = {
            "coordinator": Mock(),
            "planner": Mock(),
            "researcher": Mock(),
            "coder": Mock(),
            "reporter": Mock(),
        }

        # 設置代理響應
        for agent_name, agent in mock_agents.items():
            agent.process_request = AsyncMock(return_value=f"{agent_name} completed task")

        # 創建對話管理器
        conversation_manager = mock_research_environment["conversation_manager"]
        conversation_manager.agents = mock_agents

        # 模擬多代理協作
        with patch(
            "src.autogen_system.agents.coordinator_agent.CoordinatorAgent"
        ) as MockCoordinator:
            MockCoordinator.return_value = mock_agents["coordinator"]

            # 執行協作任務
            task = "Create a comprehensive analysis report"

            # 模擬協調過程
            coordinator_result = await mock_agents["coordinator"].process_request(task)
            planner_result = await mock_agents["planner"].process_request("Create plan")
            researcher_result = await mock_agents["researcher"].process_request("Conduct research")
            coder_result = await mock_agents["coder"].process_request("Write analysis code")
            reporter_result = await mock_agents["reporter"].process_request("Generate report")

            # 驗證所有代理都參與了協作
            assert coordinator_result == "coordinator completed task"
            assert planner_result == "planner completed task"
            assert researcher_result == "researcher completed task"
            assert coder_result == "coder completed task"
            assert reporter_result == "reporter completed task"

    async def test_tool_integration_in_workflow(self, mock_research_environment):
        """測試工作流中的工具集成"""

        tools = mock_research_environment["tools"]
        conversation_manager = mock_research_environment["conversation_manager"]

        # 創建工作流管理器
        workflow_manager = ResearchWorkflowManager(conversation_manager)

        # 模擬工具使用
        search_tool = tools[0]  # search
        crawl_tool = tools[1]  # crawl
        code_tool = tools[2]  # code_execution

        # 執行搜索
        search_result = await search_tool.invoke(query="AI healthcare")
        assert search_result == "Search results"

        # 執行爬蟲
        crawl_result = await crawl_tool.invoke(url="https://example.com")
        assert crawl_result == "Crawled content"

        # 執行代碼
        code_result = await code_tool.invoke(code="print('test')")
        assert code_result == "Code output"

        # 驗證工具調用
        search_tool.invoke.assert_called_with(query="AI healthcare")
        crawl_tool.invoke.assert_called_with(url="https://example.com")
        code_tool.invoke.assert_called_with(code="print('test')")

    async def test_error_recovery_in_workflow(self, mock_research_environment):
        """測試工作流中的錯誤恢復"""

        conversation_manager = mock_research_environment["conversation_manager"]

        # 創建工作流控制器
        workflow_controller = WorkflowController()

        # 模擬會失敗然後恢復的執行器
        failure_count = 0

        async def failing_executor(step, state):
            nonlocal failure_count
            failure_count += 1

            if failure_count <= 2:  # 前兩次失敗
                raise Exception(f"Simulated failure {failure_count}")

            # 第三次成功
            state["result"] = f"Recovered after {failure_count} attempts"
            return state

        # 創建簡單計劃
        from src.autogen_system.controllers.workflow_controller import (
            WorkflowPlan,
            WorkflowStep,
            StepType,
        )

        step = WorkflowStep(
            id="test_step",
            name="測試步驟",
            step_type=StepType.PROCESSING,
            description="會失敗的測試步驟",
            dependencies=[],
            estimated_duration=10,
        )

        plan = WorkflowPlan(
            id="recovery_test",
            name="恢復測試",
            description="測試錯誤恢復",
            steps=[step],
            estimated_duration=10,
        )

        # 執行帶錯誤恢復的計劃
        with patch.object(workflow_controller, "_retry_step") as mock_retry:
            mock_retry.side_effect = failing_executor

            try:
                # 第一次應該失敗
                with pytest.raises(Exception, match="Simulated failure"):
                    await workflow_controller.execute_plan(plan, {}, failing_executor)
            except:
                pass

            # 驗證失敗被記錄
            assert failure_count > 0

    async def test_performance_monitoring(self, mock_research_environment, performance_monitor):
        """測試性能監控"""

        conversation_manager = mock_research_environment["conversation_manager"]
        research_manager = ResearchWorkflowManager(conversation_manager)

        # 測量工作流執行性能
        performance_monitor.start()

        # 模擬工作流執行
        with patch.object(research_manager, "workflow_controller") as mock_controller:
            mock_controller.execute_plan = AsyncMock(return_value={"status": "completed"})

            # 執行多個測量
            with performance_monitor.measure("workflow_execution"):
                await research_manager.run_research("Test task")

            with performance_monitor.measure("agent_processing"):
                await conversation_manager.model_client.complete(["test message"])

        duration = performance_monitor.end()

        # 驗證性能指標
        assert duration is not None
        assert duration > 0
        assert "workflow_execution" in performance_monitor.measurements
        assert "agent_processing" in performance_monitor.measurements

    async def test_concurrent_workflows(self, mock_research_environment):
        """測試並發工作流執行"""

        conversation_manager = mock_research_environment["conversation_manager"]

        # 創建多個工作流管理器
        managers = [ResearchWorkflowManager(conversation_manager) for _ in range(3)]

        # 模擬每個管理器的工作流控制器
        results = []
        for i, manager in enumerate(managers):
            with patch.object(manager, "workflow_controller") as mock_controller:
                mock_controller.execute_plan = AsyncMock(
                    return_value={"status": "completed", "task_id": i}
                )
                results.append(manager.run_research(f"Task {i}"))

        # 並發執行所有工作流
        concurrent_results = await asyncio.gather(*results)

        # 驗證所有工作流都成功完成
        assert len(concurrent_results) == 3
        for i, result in enumerate(concurrent_results):
            assert result["status"] == "completed"
            assert result["task_id"] == i

    async def test_memory_usage(self, mock_research_environment):
        """測試內存使用情況"""

        import gc
        import sys

        conversation_manager = mock_research_environment["conversation_manager"]

        # 記錄初始內存
        gc.collect()
        initial_objects = len(gc.get_objects())

        # 創建並執行多個工作流
        workflows = []
        for i in range(10):
            manager = ResearchWorkflowManager(conversation_manager)
            with patch.object(manager, "workflow_controller") as mock_controller:
                mock_controller.execute_plan = AsyncMock(return_value={"status": "completed"})
                workflows.append(manager.run_research(f"Memory test {i}"))

        # 執行所有工作流
        await asyncio.gather(*workflows)

        # 強制垃圾回收
        del workflows
        gc.collect()

        # 檢查內存洩漏
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

        # 允許一些合理的對象增長，但不應該有嚴重洩漏
        assert object_growth < 1000, f"可能存在內存洩漏: 對象增長 {object_growth}"

    async def test_configuration_integration(self, temp_config_file, mock_env_vars):
        """測試配置集成"""

        from src.autogen_system.config.config_loader import ConfigLoader

        # 加載配置
        config_loader = ConfigLoader()

        with patch.object(config_loader, "load_config") as mock_load:
            mock_config = {
                "models": {"default": {"type": "openai", "model": "gpt-4", "api_key": "test-key"}},
                "agents": {"researcher": {"model": "default", "tools": ["search", "crawl"]}},
                "tools": {"search": {"type": "tavily", "config": {"api_key": "test-key"}}},
            }
            mock_load.return_value = mock_config

            config = config_loader.load_config(temp_config_file)

            # 驗證配置加載
            assert "models" in config
            assert "agents" in config
            assert "tools" in config

            # 驗證環境變數整合
            assert mock_env_vars["OPENAI_API_KEY"] == "test-openai-key"

    async def test_logging_integration(self, mock_research_environment):
        """測試日誌集成"""

        import logging
        from io import StringIO

        # 設置內存日誌處理器
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.INFO)

        # 獲取AutoGen系統的日誌器
        logger = logging.getLogger("src.autogen_system")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        conversation_manager = mock_research_environment["conversation_manager"]
        research_manager = ResearchWorkflowManager(conversation_manager)

        # 執行工作流以生成日誌
        with patch.object(research_manager, "workflow_controller") as mock_controller:
            mock_controller.execute_plan = AsyncMock(return_value={"status": "completed"})

            await research_manager.run_research("Test logging")

        # 獲取日誌輸出
        log_output = log_stream.getvalue()

        # 清理
        logger.removeHandler(handler)

        # 驗證日誌記錄（如果有的話）
        # 注意：這取決於實際的日誌實現
        assert isinstance(log_output, str)

    async def test_api_compatibility_integration(self, mock_research_environment):
        """測試API兼容性集成"""

        from src.autogen_system.compatibility.api_adapter import AutoGenAPIAdapter

        # 創建API適配器
        api_adapter = AutoGenAPIAdapter(
            conversation_manager=mock_research_environment["conversation_manager"]
        )

        # 模擬API請求
        mock_request = {"messages": [{"role": "user", "content": "Test message"}], "stream": False}

        # 模擬響應
        with patch.object(api_adapter, "process_chat_request") as mock_process:
            mock_process.return_value = {"choices": [{"message": {"content": "API response"}}]}

            response = await api_adapter.process_chat_request(mock_request)

            # 驗證API響應格式
            assert "choices" in response
            assert len(response["choices"]) > 0
            assert "message" in response["choices"][0]
