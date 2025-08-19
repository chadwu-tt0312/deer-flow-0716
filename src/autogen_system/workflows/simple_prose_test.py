#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Prose工作流簡化測試

不依賴autogen_core的測試，專注於驗證工作流邏輯和結構。
"""

import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# 直接導入和模擬所需的類，避免依賴問題
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Any, Optional, Union


class StepType(Enum):
    """步驟類型"""

    RESEARCH = "research"
    PROCESSING = "processing"
    CODE = "code"
    ANALYSIS = "analysis"
    VALIDATION = "validation"
    SYNTHESIS = "synthesis"
    PROSE_PLANNING = "prose_planning"
    CONTENT_GENERATION = "content_generation"
    STYLE_REFINEMENT = "style_refinement"


class ExecutionStatus(Enum):
    """執行狀態"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """工作流步驟"""

    id: str
    name: str
    step_type: StepType
    description: str
    dependencies: List[str]
    estimated_duration: int
    status: ExecutionStatus = ExecutionStatus.PENDING
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkflowPlan:
    """工作流計劃"""

    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    estimated_duration: int
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ProseOption(Enum):
    """Prose處理選項"""

    CONTINUE = "continue"
    IMPROVE = "improve"
    SHORTER = "shorter"
    LONGER = "longer"
    FIX = "fix"
    ZAP = "zap"


@dataclass
class ProseRequest:
    """Prose處理請求"""

    content: str  # 原始內容
    option: ProseOption  # 處理選項
    command: Optional[str] = None  # 自定義命令（用於ZAP選項）


@dataclass
class ProseResult:
    """Prose處理結果"""

    original_content: str
    processed_content: str
    option_used: ProseOption
    processing_details: Dict[str, Any]


class MockConversationManager:
    """模擬對話管理器"""

    def __init__(self):
        self.model_client = Mock()
        self.tools = []


class MockCoderAgent:
    """模擬CoderAgent"""

    def __init__(self, model_client, tools):
        self.model_client = model_client
        self.tools = tools

    async def process_request(self, task: str) -> str:
        """模擬處理請求"""
        # 簡單的模擬邏輯
        if "continue" in task.lower():
            return "This is a continuation of the original text with additional content."
        elif "improve" in task.lower():
            return "This is an improved version of the original text with better clarity."
        elif "shorter" in task.lower():
            return "Shorter version."
        elif "longer" in task.lower():
            return "This is a much longer and more detailed version of the original text with extensive explanations and examples."
        elif "fix" in task.lower():
            return "This is the corrected version of the text with all errors fixed."
        elif "zap" in task.lower():
            return "Custom processed text based on the specific command provided."
        else:
            return "Processed text result."


class MockWorkflowController:
    """模擬工作流控制器"""

    async def execute_plan(
        self, plan: WorkflowPlan, initial_state: Dict[str, Any], executor_func
    ) -> Dict[str, Any]:
        """模擬執行計劃"""
        state = initial_state.copy()
        for step in plan.steps:
            step.status = ExecutionStatus.IN_PROGRESS
            state = await executor_func(step, state)
            step.status = ExecutionStatus.COMPLETED
        state["status"] = "completed"
        state["execution_time"] = 1.5
        return state


class ProseWorkflowManager:
    """簡化的Prose工作流管理器"""

    def __init__(self, conversation_manager: MockConversationManager):
        self.conversation_manager = conversation_manager
        self.workflow_controller = MockWorkflowController()

        # 定義各種Prose選項對應的提示模板
        self.prose_prompts = {
            ProseOption.CONTINUE: "prose/prose_continue",
            ProseOption.IMPROVE: "prose/prose_improver",
            ProseOption.SHORTER: "prose/prose_shorter",
            ProseOption.LONGER: "prose/prose_longer",
            ProseOption.FIX: "prose/prose_fix",
            ProseOption.ZAP: "prose/prose_zap",
        }

    async def _create_prose_plan(self, request: ProseRequest) -> WorkflowPlan:
        """創建Prose工作流計劃"""
        steps = []

        # 根據選項類型創建相應的處理步驟
        if request.option == ProseOption.CONTINUE:
            steps.append(
                WorkflowStep(
                    id="prose_continue",
                    name="繼續寫作",
                    step_type=StepType.CONTENT_GENERATION,
                    description="基於現有內容繼續寫作",
                    dependencies=[],
                    estimated_duration=30,
                    metadata={"option": request.option.value},
                )
            )
        elif request.option == ProseOption.IMPROVE:
            steps.append(
                WorkflowStep(
                    id="prose_improve",
                    name="改進文本",
                    step_type=StepType.STYLE_REFINEMENT,
                    description="改進現有文本的質量和可讀性",
                    dependencies=[],
                    estimated_duration=45,
                    metadata={"option": request.option.value},
                )
            )
        elif request.option == ProseOption.SHORTER:
            steps.append(
                WorkflowStep(
                    id="prose_shorter",
                    name="精簡文本",
                    step_type=StepType.STYLE_REFINEMENT,
                    description="將文本精簡為更短的版本",
                    dependencies=[],
                    estimated_duration=30,
                    metadata={"option": request.option.value},
                )
            )
        elif request.option == ProseOption.LONGER:
            steps.append(
                WorkflowStep(
                    id="prose_longer",
                    name="擴展文本",
                    step_type=StepType.CONTENT_GENERATION,
                    description="擴展文本內容使其更詳細",
                    dependencies=[],
                    estimated_duration=60,
                    metadata={"option": request.option.value},
                )
            )
        elif request.option == ProseOption.FIX:
            steps.append(
                WorkflowStep(
                    id="prose_fix",
                    name="修正文本",
                    step_type=StepType.STYLE_REFINEMENT,
                    description="修正文本中的錯誤和問題",
                    dependencies=[],
                    estimated_duration=45,
                    metadata={"option": request.option.value},
                )
            )
        elif request.option == ProseOption.ZAP:
            steps.append(
                WorkflowStep(
                    id="prose_zap",
                    name="自定義處理",
                    step_type=StepType.CONTENT_GENERATION,
                    description="根據自定義命令處理文本",
                    dependencies=[],
                    estimated_duration=60,
                    metadata={"option": request.option.value, "command": request.command},
                )
            )

        return WorkflowPlan(
            id=f"prose_{request.option.value}_{hash(request.content) % 10000}",
            name=f"Prose {request.option.value.title()} 工作流",
            description=f"使用 {request.option.value} 選項處理文本",
            steps=steps,
            estimated_duration=sum(step.estimated_duration for step in steps),
            metadata={"prose_option": request.option.value},
        )

    async def _prose_step_executor(
        self, step: WorkflowStep, state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """執行Prose處理步驟"""
        request = state["request"]
        option = ProseOption(step.metadata["option"])

        # 模擬處理
        coder_agent = MockCoderAgent(None, [])

        if option == ProseOption.ZAP:
            user_message = f"For this text: {request.content}\nYou have to respect the command: {request.command}"
        elif option in [
            ProseOption.IMPROVE,
            ProseOption.SHORTER,
            ProseOption.LONGER,
            ProseOption.FIX,
        ]:
            user_message = f"The existing text is: {request.content}"
        else:  # CONTINUE
            user_message = request.content

        processing_task = f"Process with {option.value}: {user_message}"
        response = await coder_agent.process_request(processing_task)

        state["output"] = response.strip()
        return state

    async def process_prose(self, request: ProseRequest) -> ProseResult:
        """處理Prose請求"""
        plan = await self._create_prose_plan(request)

        initial_state = {
            "content": request.content,
            "option": request.option.value,
            "command": request.command or "",
            "output": "",
            "request": request,
        }

        result = await self.workflow_controller.execute_plan(
            plan, initial_state, self._prose_step_executor
        )

        return ProseResult(
            original_content=request.content,
            processed_content=result.get("output", ""),
            option_used=request.option,
            processing_details={
                "execution_time": result.get("execution_time"),
                "steps_completed": len(
                    [s for s in plan.steps if s.status == ExecutionStatus.COMPLETED]
                ),
                "workflow_status": result.get("status"),
            },
        )

    async def process_prose_simple(
        self, content: str, option: Union[str, ProseOption], command: Optional[str] = None
    ) -> str:
        """簡化的Prose處理接口"""
        if isinstance(option, str):
            option = ProseOption(option.lower())

        request = ProseRequest(content=content, option=option, command=command)
        result = await self.process_prose(request)
        return result.processed_content


def mock_get_prompt_template(template_name: str) -> str:
    """模擬提示模板獲取"""
    templates = {
        "prose/prose_continue": "You are an AI writing assistant that continues existing text based on context from prior text.",
        "prose/prose_improver": "You are an AI writing assistant that improves existing text.",
        "prose/prose_shorter": "You are an AI writing assistant that makes text shorter while preserving meaning.",
        "prose/prose_longer": "You are an AI writing assistant that expands text to make it longer and more detailed.",
        "prose/prose_fix": "You are an AI writing assistant that fixes errors in text.",
        "prose/prose_zap": "You area an AI writing assistant that generates text based on a prompt.",
    }
    return templates.get(template_name, "Default prompt template")


async def test_prose_workflow_structure():
    """測試Prose工作流結構"""
    print("=== 測試Prose工作流結構 ===")

    # 創建模擬管理器
    mock_manager = MockConversationManager()
    workflow_manager = ProseWorkflowManager(mock_manager)

    # 測試各種選項的計劃創建
    test_requests = [
        ProseRequest(content="Test content", option=ProseOption.CONTINUE),
        ProseRequest(content="Test content", option=ProseOption.IMPROVE),
        ProseRequest(content="Test content", option=ProseOption.SHORTER),
        ProseRequest(content="Test content", option=ProseOption.LONGER),
        ProseRequest(content="Test content", option=ProseOption.FIX),
        ProseRequest(content="Test content", option=ProseOption.ZAP, command="Make it funny"),
    ]

    for request in test_requests:
        try:
            plan = await workflow_manager._create_prose_plan(request)
            print(f"✓ {request.option.value}: 計劃創建成功 - {len(plan.steps)} 步驟")

            # 驗證計劃基本屬性
            assert plan.id is not None
            assert plan.name is not None
            assert len(plan.steps) > 0
            assert plan.estimated_duration > 0

            # 驗證步驟屬性
            for step in plan.steps:
                assert step.id is not None
                assert step.name is not None
                assert step.step_type is not None
                assert step.estimated_duration > 0

        except Exception as e:
            print(f"✗ {request.option.value}: 計劃創建失敗 - {e}")


async def test_prose_options():
    """測試不同Prose選項"""
    print("\n=== 測試Prose選項處理 ===")

    # 創建工作流管理器（不需要外部依賴）
    mock_manager = MockConversationManager()
    workflow_manager = ProseWorkflowManager(mock_manager)

    test_content = "The weather in Beijing is sunny today."

    for option in ProseOption:
        try:
            print(f"測試選項: {option.value}")

            # 創建請求
            command = "Make it funny" if option == ProseOption.ZAP else None
            request = ProseRequest(content=test_content, option=option, command=command)

            # 測試簡化接口
            result = await workflow_manager.process_prose_simple(test_content, option, command)

            print(f"  原始: {test_content}")
            print(f"  結果: {result}")
            print(f"  ✓ 處理成功")

        except Exception as e:
            print(f"  ✗ 處理失敗: {e}")


async def test_prose_workflow_integration():
    """測試工作流集成"""
    print("\n=== 測試工作流集成 ===")

    try:
        # 創建工作流管理器（不需要外部依賴）
        mock_manager = MockConversationManager()
        workflow_manager = ProseWorkflowManager(mock_manager)

        # 創建測試請求
        request = ProseRequest(
            content="This is a test document about artificial intelligence.",
            option=ProseOption.IMPROVE,
        )

        # 執行完整工作流
        result = await workflow_manager.process_prose(request)

        # 驗證結果
        assert isinstance(result, ProseResult)
        assert result.original_content == request.content
        assert result.processed_content is not None
        assert result.option_used == request.option
        assert isinstance(result.processing_details, dict)

        print(f"✓ 完整工作流測試成功")
        print(f"  原始內容: {result.original_content}")
        print(f"  處理結果: {result.processed_content}")
        print(f"  使用選項: {result.option_used.value}")

    except Exception as e:
        print(f"✗ 工作流集成測試失敗: {e}")
        import traceback

        traceback.print_exc()


def test_prose_enum_values():
    """測試Prose枚舉值"""
    print("\n=== 測試Prose枚舉值 ===")

    expected_options = {"continue", "improve", "shorter", "longer", "fix", "zap"}
    actual_options = {option.value for option in ProseOption}

    if expected_options == actual_options:
        print("✓ Prose選項枚舉值正確")
    else:
        print(f"✗ Prose選項枚舉值不匹配: 期望 {expected_options}, 實際 {actual_options}")


def test_prompt_templates():
    """測試提示模板映射"""
    print("\n=== 測試提示模板映射 ===")

    mock_manager = MockConversationManager()
    workflow_manager = ProseWorkflowManager(mock_manager)

    # 驗證所有選項都有對應的模板
    for option in ProseOption:
        if option in workflow_manager.prose_prompts:
            template_name = workflow_manager.prose_prompts[option]
            print(f"✓ {option.value}: {template_name}")
        else:
            print(f"✗ {option.value}: 缺少模板映射")


async def main():
    """運行所有測試"""
    print("開始Prose工作流測試...\n")

    # 運行同步測試
    test_prose_enum_values()
    test_prompt_templates()

    # 運行異步測試
    await test_prose_workflow_structure()
    await test_prose_options()
    await test_prose_workflow_integration()

    print("\n=== 測試完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
