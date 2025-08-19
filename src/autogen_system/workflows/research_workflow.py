# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 研究工作流

實現主要的研究工作流程，集成對話管理器和工作流控制器。
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime


# Mock AutoGen classes for compatibility
class MockChatCompletionClient:
    """Mock ChatCompletionClient for compatibility"""

    def __init__(self, *args, **kwargs):
        self.config = kwargs.get("config", {})
        self.api_key = kwargs.get("api_key", "mock_key")
        self.base_url = kwargs.get("base_url", "https://api.openai.com/v1")

    def get(self, key, default=None):
        """Mock get method for config access"""
        if hasattr(self, key):
            return getattr(self, key)
        return self.config.get(key, default)

    def __getattr__(self, name):
        """Handle any other attribute access"""
        return lambda *args, **kwargs: None


ChatCompletionClient = MockChatCompletionClient
UserMessage = type("UserMessage", (), {})
SystemMessage = type("SystemMessage", (), {})

from src.logging import get_logger
from ..controllers.conversation_manager import (
    AutoGenConversationManager,
    ConversationConfig,
    ConversationState,
    WorkflowState,
)
from ..controllers.workflow_controller import (
    WorkflowController,
    WorkflowPlan,
    WorkflowStep,
    StepType,
    ExecutionStatus,
    create_research_workflow_plan,
)
from ..agents import CoordinatorAgent, PlannerAgent, ResearcherAgent, CoderAgent, ReporterAgent

logger = get_logger(__name__)


