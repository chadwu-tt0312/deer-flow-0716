# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
人機互動反饋管理器

負責處理用戶反饋、計劃審查和互動式決策。
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.logging import get_logger

logger = get_logger(__name__)


class FeedbackType(Enum):
    """反饋類型"""

    PLAN_REVIEW = "plan_review"
    STEP_CONFIRMATION = "step_confirmation"
    ERROR_HANDLING = "error_handling"
    EXECUTION_PAUSE = "execution_pause"
    RESULT_VALIDATION = "result_validation"
    WORKFLOW_MODIFICATION = "workflow_modification"


class FeedbackStatus(Enum):
    """反饋狀態"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    CANCELLED = "cancelled"


@dataclass
class FeedbackRequest:
    """反饋請求"""

    id: str
    feedback_type: FeedbackType
    title: str
    message: str
    context: Dict[str, Any]
    options: List[Dict[str, Any]] = field(default_factory=list)
    timeout_seconds: int = 300
    created_at: datetime = field(default_factory=datetime.now)
    status: FeedbackStatus = FeedbackStatus.PENDING
    user_response: Optional[Dict[str, Any]] = None
    responded_at: Optional[datetime] = None


@dataclass
class FeedbackResponse:
    """反饋回應"""

    request_id: str
    response_type: str  # approve, reject, modify, cancel
    data: Dict[str, Any] = field(default_factory=dict)
    comment: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class HumanFeedbackManager:
    """
    人機互動反饋管理器

    負責管理用戶反饋請求、處理互動式決策和計劃審查。
    """

    def __init__(self):
        """初始化反饋管理器"""
        self.pending_requests: Dict[str, FeedbackRequest] = {}
        self.completed_requests: List[FeedbackRequest] = []
        self.feedback_handlers: Dict[FeedbackType, Callable] = {}
        self.response_queue: asyncio.Queue = asyncio.Queue()

        # 設置預設處理器
        self._setup_default_handlers()

        logger.info("人機互動反饋管理器初始化完成")

    def _setup_default_handlers(self):
        """設置預設反饋處理器"""
        self.feedback_handlers = {
            FeedbackType.PLAN_REVIEW: self._handle_plan_review,
            FeedbackType.STEP_CONFIRMATION: self._handle_step_confirmation,
            FeedbackType.ERROR_HANDLING: self._handle_error_handling,
            FeedbackType.EXECUTION_PAUSE: self._handle_execution_pause,
            FeedbackType.RESULT_VALIDATION: self._handle_result_validation,
            FeedbackType.WORKFLOW_MODIFICATION: self._handle_workflow_modification,
        }

    async def request_feedback(
        self,
        feedback_type: FeedbackType,
        title: str,
        message: str,
        context: Dict[str, Any],
        options: List[Dict[str, Any]] = None,
        timeout_seconds: int = 300,
    ) -> FeedbackResponse:
        """
        請求用戶反饋

        Args:
            feedback_type: 反饋類型
            title: 標題
            message: 訊息
            context: 上下文資料
            options: 可選選項
            timeout_seconds: 超時時間

        Returns:
            FeedbackResponse: 用戶回應
        """
        request_id = f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        request = FeedbackRequest(
            id=request_id,
            feedback_type=feedback_type,
            title=title,
            message=message,
            context=context,
            options=options or [],
            timeout_seconds=timeout_seconds,
        )

        logger.info(f"請求用戶反饋: {feedback_type.value} - {title}")

        # 儲存請求
        self.pending_requests[request_id] = request

        # 調用相應的處理器
        handler = self.feedback_handlers.get(feedback_type)
        if handler:
            try:
                response = await handler(request)
                return response
            except Exception as e:
                logger.error(f"反饋處理器執行失敗: {e}")
                # 回傳預設拒絕回應
                return FeedbackResponse(
                    request_id=request_id, response_type="reject", comment=f"處理失敗: {str(e)}"
                )
        else:
            logger.warning(f"未找到反饋處理器: {feedback_type.value}")
            return FeedbackResponse(
                request_id=request_id, response_type="approve", comment="自動批准（未找到處理器）"
            )

    async def _handle_plan_review(self, request: FeedbackRequest) -> FeedbackResponse:
        """處理計劃審查反饋"""
        logger.info(f"處理計劃審查: {request.id}")

        plan_data = request.context.get("plan", {})

        # 顯示計劃資訊給用戶
        plan_summary = self._format_plan_summary(plan_data)

        # 模擬用戶互動（實際實現中應該等待真實用戶輸入）
        user_choice = await self._simulate_user_interaction(
            request,
            f"請審查以下計劃：\n\n{plan_summary}\n\n您是否批准此計劃？",
            ["批准", "拒絕", "修改"],
        )

        if user_choice == "批准":
            response = FeedbackResponse(
                request_id=request.id, response_type="approve", comment="用戶批准計劃"
            )
        elif user_choice == "拒絕":
            response = FeedbackResponse(
                request_id=request.id, response_type="reject", comment="用戶拒絕計劃"
            )
        else:  # 修改
            # 模擬修改建議
            modifications = {
                "add_steps": ["增加資料驗證步驟"],
                "modify_steps": {"step_1": "增加更詳細的分析"},
                "remove_steps": [],
            }

            response = FeedbackResponse(
                request_id=request.id,
                response_type="modify",
                data={"modifications": modifications},
                comment="用戶要求修改計劃",
            )

        await self._complete_request(request, response)
        return response

    async def _handle_step_confirmation(self, request: FeedbackRequest) -> FeedbackResponse:
        """處理步驟確認反饋"""
        logger.info(f"處理步驟確認: {request.id}")

        step_data = request.context.get("step", {})
        step_description = step_data.get("description", "未知步驟")

        user_choice = await self._simulate_user_interaction(
            request, f"即將執行步驟：{step_description}\n\n是否繼續？", ["繼續", "跳過", "暫停"]
        )

        if user_choice == "繼續":
            response_type = "approve"
        elif user_choice == "跳過":
            response_type = "reject"
        else:  # 暫停
            response_type = "cancel"

        response = FeedbackResponse(
            request_id=request.id, response_type=response_type, comment=f"用戶選擇：{user_choice}"
        )

        await self._complete_request(request, response)
        return response

    async def _handle_error_handling(self, request: FeedbackRequest) -> FeedbackResponse:
        """處理錯誤處理反饋"""
        logger.info(f"處理錯誤處理: {request.id}")

        error_info = request.context.get("error", {})
        error_message = error_info.get("message", "未知錯誤")

        user_choice = await self._simulate_user_interaction(
            request,
            f"執行過程中發生錯誤：{error_message}\n\n請選擇處理方式：",
            ["重試", "跳過", "停止執行"],
        )

        response_data = {}
        if user_choice == "重試":
            response_type = "approve"
            response_data["action"] = "retry"
        elif user_choice == "跳過":
            response_type = "approve"
            response_data["action"] = "skip"
        else:  # 停止執行
            response_type = "reject"
            response_data["action"] = "stop"

        response = FeedbackResponse(
            request_id=request.id,
            response_type=response_type,
            data=response_data,
            comment=f"用戶選擇：{user_choice}",
        )

        await self._complete_request(request, response)
        return response

    async def _handle_execution_pause(self, request: FeedbackRequest) -> FeedbackResponse:
        """處理執行暫停反饋"""
        logger.info(f"處理執行暫停: {request.id}")

        current_step = request.context.get("current_step", {})

        user_choice = await self._simulate_user_interaction(
            request,
            f"工作流已暫停在步驟：{current_step.get('description', '未知')}\n\n請選擇操作：",
            ["繼續執行", "修改計劃", "停止執行"],
        )

        if user_choice == "繼續執行":
            response_type = "approve"
        elif user_choice == "修改計劃":
            response_type = "modify"
        else:  # 停止執行
            response_type = "reject"

        response = FeedbackResponse(
            request_id=request.id, response_type=response_type, comment=f"用戶選擇：{user_choice}"
        )

        await self._complete_request(request, response)
        return response

    async def _handle_result_validation(self, request: FeedbackRequest) -> FeedbackResponse:
        """處理結果驗證反饋"""
        logger.info(f"處理結果驗證: {request.id}")

        result_data = request.context.get("result", {})

        user_choice = await self._simulate_user_interaction(
            request,
            f"請驗證以下執行結果：\n\n{self._format_result_summary(result_data)}\n\n結果是否滿意？",
            ["滿意", "需要改進", "重新執行"],
        )

        if user_choice == "滿意":
            response_type = "approve"
        elif user_choice == "需要改進":
            response_type = "modify"
        else:  # 重新執行
            response_type = "reject"

        response = FeedbackResponse(
            request_id=request.id,
            response_type=response_type,
            comment=f"用戶驗證結果：{user_choice}",
        )

        await self._complete_request(request, response)
        return response

    async def _handle_workflow_modification(self, request: FeedbackRequest) -> FeedbackResponse:
        """處理工作流修改反饋"""
        logger.info(f"處理工作流修改: {request.id}")

        modification_suggestions = request.context.get("suggestions", [])

        user_choice = await self._simulate_user_interaction(
            request,
            f"建議的工作流修改：\n\n{self._format_modifications(modification_suggestions)}\n\n是否接受這些修改？",
            ["接受", "部分接受", "拒絕"],
        )

        response_data = {}
        if user_choice == "接受":
            response_type = "approve"
            response_data["accepted_modifications"] = modification_suggestions
        elif user_choice == "部分接受":
            # 模擬部分接受
            response_type = "modify"
            response_data["accepted_modifications"] = modification_suggestions[
                : len(modification_suggestions) // 2
            ]
        else:  # 拒絕
            response_type = "reject"

        response = FeedbackResponse(
            request_id=request.id,
            response_type=response_type,
            data=response_data,
            comment=f"用戶對修改的回應：{user_choice}",
        )

        await self._complete_request(request, response)
        return response

    async def _simulate_user_interaction(
        self, request: FeedbackRequest, prompt: str, options: List[str]
    ) -> str:
        """
        模擬用戶互動（實際實現中應該替換為真實的用戶介面）

        Args:
            request: 反饋請求
            prompt: 提示訊息
            options: 可選選項

        Returns:
            str: 用戶選擇
        """
        logger.info(f"模擬用戶互動 - {request.feedback_type.value}")
        logger.info(f"提示: {prompt}")
        logger.info(f"選項: {options}")

        # 在實際實現中，這裡應該：
        # 1. 顯示用戶介面
        # 2. 等待用戶輸入
        # 3. 處理超時
        # 4. 返回用戶選擇

        # 暫時模擬智能預設選擇
        await asyncio.sleep(0.1)  # 模擬用戶思考時間

        # 根據反饋類型提供智能預設回應
        if request.feedback_type == FeedbackType.PLAN_REVIEW:
            return "批准"  # 預設批准計劃
        elif request.feedback_type == FeedbackType.STEP_CONFIRMATION:
            return "繼續"  # 預設繼續執行
        elif request.feedback_type == FeedbackType.ERROR_HANDLING:
            return "重試"  # 預設重試
        elif request.feedback_type == FeedbackType.EXECUTION_PAUSE:
            return "繼續執行"  # 預設繼續
        elif request.feedback_type == FeedbackType.RESULT_VALIDATION:
            return "滿意"  # 預設滿意
        elif request.feedback_type == FeedbackType.WORKFLOW_MODIFICATION:
            return "接受"  # 預設接受修改
        else:
            return options[0] if options else "approve"

    def _format_plan_summary(self, plan_data: Dict[str, Any]) -> str:
        """格式化計劃摘要"""
        if not plan_data:
            return "無計劃資料"

        summary = []
        summary.append(f"計劃名稱: {plan_data.get('name', '未命名')}")
        summary.append(f"描述: {plan_data.get('description', '無描述')}")

        steps = plan_data.get("steps", [])
        if steps:
            summary.append(f"\n計劃步驟 ({len(steps)} 個):")
            for i, step in enumerate(steps, 1):
                summary.append(f"  {i}. {step.get('description', '未知步驟')}")

        return "\n".join(summary)

    def _format_result_summary(self, result_data: Dict[str, Any]) -> str:
        """格式化結果摘要"""
        if not result_data:
            return "無結果資料"

        summary = []
        summary.append(f"執行狀態: {result_data.get('status', '未知')}")

        if "output" in result_data:
            output = str(result_data["output"])
            if len(output) > 200:
                output = output[:200] + "..."
            summary.append(f"輸出: {output}")

        if "execution_time" in result_data:
            summary.append(f"執行時間: {result_data['execution_time']:.2f} 秒")

        return "\n".join(summary)

    def _format_modifications(self, modifications: List[Dict[str, Any]]) -> str:
        """格式化修改建議"""
        if not modifications:
            return "無修改建議"

        summary = []
        for i, mod in enumerate(modifications, 1):
            summary.append(f"{i}. {mod.get('description', '未知修改')}")
            if mod.get("impact"):
                summary.append(f"   影響: {mod['impact']}")

        return "\n".join(summary)

    async def _complete_request(self, request: FeedbackRequest, response: FeedbackResponse):
        """完成反饋請求"""
        request.status = (
            FeedbackStatus.APPROVED
            if response.response_type == "approve"
            else FeedbackStatus.REJECTED
        )
        request.user_response = response.data
        request.responded_at = datetime.now()

        # 從待處理列表移除
        if request.id in self.pending_requests:
            del self.pending_requests[request.id]

        # 添加到已完成列表
        self.completed_requests.append(request)

        logger.info(f"反饋請求已完成: {request.id} - {response.response_type}")

    def get_pending_requests(self) -> List[FeedbackRequest]:
        """獲取待處理的反饋請求"""
        return list(self.pending_requests.values())

    def get_completed_requests(self) -> List[FeedbackRequest]:
        """獲取已完成的反饋請求"""
        return self.completed_requests.copy()

    def get_feedback_statistics(self) -> Dict[str, Any]:
        """獲取反饋統計資訊"""
        total_requests = len(self.completed_requests)
        if total_requests == 0:
            return {
                "total_requests": 0,
                "approval_rate": 0,
                "average_response_time": 0,
                "feedback_types": {},
            }

        approved_count = sum(
            1 for req in self.completed_requests if req.status == FeedbackStatus.APPROVED
        )

        response_times = []
        feedback_types = {}

        for req in self.completed_requests:
            if req.responded_at and req.created_at:
                response_time = (req.responded_at - req.created_at).total_seconds()
                response_times.append(response_time)

            feedback_type = req.feedback_type.value
            feedback_types[feedback_type] = feedback_types.get(feedback_type, 0) + 1

        return {
            "total_requests": total_requests,
            "pending_requests": len(self.pending_requests),
            "approval_rate": approved_count / total_requests * 100,
            "average_response_time": sum(response_times) / len(response_times)
            if response_times
            else 0,
            "feedback_types": feedback_types,
        }

    def register_feedback_handler(self, feedback_type: FeedbackType, handler: Callable):
        """註冊自定義反饋處理器"""
        self.feedback_handlers[feedback_type] = handler
        logger.info(f"註冊反饋處理器: {feedback_type.value}")

    async def cleanup(self):
        """清理資源"""
        # 取消所有待處理請求
        for request in self.pending_requests.values():
            request.status = FeedbackStatus.CANCELLED

        self.pending_requests.clear()
        logger.info("人機互動反饋管理器已清理")


# 便利函數
async def request_plan_approval(
    feedback_manager: HumanFeedbackManager, plan_data: Dict[str, Any], timeout_seconds: int = 300
) -> bool:
    """請求計劃批准"""
    response = await feedback_manager.request_feedback(
        FeedbackType.PLAN_REVIEW,
        "計劃審查",
        "請審查並批准此執行計劃",
        {"plan": plan_data},
        timeout_seconds=timeout_seconds,
    )

    return response.response_type == "approve"


async def request_step_confirmation(
    feedback_manager: HumanFeedbackManager, step_data: Dict[str, Any], timeout_seconds: int = 60
) -> bool:
    """請求步驟確認"""
    response = await feedback_manager.request_feedback(
        FeedbackType.STEP_CONFIRMATION,
        "步驟確認",
        "確認執行此步驟",
        {"step": step_data},
        timeout_seconds=timeout_seconds,
    )

    return response.response_type == "approve"


async def request_error_handling(
    feedback_manager: HumanFeedbackManager, error_info: Dict[str, Any], timeout_seconds: int = 120
) -> str:
    """請求錯誤處理決定"""
    response = await feedback_manager.request_feedback(
        FeedbackType.ERROR_HANDLING,
        "錯誤處理",
        "處理執行錯誤",
        {"error": error_info},
        timeout_seconds=timeout_seconds,
    )

    return response.data.get("action", "stop")


class HumanFeedbackHandler:
    """
    人機互動處理器（相容性類別）

    提供與遷移計劃中提到的 HumanFeedbackHandler 相容的接口。
    """

    def __init__(self, auto_accepted: bool = True):
        """
        初始化人機互動處理器

        Args:
            auto_accepted: 是否自動接受計劃
        """
        self.auto_accepted = auto_accepted
        self.feedback_manager = HumanFeedbackManager()

        logger.info(f"人機互動處理器初始化完成 (auto_accepted: {auto_accepted})")

    async def review_plan(self, plan: str) -> str:
        """
        審查計劃

        Args:
            plan: 計劃字串

        Returns:
            str: 審查結果
        """
        if self.auto_accepted:
            logger.info("自動接受計劃")
            return "[ACCEPTED]"

        # 解析計劃
        plan_dict = {
            "name": "研究計劃",
            "description": plan,
            "content": plan,
        }

        # 執行審查
        response = await self.feedback_manager.request_feedback(
            FeedbackType.PLAN_REVIEW,
            "計劃審查",
            "請審查以下研究計劃",
            {"plan": plan_dict},
        )

        if response.response_type == "approve":
            return "[ACCEPTED]"
        elif response.response_type == "modify":
            modifications = response.data.get("modifications", {})
            return f"[MODIFIED] {response.comment}\n修改建議: {modifications}"
        else:
            return f"[REJECTED] {response.comment}"

    async def get_human_input(self, prompt: str) -> str:
        """
        獲取人工輸入

        Args:
            prompt: 提示訊息

        Returns:
            str: 用戶輸入
        """
        if self.auto_accepted:
            return "[AUTO_ACCEPTED]"

        # 創建一個通用反饋請求
        response = await self.feedback_manager.request_feedback(
            FeedbackType.EXECUTION_PAUSE,
            "用戶輸入請求",
            prompt,
            {"prompt": prompt},
        )

        return response.comment or "[NO_INPUT]"

    def set_auto_accept(self, auto_accept: bool):
        """設置自動接受模式"""
        self.auto_accepted = auto_accept
        logger.info(f"設置自動接受模式: {auto_accept}")

    async def cleanup(self):
        """清理資源"""
        await self.feedback_manager.cleanup()
