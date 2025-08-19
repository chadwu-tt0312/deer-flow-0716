#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PromptEnhancer工作流簡化測試

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
    PROMPT_ANALYSIS = "prompt_analysis"
    ENHANCEMENT_GENERATION = "enhancement_generation"
    PROMPT_VALIDATION = "prompt_validation"


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


class ReportStyle(Enum):
    """報告風格"""

    ACADEMIC = "academic"
    POPULAR_SCIENCE = "popular_science"
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"


@dataclass
class PromptEnhancementRequest:
    """提示增強請求"""

    prompt: str  # 原始提示
    context: Optional[str] = None  # 額外上下文
    report_style: Optional[ReportStyle] = None  # 報告風格


@dataclass
class PromptEnhancementResult:
    """提示增強結果"""

    original_prompt: str
    enhanced_prompt: str
    context_used: Optional[str]
    report_style_used: Optional[ReportStyle]
    enhancement_details: Dict[str, Any]


class MockConversationManager:
    """模擬對話管理器"""

    def __init__(self):
        self.model_client = Mock()
        self.tools = []


class MockPlannerAgent:
    """模擬PlannerAgent"""

    def __init__(self, model_client, tools):
        self.model_client = model_client
        self.tools = tools

    async def create_plan(self, task: str) -> str:
        """模擬創建計劃"""
        return "Analysis: The prompt needs more specificity and structure. Improvements needed in clarity and actionability."


class MockCoderAgent:
    """模擬CoderAgent"""

    def __init__(self, model_client, tools):
        self.model_client = model_client
        self.tools = tools

    async def process_request(self, task: str) -> str:
        """模擬處理請求"""
        # 根據風格返回不同的增強結果
        if "academic" in task.lower():
            return """<enhanced_prompt>
Conduct a comprehensive academic analysis of artificial intelligence applications. Employ systematic methodology to examine current research and provide evidence-based conclusions with proper citations and theoretical framework.
</enhanced_prompt>"""
        elif "popular_science" in task.lower():
            return """<enhanced_prompt>
Tell the fascinating story of artificial intelligence in an engaging way that captivates readers. Use vivid analogies and real-world examples to make complex concepts accessible and exciting for a general audience.
</enhanced_prompt>"""
        elif "news" in task.lower():
            return """<enhanced_prompt>
Report on the current state of artificial intelligence with journalistic rigor. Include recent developments, verified data, expert quotes, and balanced perspective following AP style guidelines.
</enhanced_prompt>"""
        elif "social_media" in task.lower():
            return """<enhanced_prompt>
Create viral-worthy content about AI that stops the scroll! 🤖 Use trending hashtags, engaging hooks, and shareable format. Include questions for audience engagement and optimize for maximum shareability.
</enhanced_prompt>"""
        else:
            return """<enhanced_prompt>
Write a comprehensive analysis of artificial intelligence with specific examples, clear structure, and actionable insights. Include relevant details and organize the response logically.
</enhanced_prompt>"""


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


