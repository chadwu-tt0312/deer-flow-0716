# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 工作流控制器

為 AutoGen 提供複雜條件分支和流程控制邏輯，彌補其在複雜工作流方面的限制。
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.logging import get_logger

logger = get_logger(__name__)


class StepType(Enum):
    """步驟類型"""

    RESEARCH = "research"
    PROCESSING = "processing"
    CODE = "code"
    ANALYSIS = "analysis"
    VALIDATION = "validation"
    SYNTHESIS = "synthesis"

    # Podcast工作流步驟類型
    SCRIPT_GENERATION = "script_generation"
    TTS_GENERATION = "tts_generation"
    AUDIO_MIXING = "audio_mixing"

    # PPT工作流步驟類型
    OUTLINE_GENERATION = "outline_generation"
    SLIDE_GENERATION = "slide_generation"
    PPT_CREATION = "ppt_creation"

    # Prose工作流步驟類型
    PROSE_PLANNING = "prose_planning"
    CONTENT_GENERATION = "content_generation"
    STYLE_REFINEMENT = "style_refinement"

    # PromptEnhancer工作流步驟類型
    PROMPT_ANALYSIS = "prompt_analysis"
    ENHANCEMENT_GENERATION = "enhancement_generation"
    PROMPT_VALIDATION = "prompt_validation"


