# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
日誌格式化器

提供不同場景下的日誌格式化器。
"""

import logging as std_logging
from typing import Optional


class ThreadAwareFormatter(std_logging.Formatter):
    """Thread-aware 日誌格式化器"""

    def __init__(self, thread_id: str, fmt: Optional[str] = None):
        self.thread_id = thread_id

        if fmt is None:
            # 不在格式中包含 thread_id，因為檔案名已經包含了 thread_id
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        super().__init__(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: std_logging.LogRecord) -> str:
        """格式化日誌記錄"""
        # 添加 thread_id 到記錄中
        record.thread_id = self.thread_id
        return super().format(record)


def get_thread_formatter(thread_id: str) -> ThreadAwareFormatter:
    """
    獲取 thread-specific 格式化器

    Args:
        thread_id: 執行緒 ID

    Returns:
        ThreadAwareFormatter: 格式化器實例
    """
    return ThreadAwareFormatter(thread_id)


def get_simple_formatter() -> std_logging.Formatter:
    """
    獲取簡單格式化器

    Returns:
        logging.Formatter: 簡單格式化器
    """
    return std_logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )


def get_detailed_formatter(thread_id: Optional[str] = None) -> std_logging.Formatter:
    """
    獲取詳細格式化器

    Args:
        thread_id: 執行緒 ID（可選）

    Returns:
        logging.Formatter: 詳細格式化器
    """
    # 不在格式中包含 thread_id，因為檔案名已經包含了 thread_id
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"

    return std_logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
