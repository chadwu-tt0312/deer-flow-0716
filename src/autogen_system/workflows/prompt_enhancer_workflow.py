# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen PromptEnhancer工作流實現

將原有的 LangGraph-based PromptEnhancer 工作流遷移到 AutoGen 架構。
支持多種報告風格的提示增強。
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from src.logging import get_logger
from src.autogen_system.controllers.workflow_controller import (
    WorkflowController,
    StepType,
    ExecutionStatus,
    WorkflowStep,
    WorkflowPlan,
)
from src.autogen_system.controllers.conversation_manager import AutoGenConversationManager
from src.autogen_system.agents.coordinator_agent import CoordinatorAgent
from src.autogen_system.agents.planner_agent import PlannerAgent
from src.autogen_system.agents.coder_agent import CoderAgent
from src.prompts.template import apply_prompt_template
from src.config.report_style import ReportStyle

logger = get_logger(__name__)


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


class PromptEnhancerWorkflowManager:
    """AutoGen PromptEnhancer工作流管理器"""

    def __init__(self, conversation_manager: AutoGenConversationManager):
        """
        初始化PromptEnhancer工作流管理器

        Args:
            conversation_manager: AutoGen對話管理器
        """
        self.conversation_manager = conversation_manager
        self.workflow_controller = WorkflowController()

    async def initialize(self):
        """初始化工作流管理器"""
        logger.info("初始化 PromptEnhancer 工作流管理器")
        # 這裡可以添加任何必要的初始化邏輯
        return True

    async def run_prompt_enhancer_workflow(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """
        執行 PromptEnhancer 工作流

        Args:
            user_input: 用戶輸入
            **kwargs: 其他參數

        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            logger.info(f"開始執行 PromptEnhancer 工作流: {user_input}")

            # 創建 PromptEnhancement 請求
            request = PromptEnhancementRequest(
                prompt=user_input,
                context=kwargs.get("context", ""),
                report_style=kwargs.get("report_style", ReportStyle.ACADEMIC),
            )

            # 執行提示增強
            result = await self.enhance_prompt(request)

            return {"success": True, "result": result, "execution_time": 0}

        except Exception as e:
            logger.error(f"PromptEnhancer 工作流執行失敗: {e}")
            return {"success": False, "error": str(e)}

    async def enhance_prompt(self, request: PromptEnhancementRequest) -> PromptEnhancementResult:
        """
        增強提示

        Args:
            request: 提示增強請求

        Returns:
            PromptEnhancementResult: 增強結果
        """
        logger.info(f"開始增強提示，風格: {request.report_style}")

        try:
            # 創建工作流計劃
            plan = self._create_enhancement_plan(request)

            # 初始化工作流狀態
            initial_state = {
                "prompt": request.prompt,
                "context": request.context,
                "report_style": request.report_style,
                "output": "",
                "request": request,
            }

            # 執行工作流
            result = await self.workflow_controller.execute_plan(
                plan, initial_state, self._enhancement_step_executor
            )

            # 構建返回結果
            enhancement_result = PromptEnhancementResult(
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

            logger.info("提示增強完成")
            return enhancement_result

        except Exception as e:
            logger.error(f"提示增強失敗: {str(e)}")
            # 失敗時返回原始提示
            return PromptEnhancementResult(
                original_prompt=request.prompt,
                enhanced_prompt=request.prompt,
                context_used=request.context,
                report_style_used=request.report_style,
                enhancement_details={"error": str(e)},
            )

    def _create_enhancement_plan(self, request: PromptEnhancementRequest) -> WorkflowPlan:
        """創建提示增強工作流計劃"""
        steps = [
            WorkflowStep(
                id="prompt_analysis",
                name="分析原始提示",
                step_type=StepType.PROMPT_ANALYSIS,
                description="分析原始提示的結構、目標和改進空間",
                agent_type="prompt_enhancer",
                inputs={"prompt": request.prompt, "context": request.context},
                dependencies=[],
                estimated_duration=20,
                metadata={"stage": "analysis"},
            ),
            WorkflowStep(
                id="enhancement_generation",
                name="生成增強提示",
                step_type=StepType.ENHANCEMENT_GENERATION,
                description="根據分析結果和報告風格生成增強的提示",
                agent_type="prompt_enhancer",
                inputs={
                    "prompt": request.prompt,
                    "context": request.context,
                    "report_style": request.report_style,
                },
                dependencies=["prompt_analysis"],
                estimated_duration=60,
                metadata={"stage": "generation"},
            ),
            WorkflowStep(
                id="prompt_validation",
                name="驗證增強結果",
                step_type=StepType.PROMPT_VALIDATION,
                description="驗證增強提示的質量和有效性",
                agent_type="prompt_enhancer",
                inputs={"prompt": request.prompt, "context": request.context},
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
        logger.info(f"執行增強步驟: {step.name}")

        request = state["request"]

        try:
            if step.id == "prompt_analysis":
                return await self._analyze_prompt(step, state)
            elif step.id == "enhancement_generation":
                return await self._generate_enhancement(step, state)
            elif step.id == "prompt_validation":
                return await self._validate_enhancement(step, state)
            else:
                logger.warning(f"未知的步驟ID: {step.id}")
                return state

        except Exception as e:
            logger.error(f"步驟執行失敗 {step.id}: {str(e)}")
            return state

    async def _analyze_prompt(self, step: WorkflowStep, state: Dict[str, Any]) -> Dict[str, Any]:
        """分析原始提示"""
        request = state["request"]

        # 使用PlannerAgent進行提示分析
        planner_agent = PlannerAgent(
            model_client=self.conversation_manager.model_client,
            tools=self.conversation_manager.tools,
        )

        analysis_task = (
            f"請分析以下提示的結構和改進潛力：\n\n"
            f"原始提示：{request.prompt}\n\n"
            f"請分析：\n"
            f"1. 提示的明確性和具體性\n"
            f"2. 是否包含足夠的上下文信息\n"
            f"3. 結構是否清晰\n"
            f"4. 可能的改進方向\n\n"
            f"請提供簡潔的分析結果。"
        )

        analysis_result = await planner_agent.create_plan(analysis_task)
        state["prompt_analysis"] = analysis_result

        logger.info("提示分析完成")
        return state

    async def _generate_enhancement(
        self, step: WorkflowStep, state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成增強提示"""
        request = state["request"]

        try:
            # 準備上下文信息
            context_info = ""
            if request.context:
                context_info = f"\n\nAdditional context: {request.context}"

            # 構建消息
            from langchain.schema import HumanMessage

            original_prompt_message = HumanMessage(
                content=f"Please enhance this prompt:{context_info}\n\nOriginal prompt: {request.prompt}"
            )

            # 應用模板
            messages = apply_prompt_template(
                "prompt_enhancer/prompt_enhancer",
                {
                    "messages": [original_prompt_message],
                    "report_style": request.report_style,
                },
            )

            # 使用CoderAgent進行增強生成
            coder_agent = CoderAgent(
                model_client=self.conversation_manager.model_client,
                tools=self.conversation_manager.tools,
            )

            # 將消息轉換為字符串格式
            full_prompt = ""
            for msg in messages:
                if hasattr(msg, "content"):
                    full_prompt += msg.content + "\n"
                else:
                    full_prompt += str(msg) + "\n"

            # 執行增強生成
            response = await coder_agent.process_request(full_prompt)

            # 提取增強的提示
            enhanced_prompt = self._extract_enhanced_prompt(response)
            state["output"] = enhanced_prompt

            logger.info("提示增強生成完成")
            return state

        except Exception as e:
            logger.error(f"增強生成失敗: {str(e)}")
            state["output"] = request.prompt  # 失敗時返回原始提示
            return state

    async def _validate_enhancement(
        self, step: WorkflowStep, state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """驗證增強結果"""
        original_prompt = state["request"].prompt
        enhanced_prompt = state.get("output", "")

        # 簡單的驗證邏輯
        if not enhanced_prompt or enhanced_prompt.strip() == "":
            logger.warning("增強提示為空，使用原始提示")
            state["output"] = original_prompt
        elif len(enhanced_prompt) < len(original_prompt) * 0.8:
            logger.warning("增強提示可能過短，請檢查")

        # 記錄驗證結果
        state["validation_passed"] = bool(enhanced_prompt and enhanced_prompt.strip())

        logger.info("提示驗證完成")
        return state

    def _extract_enhanced_prompt(self, response_content: str) -> str:
        """從響應中提取增強的提示"""
        response_content = response_content.strip()

        # 嘗試從XML標籤中提取
        xml_match = re.search(
            r"<enhanced_prompt>(.*?)</enhanced_prompt>", response_content, re.DOTALL
        )

        if xml_match:
            enhanced_prompt = xml_match.group(1).strip()
            logger.debug("從XML標籤中成功提取增強提示")
            return enhanced_prompt

        # 回退邏輯：移除常見前綴
        enhanced_prompt = response_content
        logger.warning("未找到XML標籤，使用回退解析")

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

    async def enhance_prompt_simple(
        self,
        prompt: str,
        context: Optional[str] = None,
        report_style: Optional[Union[str, ReportStyle]] = None,
    ) -> str:
        """
        簡化的提示增強接口

        Args:
            prompt: 原始提示
            context: 額外上下文
            report_style: 報告風格

        Returns:
            str: 增強後的提示
        """
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


def create_prompt_enhancer_workflow_manager() -> PromptEnhancerWorkflowManager:
    """創建PromptEnhancer工作流管理器實例"""
    from src.autogen_system.controllers.conversation_manager import create_conversation_manager

    conversation_manager = create_conversation_manager()
    return PromptEnhancerWorkflowManager(conversation_manager)


async def enhance_prompt_with_autogen(
    prompt: str, context: Optional[str] = None, report_style: Optional[str] = None
) -> str:
    """
    使用AutoGen增強提示的便捷函數

    Args:
        prompt: 原始提示
        context: 額外上下文
        report_style: 報告風格 (academic, popular_science, news, social_media)

    Returns:
        str: 增強後的提示
    """
    workflow_manager = create_prompt_enhancer_workflow_manager()
    return await workflow_manager.enhance_prompt_simple(prompt, context, report_style)


if __name__ == "__main__":

    async def test_prompt_enhancer_workflow():
        """測試PromptEnhancer工作流"""
        test_prompts = ["Write about AI", "Explain climate change", "Create a marketing plan"]

        test_styles = ["academic", "popular_science", "news"]

        for prompt in test_prompts:
            for style in test_styles:
                print(f"\n=== 測試提示: '{prompt}' 風格: {style} ===")
                try:
                    result = await enhance_prompt_with_autogen(prompt=prompt, report_style=style)
                    print(f"原始提示: {prompt}")
                    print(f"增強結果: {result[:200]}{'...' if len(result) > 200 else ''}")
                except Exception as e:
                    print(f"測試失敗: {e}")

    asyncio.run(test_prompt_enhancer_workflow())
