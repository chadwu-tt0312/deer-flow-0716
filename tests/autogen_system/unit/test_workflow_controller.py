# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
WorkflowController 單元測試
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.autogen_system.controllers.workflow_controller import (
    WorkflowController,
    WorkflowStep,
    WorkflowPlan,
    StepType,
    ExecutionStatus,
)


class TestWorkflowController:
    """WorkflowController測試類"""

    @pytest.fixture
    def workflow_controller(self):
        """創建WorkflowController實例"""
        return WorkflowController()

    @pytest.fixture
    def simple_plan(self):
        """創建簡單的工作流計劃"""
        steps = [
            WorkflowStep(
                id="step1",
                name="第一步",
                step_type=StepType.RESEARCH,
                description="執行研究",
                agent_type="researcher",
                inputs={"topic": "test topic"},
                dependencies=[],
                estimated_duration=10,
            ),
            WorkflowStep(
                id="step2",
                name="第二步",
                step_type=StepType.PROCESSING,
                description="處理數據",
                agent_type="processor",
                inputs={"data": "test data"},
                dependencies=["step1"],
                estimated_duration=20,
            ),
        ]

        return WorkflowPlan(
            id="simple_plan",
            name="簡單計劃",
            description="測試用簡單計劃",
            steps=steps,
            estimated_duration=30,
        )

    async def test_execute_plan_success(self, workflow_controller, simple_plan):
        """測試成功執行工作流計劃"""

        async def mock_executor(step, state):
            """模擬步驟執行器"""
            state[f"step_{step.id}_result"] = f"完成 {step.name}"
            return state

        initial_state = {"input": "test_input"}

        # 執行計劃
        result = await workflow_controller.execute_plan(simple_plan, initial_state, mock_executor)

        # 驗證結果
        assert result["input"] == "test_input"
        assert result["step_step1_result"] == "完成 第一步"
        assert result["step_step2_result"] == "完成 第二步"
        assert "execution_time" in result
        assert "status" in result

        # 驗證步驟狀態
        for step in simple_plan.steps:
            assert step.status == ExecutionStatus.COMPLETED

    async def test_execute_plan_with_failure(self, workflow_controller, simple_plan):
        """測試執行計劃時的失敗處理"""

        async def mock_executor(step, state):
            """模擬會失敗的步驟執行器"""
            if step.id == "step2":
                raise Exception("Step2 失敗")
            state[f"step_{step.id}_result"] = f"完成 {step.name}"
            return state

        initial_state = {"input": "test_input"}

        # 執行計劃應該拋出異常
        with pytest.raises(Exception, match="Step2 失敗"):
            await workflow_controller.execute_plan(simple_plan, initial_state, mock_executor)

        # 驗證第一步成功，第二步失敗
        assert simple_plan.steps[0].status == ExecutionStatus.COMPLETED
        assert simple_plan.steps[1].status == ExecutionStatus.FAILED

    async def test_validate_plan_dependencies(self, workflow_controller):
        """測試計劃依賴驗證"""

        # 創建有循環依賴的計劃
        steps = [
            WorkflowStep(
                id="step1",
                name="第一步",
                step_type=StepType.RESEARCH,
                description="執行研究",
                agent_type="researcher",
                inputs={"topic": "test topic"},
                dependencies=["step2"],  # 循環依賴
                estimated_duration=10,
            ),
            WorkflowStep(
                id="step2",
                name="第二步",
                step_type=StepType.PROCESSING,
                description="處理數據",
                agent_type="processor",
                inputs={"data": "test data"},
                dependencies=["step1"],  # 循環依賴
                estimated_duration=20,
            ),
        ]

        invalid_plan = WorkflowPlan(
            id="invalid_plan",
            name="無效計劃",
            description="有循環依賴的計劃",
            steps=steps,
            estimated_duration=30,
        )

        # 驗證計劃應該失敗
        is_valid = workflow_controller.validate_plan(invalid_plan)
        assert not is_valid

    async def test_get_execution_order(self, workflow_controller, simple_plan):
        """測試獲取執行順序"""

        execution_order = workflow_controller.get_execution_order(simple_plan)

        # 驗證執行順序
        assert len(execution_order) == 2
        assert execution_order[0].id == "step1"  # 無依賴的步驟先執行
        assert execution_order[1].id == "step2"  # 有依賴的步驟後執行

    async def test_complex_dependencies(self, workflow_controller):
        """測試複雜依賴關係"""

        steps = [
            WorkflowStep(
                id="step1",
                name="第一步",
                step_type=StepType.RESEARCH,
                description="執行研究",
                agent_type="researcher",
                inputs={"topic": "test topic"},
                dependencies=[],
                estimated_duration=10,
            ),
            WorkflowStep(
                id="step2",
                name="第二步",
                step_type=StepType.PROCESSING,
                description="處理數據",
                agent_type="processor",
                inputs={"data": "test data"},
                dependencies=["step1"],
                estimated_duration=20,
            ),
            WorkflowStep(
                id="step3",
                name="第三步",
                step_type=StepType.ANALYSIS,
                description="分析結果",
                agent_type="analyzer",
                inputs={"data": "analysis data"},
                dependencies=["step1"],  # 只依賴step1
                estimated_duration=15,
            ),
            WorkflowStep(
                id="step4",
                name="第四步",
                step_type=StepType.SYNTHESIS,
                description="綜合結論",
                agent_type="synthesizer",
                inputs={"conclusions": "synthesis data"},
                dependencies=["step2", "step3"],  # 依賴step2和step3
                estimated_duration=25,
            ),
        ]

        complex_plan = WorkflowPlan(
            id="complex_plan",
            name="複雜計劃",
            description="有複雜依賴關係的計劃",
            steps=steps,
            estimated_duration=70,
        )

        # 驗證計劃有效
        assert workflow_controller.validate_plan(complex_plan)

        # 獲取執行順序
        execution_order = workflow_controller.get_execution_order(complex_plan)

        # 驗證執行順序
        step_ids = [step.id for step in execution_order]

        # step1 必須在最前面
        assert step_ids[0] == "step1"

        # step2 和 step3 必須在 step1 之後，step4 之前
        step1_index = step_ids.index("step1")
        step2_index = step_ids.index("step2")
        step3_index = step_ids.index("step3")
        step4_index = step_ids.index("step4")

        assert step2_index > step1_index
        assert step3_index > step1_index
        assert step4_index > step2_index
        assert step4_index > step3_index

    async def test_parallel_execution(self, workflow_controller):
        """測試並行執行能力"""

        steps = [
            WorkflowStep(
                id="step1",
                name="第一步",
                step_type=StepType.RESEARCH,
                description="執行研究",
                agent_type="researcher",
                inputs={"topic": "test topic"},
                dependencies=[],
                estimated_duration=10,
            ),
            WorkflowStep(
                id="step2a",
                name="第二步A",
                step_type=StepType.PROCESSING,
                description="處理數據A",
                agent_type="processor_a",
                inputs={"data": "data a"},
                dependencies=["step1"],
                estimated_duration=20,
            ),
            WorkflowStep(
                id="step2b",
                name="第二步B",
                step_type=StepType.PROCESSING,
                description="處理數據B",
                agent_type="processor_b",
                inputs={"data": "data b"},
                dependencies=["step1"],
                estimated_duration=20,
            ),
        ]

        parallel_plan = WorkflowPlan(
            id="parallel_plan",
            name="並行計劃",
            description="可並行執行的計劃",
            steps=steps,
            estimated_duration=50,
        )

        execution_times = []

        async def timing_executor(step, state):
            """記錄執行時間的執行器"""
            import time

            start_time = time.time()
            await asyncio.sleep(0.1)  # 模擬處理時間
            end_time = time.time()

            execution_times.append(
                {
                    "step_id": step.id,
                    "start_time": start_time,
                    "end_time": end_time,
                }
            )

            state[f"step_{step.id}_result"] = f"完成 {step.name}"
            return state

        initial_state = {"input": "test_input"}

        # 執行計劃
        await workflow_controller.execute_plan(parallel_plan, initial_state, timing_executor)

        # 驗證所有步驟都執行了
        assert len(execution_times) == 3

        # 找到各步驟的執行時間
        step1_time = next(t for t in execution_times if t["step_id"] == "step1")
        step2a_time = next(t for t in execution_times if t["step_id"] == "step2a")
        step2b_time = next(t for t in execution_times if t["step_id"] == "step2b")

        # 驗證step1在step2a和step2b之前完成
        assert step1_time["end_time"] <= step2a_time["start_time"]
        assert step1_time["end_time"] <= step2b_time["start_time"]

    def test_step_type_enum(self):
        """測試步驟類型枚舉"""

        # 驗證所有步驟類型都存在
        expected_types = [
            "research",
            "processing",
            "code",
            "analysis",
            "validation",
            "synthesis",
            "script_generation",
            "tts_generation",
            "audio_mixing",
            "outline_generation",
            "slide_generation",
            "ppt_creation",
            "prose_planning",
            "content_generation",
            "style_refinement",
            "prompt_analysis",
            "enhancement_generation",
            "prompt_validation",
        ]

        for type_name in expected_types:
            assert hasattr(StepType, type_name.upper())

    def test_execution_status_enum(self):
        """測試執行狀態枚舉"""

        # 驗證所有執行狀態都存在
        expected_statuses = ["pending", "in_progress", "completed", "failed", "cancelled"]

        for status_name in expected_statuses:
            assert hasattr(ExecutionStatus, status_name.upper())

    async def test_workflow_step_metadata(self, workflow_controller):
        """測試工作流步驟元數據"""

        metadata = {"custom_param": "value", "retry_count": 3}

        step = WorkflowStep(
            id="meta_step",
            name="帶元數據的步驟",
            step_type=StepType.PROCESSING,
            description="測試元數據",
            agent_type="processor",
            inputs={"data": "test data"},
            dependencies=[],
            estimated_duration=10,
            metadata=metadata,
        )

        # 驗證元數據正確設置
        assert step.metadata == metadata
        assert step.metadata["custom_param"] == "value"
        assert step.metadata["retry_count"] == 3

    async def test_plan_validation_edge_cases(self, workflow_controller):
        """測試計劃驗證的邊界情況"""

        # 測試空計劃
        empty_plan = WorkflowPlan(
            id="empty_plan",
            name="空計劃",
            description="沒有步驟的計劃",
            steps=[],
            estimated_duration=0,
        )

        assert not workflow_controller.validate_plan(empty_plan)

        # 測試引用不存在依賴的計劃
        steps = [
            WorkflowStep(
                id="step1",
                name="第一步",
                step_type=StepType.RESEARCH,
                description="執行研究",
                agent_type="researcher",
                inputs={"topic": "test topic"},
                dependencies=["nonexistent_step"],  # 不存在的依賴
                estimated_duration=10,
            ),
        ]

        invalid_deps_plan = WorkflowPlan(
            id="invalid_deps_plan",
            name="無效依賴計劃",
            description="有無效依賴的計劃",
            steps=steps,
            estimated_duration=10,
        )

        assert not workflow_controller.validate_plan(invalid_deps_plan)
