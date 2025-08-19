# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen Agents 單元測試
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.autogen_system.agents.base_agent import BaseResearchAgent as BaseAgent
from src.autogen_system.agents.coordinator_agent import CoordinatorAgent
from src.autogen_system.agents.planner_agent import PlannerAgent
from src.autogen_system.agents.researcher_agent import ResearcherAgent
from src.autogen_system.agents.coder_agent import CoderAgent
from src.autogen_system.agents.reporter_agent import ReporterAgent


class TestBaseAgent:
    """BaseAgent測試類"""

    @pytest.fixture
    def mock_model_client(self):
        """模擬模型客戶端"""
        client = Mock()
        client.complete = AsyncMock(return_value="Mock response")
        return client

    @pytest.fixture
    def mock_tools(self):
        """模擬工具列表"""
        return [Mock(name="search"), Mock(name="code_execution")]

    def test_base_agent_initialization(self, mock_model_client, mock_tools, mock_config):
        """測試BaseAgent初始化"""

        agent = BaseAgent(config=mock_config, tools=mock_tools)

        assert agent.config == mock_config
        assert agent.tools == mock_tools

    async def test_base_agent_process_request(self, mock_model_client, mock_tools, mock_config):
        """測試BaseAgent處理請求"""

        agent = BaseAgent(config=mock_config, tools=mock_tools)

        request = "Test request"
        response = await agent.process_request(request)

        assert response == "Mock response"
        mock_model_client.complete.assert_called_once()

    def test_base_agent_add_tool(self, mock_model_client, mock_tools, mock_config):
        """測試添加工具"""

        agent = BaseAgent(config=mock_config, tools=mock_tools)

        new_tool = Mock(name="new_tool")
        agent.add_tool(new_tool)

        assert new_tool in agent.tools
        assert len(agent.tools) == 3

    def test_base_agent_remove_tool(self, mock_model_client, mock_tools, mock_config):
        """測試移除工具"""

        agent = BaseAgent(config=mock_config, tools=mock_tools)

        tool_to_remove = mock_tools[0]
        tool_name = getattr(tool_to_remove, "__name__", str(tool_to_remove))
        agent.remove_tool(tool_name)

        assert tool_to_remove not in agent.tools
        assert len(agent.tools) == 1


class TestCoordinatorAgent:
    """CoordinatorAgent測試類"""

    @pytest.fixture
    def coordinator_agent(self, mock_model_client, mock_tools, mock_config):
        """創建CoordinatorAgent實例"""
        return CoordinatorAgent(config=mock_config, tools=mock_tools)

    async def test_coordinate_agents(self, coordinator_agent):
        """測試代理協調"""

        mock_agents = [
            Mock(name="researcher", process_request=AsyncMock(return_value="Research done")),
            Mock(name="coder", process_request=AsyncMock(return_value="Code written")),
        ]

        task = "Complete a research and coding task"

        # 模擬協調過程
        with patch.object(
            coordinator_agent, "process_request", return_value="Coordination complete"
        ):
            result = await coordinator_agent.coordinate_agents(mock_agents, task)

        assert result == "Coordination complete"

    async def test_delegate_task(self, coordinator_agent):
        """測試任務委派"""

        task = "Search for information about AI"
        agent_type = "researcher"

        with patch.object(coordinator_agent, "process_request", return_value="Task delegated"):
            result = await coordinator_agent.delegate_task(task, agent_type)

        assert result == "Task delegated"

    async def test_workflow_coordination(self, coordinator_agent):
        """測試工作流協調"""

        workflow_steps = [
            {"agent": "researcher", "task": "Research AI trends"},
            {"agent": "coder", "task": "Implement analysis code"},
            {"agent": "reporter", "task": "Generate report"},
        ]

        with patch.object(
            coordinator_agent, "process_request", return_value="Workflow coordinated"
        ):
            result = await coordinator_agent.coordinate_workflow(workflow_steps)

        assert result == "Workflow coordinated"


class TestPlannerAgent:
    """PlannerAgent測試類"""

    @pytest.fixture
    def planner_agent(self, mock_model_client, mock_tools, mock_config):
        """創建PlannerAgent實例"""
        return PlannerAgent(config=mock_config, tools=mock_tools)

    async def test_create_plan(self, planner_agent):
        """測試創建計劃"""

        task = "Analyze market trends in AI industry"

        with patch.object(
            planner_agent.model_client, "complete", return_value="Detailed plan created"
        ):
            plan = await planner_agent.create_plan(task)

        assert plan == "Detailed plan created"
        planner_agent.model_client.complete.assert_called_once()

    async def test_refine_plan(self, planner_agent):
        """測試優化計劃"""

        initial_plan = "Basic plan"
        feedback = "Need more detail in step 2"

        with patch.object(planner_agent.model_client, "complete", return_value="Refined plan"):
            refined_plan = await planner_agent.refine_plan(initial_plan, feedback)

        assert refined_plan == "Refined plan"

    async def test_validate_plan(self, planner_agent):
        """測試驗證計劃"""

        plan = "Test plan with steps"

        with patch.object(planner_agent, "process_request", return_value="Plan is valid"):
            result = await planner_agent.validate_plan(plan)

        assert result == "Plan is valid"

    async def test_decompose_task(self, planner_agent):
        """測試任務分解"""

        complex_task = "Build a complete AI-powered application"

        with patch.object(
            planner_agent, "process_request", return_value="Task decomposed into steps"
        ):
            decomposition = await planner_agent.decompose_task(complex_task)

        assert decomposition == "Task decomposed into steps"


