# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
DeerFlow 日誌系統

專為多使用者、多 thread_id 環境設計的日誌系統，確保：
1. Thread-safe 日誌記錄
2. 每個 thread_id 有獨立的日誌檔案
3. 防止日誌混淆和誤植
4. 簡潔易用的 API
"""

from .thread_logger import (
    get_thread_logger,
    init_thread_logging,
    set_thread_context,
    get_thread_context,
    clear_thread_context,
    cleanup_thread_logging,
)
from .simple_logger import get_simple_logger, init_simple_logging

__version__ = "1.0.0"

__all__ = [
    # Thread-specific 日誌 API
    "get_thread_logger",
    "init_thread_logging",
    "set_thread_context",
    "get_thread_context",
    "clear_thread_context",
    "cleanup_thread_logging",
    # 簡化日誌 API（用於測試和單執行緒環境）
    "get_simple_logger",
    "init_simple_logging",
]

# 向後兼容的別名
get_logger = get_simple_logger
init_logging = init_simple_logging
