# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen Prose工作流實現

將原有的 LangGraph-based Prose 工作流遷移到 AutoGen 架構。
支持多種文本處理選項：continue, improve, shorter, longer, fix, zap。
"""

import asyncio
import json
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
from src.prompts.template import get_prompt_template

logger = get_logger(__name__)


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


class ProseWorkflowManager:
    """AutoGen Prose工作流管理器"""

    def __init__(self, conversation_manager: AutoGenConversationManager):
        """
        初始化Prose工作流管理器

        Args:
            conversation_manager: AutoGen對話管理器
        """
        self.conversation_manager = conversation_manager
        self.workflow_controller = WorkflowController()

        # 定義各種Prose選項對應的提示模板
        self.prose_prompts = {
            ProseOption.CONTINUE: "prose/prose_continue",
            ProseOption.IMPROVE: "prose/prose_improver",
            ProseOption.SHORTER: "prose/prose_shorter",
            ProseOption.LONGER: "prose/prose_longer",
            ProseOption.FIX: "prose/prose_fix",
            ProseOption.ZAP: "prose/prose_zap",
        }
        logger.info("Prose工作流管理器初始化完成")

    async def initialize(self):
        """初始化工作流管理器"""
        logger.info("初始化 Prose 工作流管理器")
        # 這裡可以添加任何必要的初始化邏輯
        return True

    async def run_prose_workflow(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """
        執行 Prose 工作流

        Args:
            user_input: 用戶輸入
            **kwargs: 其他參數

        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            logger.info(f"開始執行 Prose 工作流: {user_input}")

            # 創建 Prose 請求
            option = kwargs.get("option", ProseOption.IMPROVE)
            request = ProseRequest(
                content=user_input, option=option, command=kwargs.get("command", "")
            )

            # 執行 Prose 處理
            result = await self.process_prose(request)

            return {"success": True, "result": result, "execution_time": 0}

        except Exception as e:
            logger.error(f"Prose 工作流執行失敗: {e}")
            return {"success": False, "error": str(e)}

    async def process_prose(self, request: ProseRequest) -> ProseResult:
        """
        處理Prose請求

        Args:
            request: Prose處理請求

        Returns:
            ProseResult: 處理結果
        """
        logger.info(f"開始處理Prose請求，選項: {request.option.value}")

        try:
            # 創建工作流計劃
            plan = self._create_prose_plan(request)

            # 初始化工作流狀態
            initial_state = {
                "content": request.content,
                "option": request.option.value,
                "command": request.command or "",
                "output": "",
                "request": request,
            }

            # 執行工作流
            result = await self.workflow_controller.execute_plan(
                plan, initial_state, self._prose_step_executor
            )

            # 構建返回結果
            prose_result = ProseResult(
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

            logger.info("Prose處理完成")
            return prose_result

        except Exception as e:
            logger.error(f"Prose處理失敗: {str(e)}")
            raise

    def _create_prose_plan(self, request: ProseRequest) -> WorkflowPlan:
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
                    agent_type="prose_processor",
                    inputs={"content": request.content, "option": request.option.value},
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
                    agent_type="prose_processor",
                    inputs={"content": request.content, "option": request.option.value},
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
                    agent_type="prose_processor",
                    inputs={"content": request.content, "option": request.option.value},
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
                    agent_type="prose_processor",
                    inputs={"content": request.content, "option": request.option.value},
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
                    agent_type="prose_processor",
                    inputs={"content": request.content, "option": request.option.value},
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
                    agent_type="prose_processor",
                    inputs={
                        "content": request.content,
                        "option": request.option.value,
                        "command": request.command,
                    },
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
        logger.info(f"執行Prose步驟: {step.name}")

        request = state["request"]
        option = ProseOption(step.metadata["option"])

        try:
            # 獲取對應的提示模板
            prompt_template_name = self.prose_prompts.get(option)
            if not prompt_template_name:
                raise ValueError(f"未支持的Prose選項: {option}")

            system_prompt = get_prompt_template(prompt_template_name)

            # 構建用戶消息
            if option == ProseOption.ZAP:
                user_message = (
                    f"For this text: {request.content}\n"
                    f"You have to respect the command: {request.command}"
                )
            elif option in [
                ProseOption.IMPROVE,
                ProseOption.SHORTER,
                ProseOption.LONGER,
                ProseOption.FIX,
            ]:
                user_message = f"The existing text is: {request.content}"
            else:  # CONTINUE
                user_message = request.content

            # 使用CoderAgent進行處理（因為它有文本處理能力）
            coder_agent = CoderAgent(
                model_client=self.conversation_manager.model_client,
                tools=self.conversation_manager.tools,
            )

            # 創建處理任務
            processing_task = (
                f"請根據以下系統指令處理文本：\n\n"
                f"系統指令：{system_prompt}\n\n"
                f"用戶輸入：{user_message}\n\n"
                f"請直接返回處理後的文本，不要包含任何解釋或元信息。"
            )

            # 執行處理
            response = await coder_agent.process_request(processing_task)

            # 更新狀態
            state["output"] = response.strip()

            logger.info(f"Prose步驟 {step.name} 完成")
            return state

        except Exception as e:
            logger.error(f"Prose步驟執行失敗: {str(e)}")
            state["output"] = state["content"]  # 失敗時返回原始內容
            return state

    async def process_prose_simple(
        self, content: str, option: Union[str, ProseOption], command: Optional[str] = None
    ) -> str:
        """
        簡化的Prose處理接口

        Args:
            content: 原始內容
            option: 處理選項
            command: 自定義命令（用於ZAP選項）

        Returns:
            str: 處理後的內容
        """
        if isinstance(option, str):
            option = ProseOption(option.lower())

        request = ProseRequest(content=content, option=option, command=command)
        result = await self.process_prose(request)
        return result.processed_content


def create_prose_workflow_manager() -> ProseWorkflowManager:
    """創建Prose工作流管理器實例"""
    from src.autogen_system.controllers.conversation_manager import create_conversation_manager

    conversation_manager = create_conversation_manager()
    return ProseWorkflowManager(conversation_manager)


async def generate_prose_with_autogen(
    content: str, option: str, command: Optional[str] = None
) -> str:
    """
    使用AutoGen生成Prose的便捷函數

    Args:
        content: 原始內容
        option: 處理選項 (continue, improve, shorter, longer, fix, zap)
        command: 自定義命令（用於zap選項）

    Returns:
        str: 處理後的內容
    """
    workflow_manager = create_prose_workflow_manager()
    return await workflow_manager.process_prose_simple(content, option, command)


if __name__ == "__main__":

    async def test_prose_workflow():
        """測試Prose工作流"""
        test_content = "The weather in Beijing is sunny today."

        # 測試不同選項
        options_to_test = ["continue", "improve", "shorter"]

        for option in options_to_test:
            print(f"\n=== 測試 {option} 選項 ===")
            try:
                result = await generate_prose_with_autogen(test_content, option)
                print(f"原始內容: {test_content}")
                print(f"處理結果: {result}")
            except Exception as e:
                print(f"測試失敗: {e}")

    asyncio.run(test_prose_workflow())
