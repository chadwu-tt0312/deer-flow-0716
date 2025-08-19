# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
互動式工作流管理器

整合人機互動功能到工作流執行中。
"""

import asyncio
from typing import Dict, List, Any, Optional
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

from src.logging import get_logger
from ..controllers.conversation_manager import ConversationConfig, WorkflowState
from ..workflows.research_workflow import ResearchWorkflowManager
from .human_feedback_manager import HumanFeedbackManager, FeedbackType
from .user_interface import InteractiveUserInterface, ControlAction

logger = get_logger(__name__)


class InteractiveWorkflowManager:
    """
    互動式工作流管理器

    將人機互動功能整合到研究工作流中，提供用戶控制和反饋機制。
    """

    def __init__(
        self,
        model_client: ChatCompletionClient,
        config: ConversationConfig = None,
        enable_interaction: bool = True,
    ):
        """
        初始化互動式工作流管理器

        Args:
            model_client: 聊天完成客戶端
            config: 對話配置
            enable_interaction: 是否啟用互動功能
        """
        self.model_client = model_client
        self.enable_interaction = enable_interaction

        # 設置互動配置
        if config is None:
            config = ConversationConfig()

        if enable_interaction:
            config.enable_human_feedback = True
            config.auto_accept_plan = False

        self.config = config

        # 初始化組件
        self.workflow_manager = ResearchWorkflowManager(model_client, config)
        self.feedback_manager = HumanFeedbackManager()
        self.user_interface = InteractiveUserInterface(self.feedback_manager)

        # 工作流狀態
        self.current_session_id: Optional[str] = None
        self.execution_state = {
            "status": "idle",
            "current_step": 0,
            "total_steps": 0,
            "paused": False,
            "user_control_enabled": enable_interaction,
        }

        logger.info(f"互動式工作流管理器初始化完成 (互動模式: {enable_interaction})")

    async def run_interactive_research_workflow(
        self, user_input: str, workflow_type: str = "interactive"
    ) -> Dict[str, Any]:
        """
        執行互動式研究工作流

        Args:
            user_input: 用戶輸入
            workflow_type: 工作流類型

        Returns:
            Dict[str, Any]: 執行結果
        """
        logger.info(f"開始執行互動式研究工作流: {user_input}")

        try:
            # 啟動互動會話
            if self.enable_interaction:
                self.current_session_id = await self.user_interface.start_interactive_session()
                await self._display_welcome()

            # 初始化工作流管理器
            await self.workflow_manager.initialize()

            # 第一階段：協調者分析（非互動）
            await self._update_status("coordinator_analysis", "執行協調者分析...")
            coordinator_result = await self.workflow_manager._coordinator_analysis(user_input)
            research_topic = coordinator_result.get("research_topic", user_input)

            # 第二階段：背景調查（可選）
            background_info = ""
            if self.config.enable_background_investigation:
                await self._update_status("background_investigation", "執行背景調查...")
                background_info = await self.workflow_manager._background_investigation(
                    research_topic
                )

            # 第三階段：計劃生成
            await self._update_status("planning", "生成執行計劃...")
            plan_result = await self.workflow_manager._generate_plan(
                user_input, research_topic, background_info
            )

            # 第四階段：計劃審查（互動）
            if self.enable_interaction:
                plan_approved = await self._handle_plan_review(plan_result)
                if not plan_approved:
                    return {
                        "success": False,
                        "error": "用戶拒絕了執行計劃",
                        "user_input": user_input,
                        "timestamp": datetime.now().isoformat(),
                    }

            # 第五階段：工作流執行（互動）
            await self._update_status("execution", "執行工作流...")
            execution_result = await self._execute_interactive_workflow(
                plan_result,
                research_topic,
                {
                    "user_input": user_input,
                    "research_topic": research_topic,
                    "background_info": background_info,
                    "plan": plan_result,
                },
            )

            # 第六階段：報告生成
            await self._update_status("reporting", "生成最終報告...")
            final_report = await self.workflow_manager._generate_final_report(
                user_input, research_topic, execution_result
            )

            # 顯示最終結果
            if self.enable_interaction:
                await self._display_final_results(
                    {
                        "success": True,
                        "user_input": user_input,
                        "research_topic": research_topic,
                        "execution_result": execution_result,
                        "final_report": final_report,
                        "execution_time": execution_result.get("execution_time", 0),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            return {
                "success": True,
                "user_input": user_input,
                "research_topic": research_topic,
                "workflow_plan": plan_result,
                "execution_result": execution_result,
                "final_report": final_report,
                "execution_time": execution_result.get("execution_time", 0),
                "timestamp": datetime.now().isoformat(),
                "session_id": self.current_session_id,
                "interaction_enabled": self.enable_interaction,
            }

        except Exception as e:
            logger.error(f"互動式工作流執行失敗: {e}")

            if self.enable_interaction:
                await self._display_error(
                    {
                        "type": "workflow_error",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            return {
                "success": False,
                "error": str(e),
                "user_input": user_input,
                "timestamp": datetime.now().isoformat(),
                "session_id": self.current_session_id,
            }

        finally:
            await self.cleanup()

    async def _handle_plan_review(self, plan_result: Dict[str, Any]) -> bool:
        """處理計劃審查"""
        logger.info("處理計劃審查")

        if not self.enable_interaction:
            return True

        try:
            # 顯示計劃供用戶審查
            review_result = await self.user_interface.display_plan_for_review(
                plan_result, auto_approve_timeout=60
            )

            # 處理審查結果
            if review_result["approved"]:
                logger.info("用戶批准了計劃")
                return True
            elif review_result["response_type"] == "modify":
                # 處理計劃修改
                modifications = review_result.get("modifications", {})
                logger.info(f"用戶要求修改計劃: {modifications}")

                # 這裡可以實現計劃修改邏輯
                # 暫時返回原計劃
                return True
            else:
                logger.info("用戶拒絕了計劃")
                return False

        except Exception as e:
            logger.error(f"計劃審查處理失敗: {e}")
            return False

    async def _execute_interactive_workflow(
        self, plan_result: Dict[str, Any], research_topic: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """執行互動式工作流"""
        logger.info("執行互動式工作流")

        # 創建工作流計劃
        workflow_plan = self.workflow_manager._create_workflow_plan(plan_result, research_topic)

        # 更新執行狀態
        self.execution_state["total_steps"] = len(workflow_plan.steps)
        self.execution_state["current_step"] = 0
        self.execution_state["status"] = "running"

        # 如果啟用互動，註冊步驟處理器
        if self.enable_interaction:
            self._register_interactive_step_handlers()

        # 執行工作流
        execution_result = await self.workflow_manager.workflow_controller.execute_plan(
            workflow_plan, context
        )

        return execution_result

    def _register_interactive_step_handlers(self):
        """註冊互動式步驟處理器"""
        # 包裝原有的步驟處理器，添加互動功能
        original_handlers = self.workflow_manager.workflow_controller.step_handlers.copy()

        async def interactive_handler_wrapper(original_handler):
            async def wrapper(step, context):
                # 步驟確認
                if self.enable_interaction:
                    step_data = {
                        "id": step.id,
                        "description": step.description,
                        "step_type": step.step_type.value,
                        "estimated_time": step.timeout_seconds,
                    }

                    confirmed = await self.user_interface.display_step_confirmation(
                        step_data, context
                    )
                    if not confirmed:
                        # 用戶選擇跳過此步驟
                        return {
                            "status": "skipped",
                            "message": "用戶跳過此步驟",
                            "step_id": step.id,
                        }

                # 更新進度
                self.execution_state["current_step"] += 1
                await self._update_progress()

                try:
                    # 執行原始處理器
                    result = await original_handler(step, context)

                    # 顯示步驟結果（如果啟用互動）
                    if self.enable_interaction and result:
                        await self._display_step_result(step, result)

                    return result

                except Exception as e:
                    # 錯誤處理
                    if self.enable_interaction:
                        error_info = {
                            "type": "step_error",
                            "message": str(e),
                            "step": step.description,
                            "step_id": step.id,
                        }

                        action = await self.user_interface.display_error_handling(error_info)

                        if action == "重試":
                            # 重試執行
                            return await original_handler(step, context)
                        elif action == "跳過":
                            # 跳過此步驟
                            return {
                                "status": "skipped",
                                "message": "因錯誤而跳過",
                                "error": str(e),
                                "step_id": step.id,
                            }
                        else:
                            # 停止執行
                            raise e
                    else:
                        raise e

            return wrapper

        # 替換所有處理器
        for step_type, handler in original_handlers.items():
            self.workflow_manager.workflow_controller.step_handlers[step_type] = (
                interactive_handler_wrapper(handler)
            )

    async def _update_status(self, status: str, message: str):
        """更新執行狀態"""
        self.execution_state["status"] = status

        if self.enable_interaction:
            print(f"\n🔄 {message}")

        logger.info(f"狀態更新: {status} - {message}")

    async def _update_progress(self):
        """更新進度"""
        if self.enable_interaction:
            current = self.execution_state["current_step"]
            total = self.execution_state["total_steps"]

            if total > 0:
                progress = current / total * 100
                progress_bar = "█" * int(progress // 5) + "░" * (20 - int(progress // 5))
                print(f"\n📈 進度: [{progress_bar}] {progress:.1f}% ({current}/{total})")

    async def _display_step_result(self, step, result):
        """顯示步驟結果"""
        print(f"\n✅ 步驟完成: {step.description}")

        if result.get("status") == "completed":
            print("   狀態: 成功完成")
        elif result.get("status") == "skipped":
            print("   狀態: 已跳過")
        else:
            print(f"   狀態: {result.get('status', '未知')}")

        # 顯示簡要結果
        if result.get("result"):
            result_summary = str(result["result"])
            if len(result_summary) > 100:
                result_summary = result_summary[:100] + "..."
            print(f"   結果: {result_summary}")

    async def _display_welcome(self):
        """顯示歡迎訊息"""
        print("\n" + "🚀" * 30)
        print("🤖 AutoGen 互動式研究工作流")
        print("🚀" * 30)
        print("歡迎使用互動式研究系統！")
        print("在執行過程中，您可以：")
        print("✅ 審查和修改計劃")
        print("⏸️  暫停或跳過步驟")
        print("🛠️  處理執行錯誤")
        print("📊 即時查看進度")
        print("\n準備開始...")
        print("🚀" * 30)

    async def _display_final_results(self, results: Dict[str, Any]):
        """顯示最終結果"""
        await self.user_interface.display_result_summary(results, include_details=True)

    async def _display_error(self, error_info: Dict[str, Any]):
        """顯示錯誤資訊"""
        print("\n" + "❌" * 30)
        print("🚨 工作流執行錯誤")
        print("❌" * 30)
        print(f"錯誤類型: {error_info.get('type', '未知')}")
        print(f"錯誤訊息: {error_info.get('message', '無訊息')}")
        print(f"時間: {error_info.get('timestamp', '')}")
        print("❌" * 30)

    async def pause_workflow(self) -> bool:
        """暫停工作流"""
        if self.execution_state["status"] == "running":
            self.execution_state["paused"] = True
            logger.info("工作流已暫停")

            if self.enable_interaction:
                print("\n⏸️  工作流已暫停")

            return True
        return False

    async def resume_workflow(self) -> bool:
        """恢復工作流"""
        if self.execution_state["paused"]:
            self.execution_state["paused"] = False
            logger.info("工作流已恢復")

            if self.enable_interaction:
                print("\n▶️  工作流已恢復")

            return True
        return False

    async def stop_workflow(self) -> bool:
        """停止工作流"""
        self.execution_state["status"] = "stopped"
        logger.info("工作流已停止")

        if self.enable_interaction:
            print("\n⏹️  工作流已停止")

        return True

    def get_execution_status(self) -> Dict[str, Any]:
        """獲取執行狀態"""
        return {
            **self.execution_state,
            "session_id": self.current_session_id,
            "feedback_stats": self.feedback_manager.get_feedback_statistics(),
            "interface_state": self.user_interface.get_interface_state(),
        }

    async def cleanup(self):
        """清理資源"""
        try:
            await self.workflow_manager.cleanup()
            await self.feedback_manager.cleanup()
            await self.user_interface.cleanup()

            self.execution_state["status"] = "idle"
            self.current_session_id = None

            logger.info("互動式工作流管理器已清理")

        except Exception as e:
            logger.error(f"清理資源失敗: {e}")


# 便利函數
async def run_interactive_research(
    user_input: str,
    model_client: ChatCompletionClient,
    enable_interaction: bool = True,
    config: ConversationConfig = None,
) -> Dict[str, Any]:
    """
    執行互動式研究工作流

    Args:
        user_input: 用戶輸入
        model_client: 聊天完成客戶端
        enable_interaction: 是否啟用互動功能
        config: 對話配置

    Returns:
        Dict[str, Any]: 執行結果
    """
    manager = InteractiveWorkflowManager(model_client, config, enable_interaction)

    try:
        result = await manager.run_interactive_research_workflow(user_input)
        return result
    finally:
        await manager.cleanup()


async def run_non_interactive_research(
    user_input: str, model_client: ChatCompletionClient, config: ConversationConfig = None
) -> Dict[str, Any]:
    """
    執行非互動式研究工作流（自動執行）

    Args:
        user_input: 用戶輸入
        model_client: 聊天完成客戶端
        config: 對話配置

    Returns:
        Dict[str, Any]: 執行結果
    """
    return await run_interactive_research(user_input, model_client, False, config)