class TestResearcherAgent:
    """ResearcherAgent測試類"""

    @pytest.fixture
    def researcher_agent(self, mock_model_client, mock_tools, mock_config):
        """創建ResearcherAgent實例"""
        return ResearcherAgent(config=mock_config, tools=mock_tools)

    async def test_conduct_research(self, researcher_agent):
        """測試進行研究"""

        topic = "Latest developments in machine learning"

        with patch.object(researcher_agent, "process_request", return_value="Research findings"):
            result = await researcher_agent.conduct_research(topic)

        assert result == "Research findings"

    async def test_search_information(self, researcher_agent):
        """測試搜索信息"""

        query = "AI trends 2024"

        # 模擬搜索工具
        search_tool = Mock()
        search_tool.name = "search"
        search_tool.invoke = AsyncMock(return_value="Search results")
        researcher_agent.tools = [search_tool]

        result = await researcher_agent.search_information(query)

        assert result == "Search results"
        search_tool.invoke.assert_called_once()

    async def test_analyze_sources(self, researcher_agent):
        """測試分析來源"""

        sources = ["source1", "source2", "source3"]

        with patch.object(researcher_agent, "process_request", return_value="Source analysis"):
            analysis = await researcher_agent.analyze_sources(sources)

        assert analysis == "Source analysis"

    async def test_gather_background_info(self, researcher_agent):
        """測試收集背景信息"""

        topic = "Quantum computing applications"

        with patch.object(
            researcher_agent, "process_request", return_value="Background information"
        ):
            info = await researcher_agent.gather_background_info(topic)

        assert info == "Background information"


class TestCoderAgent:
    """CoderAgent測試類"""

    @pytest.fixture
    def coder_agent(self, mock_model_client, mock_tools, mock_config):
        """創建CoderAgent實例"""
        return CoderAgent(config=mock_config, tools=mock_tools)

    async def test_write_code(self, coder_agent):
        """測試編寫代碼"""

        requirements = "Create a function to calculate fibonacci numbers"

        with patch.object(coder_agent, "process_request", return_value="def fibonacci(n): ..."):
            code = await coder_agent.write_code(requirements)

        assert code == "def fibonacci(n): ..."

    async def test_execute_code(self, coder_agent):
        """測試執行代碼"""

        code = "print('Hello, World!')"

        # 模擬代碼執行工具
        exec_tool = Mock()
        exec_tool.name = "code_execution"
        exec_tool.invoke = AsyncMock(return_value="Hello, World!")
        coder_agent.tools = [exec_tool]

        result = await coder_agent.execute_code(code)

        assert result == "Hello, World!"
        exec_tool.invoke.assert_called_once()

    async def test_debug_code(self, coder_agent):
        """測試調試代碼"""

        code = "buggy code"
        error_message = "SyntaxError: invalid syntax"

        with patch.object(coder_agent, "process_request", return_value="Fixed code"):
            fixed_code = await coder_agent.debug_code(code, error_message)

        assert fixed_code == "Fixed code"

    async def test_optimize_code(self, coder_agent):
        """測試優化代碼"""

        code = "inefficient code"

        with patch.object(coder_agent, "process_request", return_value="Optimized code"):
            optimized = await coder_agent.optimize_code(code)

        assert optimized == "Optimized code"

    async def test_generate_tests(self, coder_agent):
        """測試生成測試代碼"""

        code = "def add(a, b): return a + b"

        with patch.object(coder_agent, "process_request", return_value="Test code"):
            tests = await coder_agent.generate_tests(code)

        assert tests == "Test code"


