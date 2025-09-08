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
# 移除 simple_logger 導入，統一使用 thread_logger

__version__ = "1.0.0"

__all__ = [
    # Thread-specific 日誌 API
    "get_thread_logger",
    "init_thread_logging",
    "set_thread_context",
    "get_thread_context",
    "clear_thread_context",
    "cleanup_thread_logging",
]


# 向後兼容的別名 - 統一使用 thread_logger
def get_logger(name: str = None):
    """向後兼容的 get_logger 函數，統一使用 thread_logger"""
    if name is None:
        return get_thread_logger()
    else:
        # 為向後兼容，創建一個簡單的 logger，但使用 deerflow_logging 系統
        try:
            # 嘗試使用 thread logger
            return get_thread_logger()
        except RuntimeError:
            # 如果 thread context 未設定，創建一個基本的 logger
            import logging as std_logging

            logger = std_logging.getLogger(name)
            if not logger.handlers:
                handler = std_logging.StreamHandler()
                formatter = std_logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
                handler.setFormatter(formatter)
                logger.addHandler(handler)
                logger.setLevel(std_logging.INFO)
                logger.propagate = False
            return logger


def init_logging():
    """向後兼容的 init_logging 函數，統一使用 thread_logger"""
    init_thread_logging()