class ResearchWorkflowManager:
    """
    研究工作流管理器

    整合對話管理器和工作流控制器，提供完整的研究工作流功能。
    """

    def __init__(self, model_client: ChatCompletionClient, config: ConversationConfig = None):
        """
        初始化研究工作流管理器

        Args:
            model_client: 聊天完成客戶端
            config: 對話配置
        """
        self.model_client = model_client
        self.config = config or ConversationConfig()

        # 初始化子組件
        self.conversation_manager = AutoGenConversationManager(model_client, config)
        self.workflow_controller = WorkflowController()

        # 註冊步驟處理器
        self._register_step_handlers()

        # 工作流狀態
        self.current_workflow: Optional[WorkflowPlan] = None
        self.execution_results: Dict[str, Any] = {}

        logger.info("研究工作流管理器初始化完成")

    def _register_step_handlers(self):
        """註冊步驟處理器"""
        self.workflow_controller.register_step_handler(
            StepType.RESEARCH, self._handle_research_step
        )
        self.workflow_controller.register_step_handler(
            StepType.ANALYSIS, self._handle_analysis_step
        )
        self.workflow_controller.register_step_handler(StepType.CODE, self._handle_code_step)
        self.workflow_controller.register_step_handler(
            StepType.PROCESSING, self._handle_processing_step
        )
        self.workflow_controller.register_step_handler(
            StepType.SYNTHESIS, self._handle_synthesis_step
        )

    async def initialize(self):
        """初始化工作流管理器"""
        await self.conversation_manager.initialize_runtime()
        logger.info("研究工作流管理器初始化完成")

    async def run_research_workflow(
        self, user_input: str, workflow_type: str = "standard"
    ) -> Dict[str, Any]:
        """
        執行研究工作流

        Args:
            user_input: 用戶輸入
            workflow_type: 工作流類型

        Returns:
            Dict[str, Any]: 執行結果
        """
        logger.info(f"開始執行研究工作流: {user_input}")

        try:
            # 第一階段：協調者分析
            coordinator_result = await self._coordinator_analysis(user_input)
            research_topic = coordinator_result.get("research_topic", user_input)

            # 第二階段：背景調查（可選）
            background_info = ""
            if self.config.enable_background_investigation:
                background_info = await self._background_investigation(research_topic)

            # 第三階段：計劃生成
            plan_result = await self._generate_plan(user_input, research_topic, background_info)

            # 第四階段：工作流執行
            workflow_plan = self._create_workflow_plan(plan_result, research_topic)
            execution_result = await self.workflow_controller.execute_plan(
                workflow_plan,
                {
                    "user_input": user_input,
                    "research_topic": research_topic,
                    "background_info": background_info,
                    "plan": plan_result,
                },
            )

            # 第五階段：報告生成
            final_report = await self._generate_final_report(
                user_input, research_topic, execution_result
            )

            return {
                "success": True,
                "user_input": user_input,
                "research_topic": research_topic,
                "workflow_plan": workflow_plan,
                "execution_result": execution_result,
                "final_report": final_report,
                "execution_time": execution_result.get("execution_time", 0),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"研究工作流執行失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_input": user_input,
                "timestamp": datetime.now().isoformat(),
            }

    async def _coordinator_analysis(self, user_input: str) -> Dict[str, Any]:
        """協調者分析階段"""
        logger.info("執行協調者分析")

        coordinator = self.conversation_manager.agents.get("coordinator")
        if not coordinator:
            # 如果沒有協調者，創建一個簡單的分析結果
            return {
                "research_topic": user_input,
                "locale": "zh-TW",
                "request_type": "research",
                "next_action": "planner",
            }

        return await coordinator.analyze_user_input(user_input)

    async def _background_investigation(self, research_topic: str) -> str:
        """背景調查階段"""
        logger.info("執行背景調查")

        researcher = self.conversation_manager.agents.get("researcher")
        if not researcher:
            return f"針對主題 '{research_topic}' 的背景調查已完成。"

        return await researcher.investigate_topic(research_topic)

    async def _generate_plan(
        self, user_input: str, research_topic: str, background_info: str
    ) -> Dict[str, Any]:
        """計劃生成階段"""
        logger.info("執行計劃生成")

        planner = self.conversation_manager.agents.get("planner")
        if not planner:
            # 如果沒有計劃者，創建一個簡單的計劃
            return {
                "plan_id": f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "description": f"針對 '{research_topic}' 的研究計劃",
                "steps": [
                    {
                        "step_id": "research_step",
                        "step_type": "research",
                        "description": f"研究主題: {research_topic}",
                        "expected_output": "研究結果和相關資料",
                    }
                ],
            }

        plan_context = {
            "user_input": user_input,
            "research_topic": research_topic,
            "background_investigation": background_info,
            "locale": "zh-TW",
        }

        return await planner.create_plan(plan_context)

    def _create_workflow_plan(
        self, plan_result: Dict[str, Any], research_topic: str
    ) -> WorkflowPlan:
        """創建工作流計劃"""
        logger.info("創建工作流計劃")

        # 從計劃結果創建工作流步驟
        workflow_steps = []
        plan_steps = plan_result.get("steps", [])

        for i, step in enumerate(plan_steps):
            step_type_mapping = {
                "research": StepType.RESEARCH,
                "analysis": StepType.ANALYSIS,
                "code": StepType.CODE,
                "processing": StepType.PROCESSING,
                "synthesis": StepType.SYNTHESIS,
            }

            step_type = step_type_mapping.get(
                step.get("step_type", "research").lower(), StepType.RESEARCH
            )

            workflow_step = WorkflowStep(
                id=step.get("step_id", f"step_{i}"),
                step_type=step_type,
                description=step.get("description", ""),
                agent_type=self._get_agent_type_for_step(step_type),
                inputs={"step_data": step, "step_index": i},
                dependencies=step.get("dependencies", []),
                metadata={"critical": i == 0},  # 第一步是關鍵步驟
            )
            workflow_steps.append(workflow_step)

        return WorkflowPlan(
            id=plan_result.get("plan_id", f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            name=f"研究工作流: {research_topic}",
            description=plan_result.get("description", ""),
            steps=workflow_steps,
            metadata={"research_topic": research_topic, "original_plan": plan_result},
        )

    def _get_agent_type_for_step(self, step_type: StepType) -> str:
        """根據步驟類型獲取智能體類型"""
        mapping = {
            StepType.RESEARCH: "researcher",
            StepType.ANALYSIS: "researcher",
            StepType.CODE: "coder",
            StepType.PROCESSING: "coder",
            StepType.SYNTHESIS: "reporter",
        }
        return mapping.get(step_type, "researcher")

    async def _handle_research_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理研究步驟"""
        logger.info(f"處理研究步驟: {step.id}")

        researcher = self.conversation_manager.agents.get("researcher")
        if not researcher:
            return {
                "status": "simulated",
                "result": f"模擬研究步驟 {step.id} 的執行結果",
                "step_id": step.id,
            }

        # 準備研究輸入
        research_input = {
            "description": step.description,
            "inputs": step.inputs,
            "context": context,
        }

        result = await researcher.execute_research_step(research_input)

        return {
            "status": "completed",
            "result": result,
            "step_id": step.id,
            "agent_type": "researcher",
        }

    async def _handle_analysis_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理分析步驟"""
        logger.info(f"處理分析步驟: {step.id}")

        researcher = self.conversation_manager.agents.get("researcher")
        if not researcher:
            return {
                "status": "simulated",
                "result": f"模擬分析步驟 {step.id} 的執行結果",
                "step_id": step.id,
            }

        # 執行分析
        analysis_input = {
            "description": step.description,
            "inputs": step.inputs,
            "context": context,
            "analysis_type": "comprehensive",
        }

        result = await researcher.analyze_research_data(analysis_input)

        return {
            "status": "completed",
            "result": result,
            "step_id": step.id,
            "agent_type": "researcher",
        }

    async def _handle_code_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理程式碼步驟"""
        logger.info(f"處理程式碼步驟: {step.id}")

        coder = self.conversation_manager.agents.get("coder")
        if not coder:
            return {
                "status": "simulated",
                "result": f"模擬程式碼步驟 {step.id} 的執行結果",
                "step_id": step.id,
            }

        # 執行程式碼任務
        coding_input = {"description": step.description, "inputs": step.inputs, "context": context}

        result = await coder.execute_coding_step(coding_input)

        return {"status": "completed", "result": result, "step_id": step.id, "agent_type": "coder"}

    async def _handle_processing_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理資料處理步驟"""
        logger.info(f"處理資料處理步驟: {step.id}")

        coder = self.conversation_manager.agents.get("coder")
        if not coder:
            return {
                "status": "simulated",
                "result": f"模擬資料處理步驟 {step.id} 的執行結果",
                "step_id": step.id,
            }

        # 執行資料處理
        processing_input = {
            "description": step.description,
            "inputs": step.inputs,
            "context": context,
            "processing_type": "data_analysis",
        }

        result = await coder.process_data(processing_input)

        return {"status": "completed", "result": result, "step_id": step.id, "agent_type": "coder"}

    async def _handle_synthesis_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理綜合步驟"""
        logger.info(f"處理綜合步驟: {step.id}")

        reporter = self.conversation_manager.agents.get("reporter")
        if not reporter:
            return {
                "status": "simulated",
                "result": f"模擬綜合步驟 {step.id} 的執行結果",
                "step_id": step.id,
            }

        # 執行綜合報告
        synthesis_input = {
            "description": step.description,
            "inputs": step.inputs,
            "context": context,
            "synthesis_type": "comprehensive",
        }

        result = await reporter.synthesize_results(synthesis_input)

        return {
            "status": "completed",
            "result": result,
            "step_id": step.id,
            "agent_type": "reporter",
        }

    async def _generate_final_report(
        self, user_input: str, research_topic: str, execution_result: Dict[str, Any]
    ) -> str:
        """生成最終報告"""
        logger.info("生成最終報告")

        reporter = self.conversation_manager.agents.get("reporter")
        if not reporter:
            # 如果沒有報告者，生成一個簡單的報告
            return f"""# 研究報告: {research_topic}

## 用戶查詢
{user_input}

## 執行摘要
- 計劃狀態: {execution_result.get("plan_status", "unknown")}
- 總步驟數: {execution_result.get("total_steps", 0)}
- 完成步驟數: {execution_result.get("steps_by_status", {}).get("completed", 0)}
- 執行時間: {execution_result.get("execution_time", 0):.2f} 秒

## 研究結果
工作流執行已完成，詳細結果請參考執行記錄。

報告生成時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        # 準備報告上下文
        report_context = {
            "user_input": user_input,
            "research_topic": research_topic,
            "execution_result": execution_result,
            "locale": "zh-TW",
        }

        return await reporter.generate_final_report(report_context)

    async def cleanup(self):
        """清理資源"""
        await self.conversation_manager.cleanup()
        logger.info("研究工作流管理器已清理")

    def get_workflow_status(self) -> Dict[str, Any]:
        """獲取工作流狀態"""
        if not self.current_workflow:
            return {"status": "no_workflow"}

        return {
            "workflow_id": self.current_workflow.id,
            "workflow_name": self.current_workflow.name,
            "status": self.current_workflow.status.value,
            "steps_summary": self.workflow_controller.get_step_results(),
            "execution_summary": self.workflow_controller._get_execution_summary()
            if self.workflow_controller.current_plan
            else {},
        }


# 便利函數
async def run_simple_research(
    user_input: str, model_client: ChatCompletionClient, config: ConversationConfig = None
) -> Dict[str, Any]:
    """
    執行簡單研究工作流

    Args:
        user_input: 用戶輸入
        model_client: 聊天完成客戶端
        config: 對話配置

    Returns:
        Dict[str, Any]: 執行結果
    """
    workflow_manager = ResearchWorkflowManager(model_client, config)

    try:
        await workflow_manager.initialize()
        result = await workflow_manager.run_research_workflow(user_input)
        return result
    finally:
        await workflow_manager.cleanup()


async def run_advanced_research(
    user_input: str,
    model_client: ChatCompletionClient,
    workflow_type: str = "comprehensive",
    config: ConversationConfig = None,
) -> Dict[str, Any]:
    """
    執行高級研究工作流

    Args:
        user_input: 用戶輸入
        model_client: 聊天完成客戶端
        workflow_type: 工作流類型
        config: 對話配置

    Returns:
        Dict[str, Any]: 執行結果
    """
    # 為高級研究設置更詳細的配置
    if not config:
        config = ConversationConfig(
            enable_background_investigation=True,
            max_plan_iterations=3,
            max_step_iterations=5,
            enable_human_feedback=False,
            auto_accept_plan=True,
        )

    workflow_manager = ResearchWorkflowManager(model_client, config)

    try:
        await workflow_manager.initialize()
        result = await workflow_manager.run_research_workflow(user_input, workflow_type)
        return result
    finally:
        await workflow_manager.cleanup()
