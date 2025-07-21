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
