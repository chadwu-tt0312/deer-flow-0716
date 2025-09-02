# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import contextvars
from typing import Optional

# 執行緒上下文變數
thread_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "thread_context", default=None
)


def set_thread_context(thread_id: str):
    """設定執行緒上下文"""
    thread_context.set(thread_id)


def get_thread_context() -> Optional[str]:
    """取得執行緒上下文"""
    value = thread_context.get()
    # 如果沒有設定或為 None，返回 "default"
    if value is None:
        return "default"
    return value


def clear_thread_context():
    """清除執行緒上下文"""
    thread_context.set(None)


# 為了向後相容，我們保留原有的函數名稱
# 但內部實作會使用新的 Thread-specific 日誌系統
def set_thread_context_legacy(thread_id: str):
    """設定執行緒上下文（向後相容版本）"""
    from .logging_config import setup_thread_logging, set_current_thread_context

    # 創建或獲取 thread-specific logger
    thread_logger = setup_thread_logging(thread_id)

    # 設置當前 thread context
    set_current_thread_context(thread_id, thread_logger)

    # 同時設置舊的 context（向後相容）
    thread_context.set(thread_id)


def get_thread_context_legacy() -> Optional[str]:
    """取得執行緒上下文（向後相容版本）"""
    from .logging_config import get_current_thread_id

    # 優先使用新的 context
    new_context = get_current_thread_id()
    if new_context:
        return new_context

    # 備用方案：使用舊的 context
    return get_thread_context()


def clear_thread_context_legacy():
    """清除執行緒上下文（向後相容版本）"""
    from .logging_config import clear_current_thread_context

    # 清除新的 context
    clear_current_thread_context()

    # 清除舊的 context
    clear_thread_context()
