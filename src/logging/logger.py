# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import logging.handlers
from typing import Optional
from .context import get_thread_context

# 移除不需要的 import，讓 DeerFlowLogger 更簡潔
# from .config import LoggingConfig
# from ..config import load_yaml_config
from .logging_config import (
    setup_deerflow_logging,
    setup_thread_logging,
    get_current_thread_logger,
    get_current_thread_id,
)


class DeerFlowLogger:
    """DeerFlow 專用的 Logger 類別"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        # 不再設定 handlers，完全依賴主日誌系統

    def info(self, message: str, **kwargs):
        """記錄 INFO 級別日誌"""
        self._log(logging.INFO, message, **kwargs)

    def debug(self, message: str, **kwargs):
        """記錄 DEBUG 級別日誌"""
        self._log(logging.DEBUG, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """記錄 WARNING 級別日誌"""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """記錄 ERROR 級別日誌"""
        self._log(logging.ERROR, message, **kwargs)

    def _log(self, level: int, message: str, **kwargs):
        """內部日誌記錄方法"""
        # 直接使用主日誌系統，避免重複記錄
        # 不再嘗試使用 Thread-specific logger，讓主日誌系統統一處理

        # 備用方案：使用舊的系統
        thread_id = get_thread_context()
        node = kwargs.get("node", "system")

        # 建立額外資訊
        extra = {"thread_id": thread_id, "node": node, "extra_data": kwargs.get("extra_data", {})}

        # 記錄日誌到主日誌系統
        self.logger.log(level, message, extra=extra)


# 全域 logger 實例字典
_logger_instances = {}


def get_logger(name: str) -> DeerFlowLogger:
    """取得 DeerFlow Logger 實例"""
    global _logger_instances
    if name not in _logger_instances:
        _logger_instances[name] = DeerFlowLogger(name)
    return _logger_instances[name]


def init_logging():
    """初始化 logging 系統"""
    # 使用新的 Thread-specific 日誌系統
    try:
        setup_deerflow_logging(debug=False, log_to_file=True, log_dir="logs")
        print("✅ Thread-specific 日誌系統已初始化")
    except Exception as e:
        print(f"⚠️ 無法初始化 Thread-specific 日誌系統: {e}")
        # 備用方案：使用傳統的日誌系統
        logging.getLogger().setLevel(logging.INFO)
        print("✅ 傳統日誌系統已初始化")


def init_thread_logging(thread_id: str, debug: bool = False) -> logging.Logger:
    """初始化特定 Thread 的日誌系統"""
    try:
        thread_logger = setup_thread_logging(
            thread_id=thread_id,
            level="DEBUG" if debug else "INFO",
            log_dir="logs",
            console_output=True,
            file_output=True,
        )
        print(f"✅ Thread {thread_id[:8]} 的日誌系統已初始化")
        return thread_logger
    except Exception as e:
        print(f"⚠️ 無法初始化 Thread {thread_id[:8]} 的日誌系統: {e}")
        # 備用方案：返回預設 logger
        return logging.getLogger(f"thread_{thread_id}")