class TestReporterAgent:
    """ReporterAgent測試類"""

    @pytest.fixture
    def reporter_agent(self, mock_model_client, mock_tools, mock_config):
        """創建ReporterAgent實例"""
        return ReporterAgent(config=mock_config, tools=mock_tools)

    async def test_generate_report(self, reporter_agent):
        """測試生成報告"""

        data = {"findings": "test findings", "analysis": "test analysis"}
        report_type = "summary"

        with patch.object(reporter_agent, "process_request", return_value="Generated report"):
            report = await reporter_agent.generate_report(data, report_type)

        assert report == "Generated report"

    async def test_format_results(self, reporter_agent):
        """測試格式化結果"""

        raw_results = "raw data"
        format_type = "markdown"

        with patch.object(reporter_agent, "process_request", return_value="Formatted results"):
            formatted = await reporter_agent.format_results(raw_results, format_type)

        assert formatted == "Formatted results"

    async def test_create_summary(self, reporter_agent):
        """測試創建摘要"""

        content = "Long detailed content"

        with patch.object(reporter_agent, "process_request", return_value="Summary"):
            summary = await reporter_agent.create_summary(content)

        assert summary == "Summary"

    async def test_generate_visualizations(self, reporter_agent):
        """測試生成視覺化"""

        data = {"x": [1, 2, 3], "y": [1, 4, 9]}
        chart_type = "line"

        with patch.object(reporter_agent, "process_request", return_value="Visualization code"):
            viz = await reporter_agent.generate_visualizations(data, chart_type)

        assert viz == "Visualization code"

    async def test_compile_final_report(self, reporter_agent):
        """測試編譯最終報告"""

        sections = {
            "introduction": "Introduction text",
            "analysis": "Analysis text",
            "conclusion": "Conclusion text",
        }

        with patch.object(reporter_agent, "process_request", return_value="Final report"):
            final_report = await reporter_agent.compile_final_report(sections)

        assert final_report == "Final report"


class TestAgentIntegration:
    """代理集成測試"""

    @pytest.fixture
    def all_agents(self, mock_model_client, mock_tools, mock_config):
        """創建所有代理實例"""
        return {
            "coordinator": CoordinatorAgent(config=mock_config, tools=mock_tools),
            "planner": PlannerAgent(config=mock_config, tools=mock_tools),
            "researcher": ResearcherAgent(config=mock_config, tools=mock_tools),
            "coder": CoderAgent(config=mock_config, tools=mock_tools),
            "reporter": ReporterAgent(config=mock_config, tools=mock_tools),
        }

    async def test_agent_communication(self, all_agents):
        """測試代理間通信"""

        coordinator = all_agents["coordinator"]
        planner = all_agents["planner"]

        # 模擬代理間通信
        with patch.object(coordinator, "process_request", return_value="Task delegated"):
            with patch.object(planner, "process_request", return_value="Plan created"):
                # 協調員委派任務給計劃員
                result = await coordinator.delegate_task("Create a plan", "planner")
                assert result == "Task delegated"

                # 計劃員創建計劃
                plan = await planner.create_plan("Create analysis workflow")
                assert plan == "Plan created"

    async def test_workflow_execution(self, all_agents):
        """測試工作流執行"""

        # 模擬完整工作流
        coordinator = all_agents["coordinator"]
        researcher = all_agents["researcher"]
        coder = all_agents["coder"]
        reporter = all_agents["reporter"]

        with patch.object(researcher, "process_request", return_value="Research completed"):
            with patch.object(coder, "process_request", return_value="Code written"):
                with patch.object(reporter, "process_request", return_value="Report generated"):
                    # 執行研究
                    research_result = await researcher.conduct_research("AI trends")
                    assert research_result == "Research completed"

                    # 編寫代碼
                    code_result = await coder.write_code("Analysis script")
                    assert code_result == "Code written"

                    # 生成報告
                    report_result = await reporter.generate_report({}, "summary")
                    assert report_result == "Report generated"

    def test_agent_inheritance(self, all_agents):
        """測試代理繼承關係"""

        # 所有代理都應該繼承自BaseAgent
        for agent_name, agent in all_agents.items():
            assert isinstance(agent, BaseAgent)
            assert hasattr(agent, "name")
            assert hasattr(agent, "tools")
                        # 檢查是否有任何處理方法（不同類型的代理可能有不同的方法）
            has_processing_method = (
                hasattr(agent, "process_request") or
                hasattr(agent, "a_generate_reply") or
                hasattr(agent, "a_send") or
                hasattr(agent, "send") or
                hasattr(agent, "process_user_input") or
                hasattr(agent, "create_research_plan") or
                hasattr(agent, "conduct_research") or
                hasattr(agent, "write_code") or
                hasattr(agent, "generate_report") or
                hasattr(agent, "execute_code") or
                hasattr(agent, "analyze_and_implement") or
                hasattr(agent, "generate_final_report") or
                hasattr(agent, "format_final_report")
            )
            assert has_processing_method, f"Agent {agent_name} missing processing method"

    async def test_error_handling(self, all_agents):
        """測試錯誤處理"""

        agent = all_agents["coordinator"]

        # 模擬模型客戶端錯誤
        agent.model_client.complete = AsyncMock(side_effect=Exception("Model error"))

        with pytest.raises(Exception, match="Model error"):
            await agent.process_request("Test request")

    async def test_concurrent_agents(self, all_agents):
        """測試並發代理執行"""

        # 準備多個代理任務
        tasks = []
        for agent_name, agent in all_agents.items():
            with patch.object(agent, "process_request", return_value=f"{agent_name} result"):
                task = agent.process_request(f"Task for {agent_name}")
                tasks.append(task)

        # 並發執行所有任務
        results = await asyncio.gather(*tasks)

        # 驗證所有結果
        expected_results = [f"{name} result" for name in all_agents.keys()]
        assert set(results) == set(expected_results)
