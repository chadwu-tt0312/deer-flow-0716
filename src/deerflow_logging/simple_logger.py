# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
簡化日誌實現

用於測試環境和不需要 thread 隔離的場景。
"""

import logging as std_logging
import sys
from typing import Optional

_initialized = False


def init_simple_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    初始化簡化日誌系統

    Args:
        level: 日誌級別 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 可選的日誌檔案路徑，如果提供則同時輸出到檔案和控制台
    """
    global _initialized

    if _initialized:
        return

    # 獲取根日誌器
    root_logger = std_logging.getLogger()
    root_logger.setLevel(getattr(std_logging, level.upper()))

    # 清除現有處理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 設定格式器
    formatter = std_logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # 添加控制台處理器
    console_handler = std_logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 如果指定了日誌檔案，添加檔案處理器
    if log_file:
        import os

        # 確保日誌目錄存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        file_handler = std_logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _initialized = True


def get_simple_logger(name: str) -> std_logging.Logger:
    """
    獲取簡化日誌器

    Args:
        name: 日誌器名稱

    Returns:
        logging.Logger: 日誌器實例
    """
    # 確保日誌系統已初始化
    if not _initialized:
        init_simple_logging()

    logger = std_logging.getLogger(name)

    # 避免重複添加 handler
    if not logger.handlers:
        handler = std_logging.StreamHandler(sys.stdout)
        formatter = std_logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(std_logging.INFO)
        logger.propagate = False  # 防止重複日誌

    return logger
