# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
用戶控制接口

提供直觀的用戶控制和互動功能。
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.logging import get_logger
from .human_feedback_manager import HumanFeedbackManager, FeedbackType, FeedbackResponse

logger = get_logger(__name__)


class ControlAction(Enum):
    """控制動作"""

    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    SKIP_STEP = "skip_step"
    MODIFY_PLAN = "modify_plan"
    APPROVE_PLAN = "approve_plan"
    REJECT_PLAN = "reject_plan"


@dataclass
class UserCommand:
    """用戶命令"""

    action: ControlAction
    parameters: Dict[str, Any]
    timestamp: datetime
    command_id: str


class InteractiveUserInterface:
    """
    互動式用戶介面

    提供用戶控制工作流執行的介面。
    """

    def __init__(self, feedback_manager: HumanFeedbackManager):
        """
        初始化用戶介面

        Args:
            feedback_manager: 反饋管理器
        """
        self.feedback_manager = feedback_manager
        self.command_queue: asyncio.Queue = asyncio.Queue()
        self.control_handlers: Dict[ControlAction, Callable] = {}
        self.interface_state = {
            "active": False,
            "current_workflow": None,
            "user_preferences": {},
            "session_id": None,
        }

        # 設置預設控制處理器
        self._setup_control_handlers()

        logger.info("互動式用戶介面初始化完成")

    def _setup_control_handlers(self):
        """設置控制處理器"""
        self.control_handlers = {
            ControlAction.START: self._handle_start,
            ControlAction.PAUSE: self._handle_pause,
            ControlAction.RESUME: self._handle_resume,
            ControlAction.STOP: self._handle_stop,
            ControlAction.SKIP_STEP: self._handle_skip_step,
            ControlAction.MODIFY_PLAN: self._handle_modify_plan,
            ControlAction.APPROVE_PLAN: self._handle_approve_plan,
            ControlAction.REJECT_PLAN: self._handle_reject_plan,
        }

    async def start_interactive_session(self, session_id: str = None) -> str:
        """
        開始互動式會話

        Args:
            session_id: 會話ID

        Returns:
            str: 會話ID
        """
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.interface_state["active"] = True
        self.interface_state["session_id"] = session_id

        logger.info(f"開始互動式會話: {session_id}")
        return session_id

    async def display_plan_for_review(
        self, plan_data: Dict[str, Any], auto_approve_timeout: int = 30
    ) -> Dict[str, Any]:
        """
        顯示計劃供用戶審查

        Args:
            plan_data: 計劃資料
            auto_approve_timeout: 自動批准超時時間

        Returns:
            Dict[str, Any]: 審查結果
        """
        logger.info("顯示計劃供用戶審查")

        # 格式化計劃展示
        plan_display = self._format_plan_display(plan_data)

        print("=" * 60)
        print("📋 計劃審查")
        print("=" * 60)
        print(plan_display)
        print("\n" + "=" * 60)
        print("請選擇操作:")
        print("1. 批准計劃 (approve)")
        print("2. 拒絕計劃 (reject)")
        print("3. 修改計劃 (modify)")
        print(f"4. 自動批准 (將在 {auto_approve_timeout} 秒後自動批准)")
        print("=" * 60)

        # 請求用戶反饋
        response = await self.feedback_manager.request_feedback(
            FeedbackType.PLAN_REVIEW,
            "計劃審查",
            "請審查並回應此計劃",
            {"plan": plan_data},
            timeout_seconds=auto_approve_timeout,
        )

        return {
            "approved": response.response_type == "approve",
            "response_type": response.response_type,
            "modifications": response.data.get("modifications", {}),
            "comment": response.comment,
        }

    async def display_step_confirmation(
        self, step_data: Dict[str, Any], context: Dict[str, Any] = None
    ) -> bool:
        """
        顯示步驟確認

        Args:
            step_data: 步驟資料
            context: 上下文資料

        Returns:
            bool: 是否確認執行
        """
        logger.info("顯示步驟確認")

        print("\n" + "=" * 50)
        print("⚡ 步驟確認")
        print("=" * 50)
        print(f"步驟: {step_data.get('description', '未知步驟')}")
        print(f"類型: {step_data.get('step_type', '未知類型')}")
        print(f"預估時間: {step_data.get('estimated_time', '未知')} 秒")

        if step_data.get("inputs"):
            print(f"輸入參數: {step_data['inputs']}")

        print("\n請確認是否執行此步驟:")
        print("1. 確認執行 (y/yes)")
        print("2. 跳過此步驟 (s/skip)")
        print("3. 暫停工作流 (p/pause)")
        print("=" * 50)

        response = await self.feedback_manager.request_feedback(
            FeedbackType.STEP_CONFIRMATION,
            "步驟確認",
            f"確認執行步驟: {step_data.get('description')}",
            {"step": step_data, "context": context or {}},
            timeout_seconds=60,
        )

        return response.response_type == "approve"

    async def display_error_handling(
        self, error_info: Dict[str, Any], available_actions: List[str] = None
    ) -> str:
        """
        顯示錯誤處理選項

        Args:
            error_info: 錯誤資訊
            available_actions: 可用操作

        Returns:
            str: 選擇的處理方式
        """
        logger.info("顯示錯誤處理選項")

        print("\n" + "❌" * 20)
        print("🚨 執行錯誤")
        print("❌" * 20)
        print(f"錯誤類型: {error_info.get('type', '未知錯誤')}")
        print(f"錯誤訊息: {error_info.get('message', '無訊息')}")

        if error_info.get("step"):
            print(f"發生步驟: {error_info['step']}")

        if error_info.get("stack_trace"):
            print(f"詳細錯誤: {error_info['stack_trace'][:200]}...")

        print("\n請選擇處理方式:")
        actions = available_actions or ["重試", "跳過", "停止執行"]
        for i, action in enumerate(actions, 1):
            print(f"{i}. {action}")
        print("❌" * 20)

        response = await self.feedback_manager.request_feedback(
            FeedbackType.ERROR_HANDLING,
            "錯誤處理",
            "選擇錯誤處理方式",
            {"error": error_info, "available_actions": actions},
            timeout_seconds=120,
        )

        return response.data.get("action", "stop")

    async def display_execution_status(
        self, workflow_status: Dict[str, Any], show_details: bool = True
    ):
        """
        顯示執行狀態

        Args:
            workflow_status: 工作流狀態
            show_details: 是否顯示詳細資訊
        """
        print("\n" + "📊" * 20)
        print("📈 執行狀態")
        print("📊" * 20)

        # 基本狀態
        print(f"工作流狀態: {workflow_status.get('status', '未知')}")
        print(f"當前步驟: {workflow_status.get('current_step', 0)}")
        print(f"總步驟數: {workflow_status.get('total_steps', 0)}")

        # 進度條
        current = workflow_status.get("current_step", 0)
        total = workflow_status.get("total_steps", 1)
        progress = min(current / total * 100, 100) if total > 0 else 0

        progress_bar = "█" * int(progress // 5) + "░" * (20 - int(progress // 5))
        print(f"進度: [{progress_bar}] {progress:.1f}%")

        if show_details:
            # 步驟詳情
            steps = workflow_status.get("steps", [])
            if steps:
                print("\n步驟詳情:")
                for i, step in enumerate(steps):
                    status_icon = self._get_status_icon(step.get("status", "pending"))
                    print(f"  {status_icon} 步驟 {i + 1}: {step.get('description', '未知')}")

                    if step.get("execution_time"):
                        print(f"      ⏱️  執行時間: {step['execution_time']:.2f}s")

                    if step.get("error"):
                        print(f"      ❌ 錯誤: {step['error']}")

        # 執行統計
        if workflow_status.get("execution_stats"):
            stats = workflow_status["execution_stats"]
            print(f"\n📈 執行統計:")
            print(f"  - 總執行時間: {stats.get('total_time', 0):.2f}s")
            print(f"  - 成功步驟: {stats.get('successful_steps', 0)}")
            print(f"  - 失敗步驟: {stats.get('failed_steps', 0)}")

        print("📊" * 20)

    async def display_result_summary(self, results: Dict[str, Any], include_details: bool = True):
        """
        顯示結果摘要

        Args:
            results: 執行結果
            include_details: 是否包含詳細資訊
        """
        print("\n" + "🎉" * 20)
        print("📋 執行結果摘要")
        print("🎉" * 20)

        # 基本結果
        success = results.get("success", False)
        status_icon = "✅" if success else "❌"
        status_text = "成功" if success else "失敗"

        print(f"{status_icon} 執行狀態: {status_text}")
        print(f"📊 總執行時間: {results.get('execution_time', 0):.2f}s")

        if results.get("research_topic"):
            print(f"🔍 研究主題: {results['research_topic']}")

        # 結果詳情
        if include_details and results.get("execution_result"):
            exec_result = results["execution_result"]
            print(f"\n📈 執行詳情:")
            print(f"  - 計劃狀態: {exec_result.get('plan_status', '未知')}")
            print(f"  - 完成步驟: {exec_result.get('steps_by_status', {}).get('completed', 0)}")
            print(f"  - 失敗步驟: {exec_result.get('steps_by_status', {}).get('failed', 0)}")

        # 最終報告
        if results.get("final_report"):
            report = results["final_report"]
            print(f"\n📄 最終報告:")
            # 顯示報告前500字符
            if len(report) > 500:
                print(f"{report[:500]}...")
                print("\n[報告已截斷，完整報告請查看詳細輸出]")
            else:
                print(report)

        # 錯誤資訊
        if not success and results.get("error"):
            print(f"\n❌ 錯誤資訊: {results['error']}")

        print("🎉" * 20)

    def _format_plan_display(self, plan_data: Dict[str, Any]) -> str:
        """格式化計劃顯示"""
        lines = []

        lines.append(f"📋 計劃名稱: {plan_data.get('name', '未命名計劃')}")
        lines.append(f"📝 描述: {plan_data.get('description', '無描述')}")

        if plan_data.get("estimated_time"):
            lines.append(f"⏱️  預估時間: {plan_data['estimated_time']} 分鐘")

        steps = plan_data.get("steps", [])
        if steps:
            lines.append(f"\n📚 計劃步驟 ({len(steps)} 個):")
            for i, step in enumerate(steps, 1):
                step_desc = step.get("description", "未知步驟")
                step_type = step.get("step_type", "未知")
                lines.append(f"  {i}. [{step_type}] {step_desc}")

                if step.get("expected_output"):
                    lines.append(f"      📤 預期輸出: {step['expected_output']}")

                if step.get("dependencies"):
                    deps = ", ".join(step["dependencies"])
                    lines.append(f"      🔗 依賴: {deps}")

        return "\n".join(lines)

    def _get_status_icon(self, status: str) -> str:
        """獲取狀態圖示"""
        icons = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "skipped": "⏭️",
            "cancelled": "🚫",
        }
        return icons.get(status.lower(), "❓")

    async def _handle_start(self, command: UserCommand) -> Dict[str, Any]:
        """處理開始命令"""
        logger.info("處理開始命令")
        return {"status": "started", "message": "工作流已開始"}

    async def _handle_pause(self, command: UserCommand) -> Dict[str, Any]:
        """處理暫停命令"""
        logger.info("處理暫停命令")
        return {"status": "paused", "message": "工作流已暫停"}

    async def _handle_resume(self, command: UserCommand) -> Dict[str, Any]:
        """處理恢復命令"""
        logger.info("處理恢復命令")
        return {"status": "resumed", "message": "工作流已恢復"}

    async def _handle_stop(self, command: UserCommand) -> Dict[str, Any]:
        """處理停止命令"""
        logger.info("處理停止命令")
        return {"status": "stopped", "message": "工作流已停止"}

    async def _handle_skip_step(self, command: UserCommand) -> Dict[str, Any]:
        """處理跳過步驟命令"""
        step_id = command.parameters.get("step_id")
        logger.info(f"處理跳過步驟命令: {step_id}")
        return {"status": "skipped", "step_id": step_id, "message": f"步驟 {step_id} 已跳過"}

    async def _handle_modify_plan(self, command: UserCommand) -> Dict[str, Any]:
        """處理修改計劃命令"""
        modifications = command.parameters.get("modifications", {})
        logger.info("處理修改計劃命令")
        return {"status": "modified", "modifications": modifications, "message": "計劃已修改"}

    async def _handle_approve_plan(self, command: UserCommand) -> Dict[str, Any]:
        """處理批准計劃命令"""
        logger.info("處理批准計劃命令")
        return {"status": "approved", "message": "計劃已批准"}

    async def _handle_reject_plan(self, command: UserCommand) -> Dict[str, Any]:
        """處理拒絕計劃命令"""
        reason = command.parameters.get("reason", "無原因")
        logger.info("處理拒絕計劃命令")
        return {"status": "rejected", "reason": reason, "message": "計劃已拒絕"}

    async def send_user_command(
        self, action: ControlAction, parameters: Dict[str, Any] = None
    ) -> str:
        """
        發送用戶命令

        Args:
            action: 控制動作
            parameters: 參數

        Returns:
            str: 命令ID
        """
        command_id = f"cmd_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        command = UserCommand(
            action=action,
            parameters=parameters or {},
            timestamp=datetime.now(),
            command_id=command_id,
        )

        await self.command_queue.put(command)
        logger.info(f"用戶命令已發送: {action.value} - {command_id}")

        return command_id

    async def get_next_command(self, timeout: float = None) -> Optional[UserCommand]:
        """
        獲取下一個用戶命令

        Args:
            timeout: 超時時間

        Returns:
            Optional[UserCommand]: 用戶命令
        """
        try:
            if timeout:
                return await asyncio.wait_for(self.command_queue.get(), timeout=timeout)
            else:
                return await self.command_queue.get()
        except asyncio.TimeoutError:
            return None

    def set_user_preferences(self, preferences: Dict[str, Any]):
        """設置用戶偏好"""
        self.interface_state["user_preferences"].update(preferences)
        logger.info("用戶偏好已更新")

    def get_interface_state(self) -> Dict[str, Any]:
        """獲取介面狀態"""
        return self.interface_state.copy()

    async def cleanup(self):
        """清理資源"""
        self.interface_state["active"] = False

        # 清空命令隊列
        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info("互動式用戶介面已清理")


# 便利函數
async def create_interactive_session(
    feedback_manager: HumanFeedbackManager = None,
) -> InteractiveUserInterface:
    """創建互動式會話"""
    if not feedback_manager:
        feedback_manager = HumanFeedbackManager()

    ui = InteractiveUserInterface(feedback_manager)
    session_id = await ui.start_interactive_session()

    logger.info(f"互動式會話已創建: {session_id}")
    return ui


async def display_welcome_message():
    """顯示歡迎訊息"""
    print("\n" + "🎉" * 30)
    print("🤖 歡迎使用 AutoGen 研究工作流系統")
    print("🎉" * 30)
    print("這是一個智能的研究和分析工作流系統，支持：")
    print("✨ 智能計劃生成")
    print("🔍 自動網路搜尋")
    print("💻 程式碼執行分析")
    print("📊 互動式結果展示")
    print("👥 人機協作決策")
    print("\n準備開始您的研究之旅...")
    print("🎉" * 30)