class ExecutionStatus(Enum):
    """執行狀態"""

    PENDING = "pending"
    RUNNING = "running"
    IN_PROGRESS = "running"  # 為了兼容測試，添加別名
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """工作流步驟"""

    id: str
    step_type: StepType
    description: str
    agent_type: str
    inputs: Dict[str, Any]
    dependencies: List[str] = None
    conditions: Dict[str, Any] = None
    timeout_seconds: int = 300
    retry_count: int = 2
    # 為了兼容測試，添加 name 字段
    name: Optional[str] = None
    # 為了兼容測試，添加 expected_output 和 estimated_duration 字段
    expected_output: Optional[str] = None
    estimated_duration: Optional[int] = None
    # 為了兼容測試，添加 metadata 字段
    metadata: Optional[Dict[str, Any]] = None

    # 執行狀態
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class WorkflowPlan:
    """工作流計劃"""

    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    metadata: Dict[str, Any] = None
    # 為了兼容測試，添加 estimated_duration 字段
    estimated_duration: Optional[int] = None
    # 為了兼容測試，添加 plan_id 字段
    plan_id: Optional[str] = None

    # 計劃狀態
    status: ExecutionStatus = ExecutionStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class WorkflowController:
    """
    工作流控制器

    提供複雜的條件分支、依賴管理、錯誤處理等工作流控制功能。
    """

    def __init__(self):
        """初始化工作流控制器"""
        self.current_plan: Optional[WorkflowPlan] = None
        self.execution_context: Dict[str, Any] = {}
        self.step_handlers: Dict[StepType, Callable] = {}
        self.condition_evaluators: Dict[str, Callable] = {}
        self.execution_history: List[Dict[str, Any]] = []

        # 設置預設條件評估器
        self._setup_default_evaluators()

        logger.info("工作流控制器初始化完成")

    def _setup_default_evaluators(self):
        """設置預設條件評估器"""
        self.condition_evaluators.update(
            {
                "always": lambda context, condition: True,
                "never": lambda context, condition: False,
                "has_result": lambda context, condition: bool(context.get(condition.get("key"))),
                "result_contains": lambda context, condition: condition.get("value")
                in str(context.get(condition.get("key"), "")),
                "step_completed": lambda context, condition: self._is_step_completed(
                    condition.get("step_id")
                ),
                "step_failed": lambda context, condition: self._is_step_failed(
                    condition.get("step_id")
                ),
                "result_count_gt": lambda context, condition: len(
                    context.get(condition.get("key"), [])
                )
                > condition.get("value", 0),
            }
        )

    def register_step_handler(self, step_type: StepType, handler: Callable):
        """
        註冊步驟處理器

        Args:
            step_type: 步驟類型
            handler: 處理器函數
        """
        self.step_handlers[step_type] = handler
        logger.info(f"註冊步驟處理器: {step_type.value}")

    def register_condition_evaluator(self, name: str, evaluator: Callable):
        """
        註冊條件評估器

        Args:
            name: 條件名稱
            evaluator: 評估器函數
        """
        self.condition_evaluators[name] = evaluator
        logger.info(f"註冊條件評估器: {name}")

    async def execute_plan(
        self, plan: WorkflowPlan, context: Dict[str, Any] = None, executor_func=None
    ) -> Dict[str, Any]:
        """
        執行工作流計劃

        Args:
            plan: 工作流計劃
            context: 執行上下文
            executor_func: 步驟執行器函數（可選）

        Returns:
            Dict[str, Any]: 執行結果
        """
        logger.info(f"開始執行工作流計劃: {plan.name}")

        self.current_plan = plan
        self.execution_context = context or {}
        self.executor_func = executor_func

        # 記錄計劃開始
        plan.status = ExecutionStatus.RUNNING
        plan.started_at = datetime.now()

        try:
            # 執行所有步驟
            if executor_func:
                await self._execute_all_steps_with_executor()
            else:
                await self._execute_all_steps()

            # 檢查執行結果
            if self._all_critical_steps_completed():
                plan.status = ExecutionStatus.COMPLETED
                logger.info(f"工作流計劃執行完成: {plan.name}")
            else:
                plan.status = ExecutionStatus.FAILED
                logger.error(f"工作流計劃執行失敗: {plan.name}")

        except Exception as e:
            plan.status = ExecutionStatus.FAILED
            logger.error(f"工作流計劃執行異常: {e}")
            raise

        finally:
            plan.completed_at = datetime.now()

            # 記錄執行歷史
            self.execution_history.append(
                {
                    "plan_id": plan.id,
                    "plan_name": plan.name,
                    "status": plan.status.value,
                    "steps_completed": len(
                        [s for s in plan.steps if s.status == ExecutionStatus.COMPLETED]
                    ),
                    "total_steps": len(plan.steps),
                    "execution_time": (plan.completed_at - plan.started_at).total_seconds(),
                    "timestamp": plan.completed_at.isoformat(),
                }
            )

        return self._get_execution_summary()

    async def _execute_all_steps(self):
        """執行所有步驟"""
        max_iterations = len(self.current_plan.steps) * 2  # 防止無限循環
        iteration = 0

        while iteration < max_iterations:
            # 找到可執行的步驟
            executable_steps = self._get_executable_steps()

            if not executable_steps:
                # 沒有可執行步驟，檢查是否完成
                if self._all_steps_processed():
                    break
                else:
                    logger.warning("沒有可執行步驟，但仍有未完成步驟")
                    break

            # 並行執行可執行步驟
            await self._execute_steps_batch(executable_steps)

            iteration += 1

        if iteration >= max_iterations:
            logger.warning("達到最大迭代次數，可能存在循環依賴")

    async def _execute_all_steps_with_executor(self):
        """使用執行器函數執行所有步驟"""
        max_iterations = len(self.current_plan.steps) * 2  # 防止無限循環
        iteration = 0

        while iteration < max_iterations:
            # 找到可執行的步驟
            executable_steps = self._get_executable_steps()

            if not executable_steps:
                # 沒有可執行步驟，檢查是否完成
                if self._all_steps_processed():
                    break
                else:
                    logger.warning("沒有可執行步驟，但仍有未完成步驟")
                    break

            # 使用執行器函數執行步驟
            for step in executable_steps:
                try:
                    step.status = ExecutionStatus.RUNNING
                    step.started_at = datetime.now()

                    # 調用執行器函數
                    result = await self.executor_func(step, self.execution_context)

                    # 更新步驟狀態
                    step.status = ExecutionStatus.COMPLETED
                    step.completed_at = datetime.now()
                    step.result = result

                    # 更新執行上下文
                    self.execution_context.update(result)

                    logger.info(f"步驟 {step.name} 執行完成")

                except Exception as e:
                    step.status = ExecutionStatus.FAILED
                    step.completed_at = datetime.now()
                    step.error_message = str(e)
                    logger.error(f"步驟 {step.name} 執行失敗: {e}")

            iteration += 1

        if iteration >= max_iterations:
            logger.warning("達到最大迭代次數，可能存在循環依賴")

    def _get_executable_steps(self) -> List[WorkflowStep]:
        """獲取可執行的步驟"""
        executable_steps = []

        for step in self.current_plan.steps:
            if step.status != ExecutionStatus.PENDING:
                continue

            # 檢查依賴
            if not self._check_dependencies(step):
                continue

            # 檢查條件
            if not self._check_conditions(step):
                continue

            executable_steps.append(step)

        return executable_steps

    def _check_dependencies(self, step: WorkflowStep) -> bool:
        """檢查步驟依賴"""
        if not step.dependencies:
            return True

        for dep_id in step.dependencies:
            dep_step = self._find_step_by_id(dep_id)
            if not dep_step or dep_step.status != ExecutionStatus.COMPLETED:
                return False

        return True

    def _check_conditions(self, step: WorkflowStep) -> bool:
        """檢查步驟條件"""
        if not step.conditions:
            return True

        condition_type = step.conditions.get("type", "always")
        evaluator = self.condition_evaluators.get(condition_type)

        if not evaluator:
            logger.warning(f"未知條件類型: {condition_type}")
            return True

        try:
            result = evaluator(self.execution_context, step.conditions)
            return bool(result)
        except Exception as e:
            logger.error(f"條件評估失敗: {e}")
            return False

    async def _execute_steps_batch(self, steps: List[WorkflowStep]):
        """批次執行步驟"""
        if not steps:
            return

        logger.info(f"批次執行 {len(steps)} 個步驟")

        # 創建執行任務
        tasks = []
        for step in steps:
            task = asyncio.create_task(self._execute_single_step(step))
            tasks.append(task)

        # 等待所有任務完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 處理結果
        for i, result in enumerate(results):
            step = steps[i]
            if isinstance(result, Exception):
                logger.error(f"步驟執行異常 {step.id}: {result}")
                step.status = ExecutionStatus.FAILED
                step.error_message = str(result)

    async def _execute_single_step(self, step: WorkflowStep):
        """執行單個步驟"""
        logger.info(f"執行步驟: {step.id} ({step.step_type.value})")

        step.status = ExecutionStatus.RUNNING
        step.started_at = datetime.now()

        try:
            # 獲取步驟處理器
            handler = self.step_handlers.get(step.step_type)
            if not handler:
                raise ValueError(f"未註冊步驟處理器: {step.step_type.value}")

            # 執行步驟，設置超時
            step_result = await asyncio.wait_for(
                handler(step, self.execution_context), timeout=step.timeout_seconds
            )

            # 更新結果
            step.result = step_result
            step.status = ExecutionStatus.COMPLETED

            # 更新執行上下文
            if step_result:
                self.execution_context[f"step_{step.id}_result"] = step_result

            logger.info(f"步驟執行成功: {step.id}")

        except asyncio.TimeoutError:
            step.status = ExecutionStatus.FAILED
            step.error_message = f"步驟執行超時（{step.timeout_seconds}秒）"
            logger.error(f"步驟執行超時: {step.id}")

        except Exception as e:
            step.status = ExecutionStatus.FAILED
            step.error_message = str(e)
            logger.error(f"步驟執行失敗 {step.id}: {e}")

        finally:
            step.completed_at = datetime.now()
            if step.started_at:
                step.execution_time = (step.completed_at - step.started_at).total_seconds()

    def _find_step_by_id(self, step_id: str) -> Optional[WorkflowStep]:
        """根據ID查找步驟"""
        for step in self.current_plan.steps:
            if step.id == step_id:
                return step
        return None

    def _is_step_completed(self, step_id: str) -> bool:
        """檢查步驟是否完成"""
        step = self._find_step_by_id(step_id)
        return step and step.status == ExecutionStatus.COMPLETED

    def _is_step_failed(self, step_id: str) -> bool:
        """檢查步驟是否失敗"""
        step = self._find_step_by_id(step_id)
        return step and step.status == ExecutionStatus.FAILED

    def _all_steps_processed(self) -> bool:
        """檢查所有步驟是否已處理"""
        for step in self.current_plan.steps:
            if step.status == ExecutionStatus.PENDING:
                return False
        return True

    def _all_critical_steps_completed(self) -> bool:
        """檢查所有關鍵步驟是否完成"""
        for step in self.current_plan.steps:
            # 如果步驟有critical標記且未完成，則計劃失敗
            if (
                step.metadata
                and step.metadata.get("critical", False)
                and step.status != ExecutionStatus.COMPLETED
            ):
                return False

        # 至少要有一個步驟成功完成
        completed_steps = [
            s for s in self.current_plan.steps if s.status == ExecutionStatus.COMPLETED
        ]
        return len(completed_steps) > 0

    def _get_execution_summary(self) -> Dict[str, Any]:
        """獲取執行摘要"""
        if not self.current_plan:
            return {}

        steps_by_status = {}
        for status in ExecutionStatus:
            steps_by_status[status.value] = len(
                [s for s in self.current_plan.steps if s.status == status]
            )

        return {
            "plan_id": self.current_plan.id,
            "plan_name": self.current_plan.name,
            "plan_status": self.current_plan.status.value,
            "total_steps": len(self.current_plan.steps),
            "steps_by_status": steps_by_status,
            "execution_time": (
                (self.current_plan.completed_at - self.current_plan.started_at).total_seconds()
                if self.current_plan.completed_at and self.current_plan.started_at
                else 0
            ),
            "context_keys": list(self.execution_context.keys()),
            "error_messages": [s.error_message for s in self.current_plan.steps if s.error_message],
        }

    def get_step_results(self, step_type: StepType = None) -> List[Dict[str, Any]]:
        """獲取步驟結果"""
        if not self.current_plan:
            return []

        results = []
        for step in self.current_plan.steps:
            if step_type and step.step_type != step_type:
                continue

            results.append(
                {
                    "id": step.id,
                    "type": step.step_type.value,
                    "status": step.status.value,
                    "result": step.result,
                    "error": step.error_message,
                    "execution_time": step.execution_time,
                }
            )

        return results


