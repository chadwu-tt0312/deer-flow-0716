# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 系統人機互動模組

提供用戶反饋、互動控制和介面管理功能。
"""

from .human_feedback_manager import (
    HumanFeedbackManager,
    FeedbackType,
    FeedbackStatus,
    FeedbackRequest,
    FeedbackResponse,
    request_plan_approval,
    request_step_confirmation,
    request_error_handling,
)

from .user_interface import (
    InteractiveUserInterface,
    ControlAction,
    UserCommand,
    create_interactive_session,
    display_welcome_message,
)

from .interactive_workflow_manager import (
    InteractiveWorkflowManager,
    run_interactive_research,
    run_non_interactive_research,
)

__all__ = [
    # 反饋管理
    "HumanFeedbackManager",
    "FeedbackType",
    "FeedbackStatus",
    "FeedbackRequest",
    "FeedbackResponse",
    "request_plan_approval",
    "request_step_confirmation",
    "request_error_handling",
    # 用戶介面
    "InteractiveUserInterface",
    "ControlAction",
    "UserCommand",
    "create_interactive_session",
    "display_welcome_message",
    # 互動式工作流
    "InteractiveWorkflowManager",
    "run_interactive_research",
    "run_non_interactive_research",
]