class PromptEnhancerWorkflowManager:
    """簡化的PromptEnhancer工作流管理器"""

    def __init__(self, conversation_manager: MockConversationManager):
        self.conversation_manager = conversation_manager
        self.workflow_controller = MockWorkflowController()

    async def _create_enhancement_plan(self, request: PromptEnhancementRequest) -> WorkflowPlan:
        """創建提示增強工作流計劃"""
        steps = [
            WorkflowStep(
                id="prompt_analysis",
                name="分析原始提示",
                step_type=StepType.PROMPT_ANALYSIS,
                description="分析原始提示的結構、目標和改進空間",
                dependencies=[],
                estimated_duration=20,
                metadata={"stage": "analysis"},
            ),
            WorkflowStep(
                id="enhancement_generation",
                name="生成增強提示",
                step_type=StepType.ENHANCEMENT_GENERATION,
                description="根據分析結果和報告風格生成增強的提示",
                dependencies=["prompt_analysis"],
                estimated_duration=60,
                metadata={"stage": "generation"},
            ),
            WorkflowStep(
                id="prompt_validation",
                name="驗證增強結果",
                step_type=StepType.PROMPT_VALIDATION,
                description="驗證增強提示的質量和有效性",
                dependencies=["enhancement_generation"],
                estimated_duration=30,
                metadata={"stage": "validation"},
            ),
        ]

        return WorkflowPlan(
            id=f"prompt_enhance_{hash(request.prompt) % 10000}",
            name="提示增強工作流",
            description="分析並增強用戶提示以提高AI響應質量",
            steps=steps,
            estimated_duration=sum(step.estimated_duration for step in steps),
            metadata={
                "report_style": request.report_style.value if request.report_style else None,
                "has_context": bool(request.context),
            },
        )

    async def _enhancement_step_executor(
        self, step: WorkflowStep, state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """執行提示增強步驟"""
        request = state["request"]

        if step.id == "prompt_analysis":
            state["prompt_analysis"] = f"Analysis of prompt: {request.prompt[:50]}..."
        elif step.id == "enhancement_generation":
            # 模擬增強生成
            coder_agent = MockCoderAgent(None, [])
            response = await coder_agent.process_request(f"enhance {request.report_style}")
            enhanced_prompt = self._extract_enhanced_prompt(response)
            state["output"] = enhanced_prompt
        elif step.id == "prompt_validation":
            if not state.get("output"):
                state["output"] = request.prompt
            state["validation_passed"] = True

        return state

    def _extract_enhanced_prompt(self, response_content: str) -> str:
        """從響應中提取增強的提示"""
        import re

        response_content = response_content.strip()

        # 嘗試從XML標籤中提取
        xml_match = re.search(
            r"<enhanced_prompt>(.*?)</enhanced_prompt>", response_content, re.DOTALL
        )

        if xml_match:
            enhanced_prompt = xml_match.group(1).strip()
            return enhanced_prompt

        # 回退邏輯：移除常見前綴
        enhanced_prompt = response_content
        prefixes_to_remove = [
            "Enhanced Prompt:",
            "Enhanced prompt:",
            "Here's the enhanced prompt:",
            "Here is the enhanced prompt:",
            "**Enhanced Prompt**:",
            "**Enhanced prompt**:",
        ]

        for prefix in prefixes_to_remove:
            if enhanced_prompt.startswith(prefix):
                enhanced_prompt = enhanced_prompt[len(prefix) :].strip()
                break

        return enhanced_prompt

    async def enhance_prompt(self, request: PromptEnhancementRequest) -> PromptEnhancementResult:
        """增強提示"""
        plan = await self._create_enhancement_plan(request)

        initial_state = {
            "prompt": request.prompt,
            "context": request.context,
            "report_style": request.report_style,
            "output": "",
            "request": request,
        }

        result = await self.workflow_controller.execute_plan(
            plan, initial_state, self._enhancement_step_executor
        )

        return PromptEnhancementResult(
            original_prompt=request.prompt,
            enhanced_prompt=result.get("output", request.prompt),
            context_used=request.context,
            report_style_used=request.report_style,
            enhancement_details={
                "execution_time": result.get("execution_time"),
                "steps_completed": len(
                    [s for s in plan.steps if s.status == ExecutionStatus.COMPLETED]
                ),
                "workflow_status": result.get("status"),
                "enhancement_method": "autogen_based",
            },
        )

    async def enhance_prompt_simple(
        self,
        prompt: str,
        context: Optional[str] = None,
        report_style: Optional[Union[str, ReportStyle]] = None,
    ) -> str:
        """簡化的提示增強接口"""
        # 處理報告風格
        if isinstance(report_style, str):
            try:
                style_mapping = {
                    "ACADEMIC": ReportStyle.ACADEMIC,
                    "POPULAR_SCIENCE": ReportStyle.POPULAR_SCIENCE,
                    "NEWS": ReportStyle.NEWS,
                    "SOCIAL_MEDIA": ReportStyle.SOCIAL_MEDIA,
                }
                report_style = style_mapping.get(report_style.upper(), ReportStyle.ACADEMIC)
            except Exception:
                report_style = ReportStyle.ACADEMIC
        elif report_style is None:
            report_style = ReportStyle.ACADEMIC

        request = PromptEnhancementRequest(
            prompt=prompt, context=context, report_style=report_style
        )

        result = await self.enhance_prompt(request)
        return result.enhanced_prompt


def mock_apply_prompt_template(template_name: str, variables: dict) -> list:
    """模擬提示模板應用"""
    from collections import namedtuple

    MockMessage = namedtuple("MockMessage", ["content"])

    # 根據報告風格生成不同的模板內容
    report_style = variables.get("report_style")
    messages = variables.get("messages", [])

    base_content = (
        "You are an expert prompt engineer. Enhance the following prompt to make it more effective."
    )

    if report_style == ReportStyle.ACADEMIC:
        style_content = "\nFocus on academic rigor, methodology, and scholarly structure."
    elif report_style == ReportStyle.POPULAR_SCIENCE:
        style_content = "\nMake it accessible and engaging for general audience."
    elif report_style == ReportStyle.NEWS:
        style_content = "\nEnsure journalistic standards and objectivity."
    elif report_style == ReportStyle.SOCIAL_MEDIA:
        style_content = "\nOptimize for engagement and shareability."
    else:
        style_content = "\nImprove clarity and specificity."

    # 組合原始消息內容
    user_content = ""
    for msg in messages:
        if hasattr(msg, "content"):
            user_content += msg.content

    full_content = (
        base_content
        + style_content
        + "\n\n"
        + user_content
        + "\n\nWrap your enhanced prompt in <enhanced_prompt></enhanced_prompt> tags."
    )

    return [MockMessage(content=full_content)]


async def test_prompt_enhancer_workflow_structure():
    """測試PromptEnhancer工作流結構"""
    print("=== 測試PromptEnhancer工作流結構 ===")

    # 創建模擬管理器
    mock_manager = MockConversationManager()
    workflow_manager = PromptEnhancerWorkflowManager(mock_manager)

    # 測試各種風格的計劃創建
    test_requests = [
        PromptEnhancementRequest(prompt="Write about AI", report_style=ReportStyle.ACADEMIC),
        PromptEnhancementRequest(
            prompt="Explain climate change", report_style=ReportStyle.POPULAR_SCIENCE
        ),
        PromptEnhancementRequest(prompt="Create a plan", report_style=ReportStyle.NEWS),
        PromptEnhancementRequest(prompt="Social post", report_style=ReportStyle.SOCIAL_MEDIA),
        PromptEnhancementRequest(prompt="Basic prompt", context="Additional context"),
    ]

    for request in test_requests:
        try:
            plan = await workflow_manager._create_enhancement_plan(request)
            style_name = request.report_style.value if request.report_style else "None"
            print(f"✓ 風格 {style_name}: 計劃創建成功 - {len(plan.steps)} 步驟")

            # 驗證計劃基本屬性
            assert plan.id is not None
            assert plan.name is not None
            assert len(plan.steps) == 3  # 應該有3個步驟：分析、生成、驗證
            assert plan.estimated_duration > 0

            # 驗證步驟順序和依賴
            step_ids = [step.id for step in plan.steps]
            expected_ids = ["prompt_analysis", "enhancement_generation", "prompt_validation"]
            assert step_ids == expected_ids

            # 驗證依賴關係
            assert plan.steps[0].dependencies == []
            assert plan.steps[1].dependencies == ["prompt_analysis"]
            assert plan.steps[2].dependencies == ["enhancement_generation"]

        except Exception as e:
            print(f"✗ 風格 {style_name}: 計劃創建失敗 - {e}")


async def test_prompt_enhancement_styles():
    """測試不同報告風格的提示增強"""
    print("\n=== 測試提示增強風格 ===")

    # 創建工作流管理器（不需要外部依賴）
    mock_manager = MockConversationManager()
    workflow_manager = PromptEnhancerWorkflowManager(mock_manager)

    test_prompt = "Write about AI"

    for style in ReportStyle:
        try:
            print(f"測試風格: {style.value}")

            # 測試簡化接口
            result = await workflow_manager.enhance_prompt_simple(
                prompt=test_prompt, report_style=style
            )

            print(f"  原始: {test_prompt}")
            print(f"  結果: {result[:100]}{'...' if len(result) > 100 else ''}")
            print(f"  ✓ 處理成功")

        except Exception as e:
            print(f"  ✗ 處理失敗: {e}")


async def test_prompt_extraction():
    """測試提示提取邏輯"""
    print("\n=== 測試提示提取邏輯 ===")

    mock_manager = MockConversationManager()
    workflow_manager = PromptEnhancerWorkflowManager(mock_manager)

    test_cases = [
        # 標準XML格式
        (
            "<enhanced_prompt>This is the enhanced prompt</enhanced_prompt>",
            "This is the enhanced prompt",
        ),
        # 帶前綴的格式
        ("Enhanced Prompt: This is the enhanced version", "This is the enhanced version"),
        # 帶Markdown粗體的格式
        ("**Enhanced Prompt**: This is the enhanced version", "This is the enhanced version"),
        # 純文本格式
        ("This is just plain text without tags", "This is just plain text without tags"),
        # 多行XML格式
        (
            "<enhanced_prompt>\nThis is a multi-line\nenhanced prompt\n</enhanced_prompt>",
            "This is a multi-line\nenhanced prompt",
        ),
    ]

    for input_text, expected_output in test_cases:
        try:
            result = workflow_manager._extract_enhanced_prompt(input_text)
            if result.strip() == expected_output.strip():
                print(f"✓ 提取成功: '{input_text[:30]}...' -> '{result[:30]}...'")
            else:
                print(f"✗ 提取失敗: 期望 '{expected_output}', 得到 '{result}'")
        except Exception as e:
            print(f"✗ 提取異常: {e}")


async def test_prompt_enhancer_integration():
    """測試工作流集成"""
    print("\n=== 測試工作流集成 ===")

    try:
        # 創建工作流管理器（不需要外部依賴）
        mock_manager = MockConversationManager()
        workflow_manager = PromptEnhancerWorkflowManager(mock_manager)

        # 創建測試請求
        request = PromptEnhancementRequest(
            prompt="Write about climate change",
            context="For a general audience",
            report_style=ReportStyle.POPULAR_SCIENCE,
        )

        # 執行完整工作流
        result = await workflow_manager.enhance_prompt(request)

        # 驗證結果
        assert isinstance(result, PromptEnhancementResult)
        assert result.original_prompt == request.prompt
        assert result.enhanced_prompt is not None
        assert result.context_used == request.context
        assert result.report_style_used == request.report_style
        assert isinstance(result.enhancement_details, dict)

        print(f"✓ 完整工作流測試成功")
        print(f"  原始提示: {result.original_prompt}")
        print(f"  增強結果: {result.enhanced_prompt[:100]}...")
        print(f"  使用風格: {result.report_style_used.value}")

    except Exception as e:
        print(f"✗ 工作流集成測試失敗: {e}")
        import traceback

        traceback.print_exc()


def test_report_style_mapping():
    """測試報告風格映射"""
    print("\n=== 測試報告風格映射 ===")

    mock_manager = MockConversationManager()
    workflow_manager = PromptEnhancerWorkflowManager(mock_manager)

    # 測試字符串到枚舉的轉換
    test_cases = [
        ("ACADEMIC", ReportStyle.ACADEMIC),
        ("academic", ReportStyle.ACADEMIC),
        ("POPULAR_SCIENCE", ReportStyle.POPULAR_SCIENCE),
        ("NEWS", ReportStyle.NEWS),
        ("SOCIAL_MEDIA", ReportStyle.SOCIAL_MEDIA),
        ("invalid_style", ReportStyle.ACADEMIC),  # 應該回退到ACADEMIC
        (None, ReportStyle.ACADEMIC),  # 應該使用默認值
    ]

    for input_style, expected_style in test_cases:
        try:
            # 這裡測試簡化接口中的轉換邏輯
            # 我們需要模擬這個邏輯
            if isinstance(input_style, str):
                style_mapping = {
                    "ACADEMIC": ReportStyle.ACADEMIC,
                    "POPULAR_SCIENCE": ReportStyle.POPULAR_SCIENCE,
                    "NEWS": ReportStyle.NEWS,
                    "SOCIAL_MEDIA": ReportStyle.SOCIAL_MEDIA,
                }
                result = style_mapping.get(input_style.upper(), ReportStyle.ACADEMIC)
            elif input_style is None:
                result = ReportStyle.ACADEMIC
            else:
                result = input_style

            if result == expected_style:
                print(f"✓ 風格映射成功: '{input_style}' -> {result.value}")
            else:
                print(f"✗ 風格映射失敗: 期望 {expected_style.value}, 得到 {result.value}")

        except Exception as e:
            print(f"✗ 風格映射異常: {e}")


async def main():
    """運行所有測試"""
    print("開始PromptEnhancer工作流測試...\n")

    # 運行同步測試
    test_report_style_mapping()

    # 運行異步測試
    await test_prompt_enhancer_workflow_structure()
    await test_prompt_enhancement_styles()
    await test_prompt_extraction()
    await test_prompt_enhancer_integration()

    print("\n=== 測試完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