# 便利函數
def create_research_workflow_plan(
    research_topic: str, max_search_results: int = 5, enable_code_analysis: bool = True
) -> WorkflowPlan:
    """創建研究工作流計劃"""

    steps = [
        WorkflowStep(
            id="initial_research",
            step_type=StepType.RESEARCH,
            description=f"對主題 '{research_topic}' 進行初步研究",
            agent_type="researcher",
            inputs={
                "topic": research_topic,
                "max_results": max_search_results,
                "search_type": "web",
            },
            metadata={"critical": True},
        ),
        WorkflowStep(
            id="deep_analysis",
            step_type=StepType.ANALYSIS,
            description="深度分析研究結果",
            agent_type="researcher",
            inputs={"analysis_type": "comprehensive"},
            dependencies=["initial_research"],
            conditions={"type": "has_result", "key": "step_initial_research_result"},
        ),
    ]

    if enable_code_analysis:
        steps.append(
            WorkflowStep(
                id="code_analysis",
                step_type=StepType.CODE,
                description="程式碼分析和處理",
                agent_type="coder",
                inputs={"analysis_type": "data_processing"},
                dependencies=["deep_analysis"],
                conditions={
                    "type": "result_contains",
                    "key": "step_deep_analysis_result",
                    "value": "code",
                },
            )
        )

    return WorkflowPlan(
        id=f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        name=f"研究工作流: {research_topic}",
        description=f"針對 '{research_topic}' 的綜合研究工作流",
        steps=steps,
        metadata={"topic": research_topic, "created_by": "workflow_controller"},
    )
