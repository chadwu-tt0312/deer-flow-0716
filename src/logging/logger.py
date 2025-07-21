# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import logging.handlers
from typing import Optional
from .context import get_thread_context
from .handlers.file_handler import DeerFlowFileHandler
from .handlers.db_handler import DeerFlowDBHandler
from .formatters import DeerFlowFormatter
from .config import LoggingConfig
from ..config import load_yaml_config


class DeerFlowLogger:
    """DeerFlow 專用的 Logger 類別"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_handlers()

    def _get_logging_config(self) -> LoggingConfig:
        """取得日誌配置"""
        try:
            config = load_yaml_config("conf.yaml")
            logging_config = config.get("LOGGING", {})
            return LoggingConfig(logging_config)
        except Exception as e:
            print(f"Failed to load logging config: {e}, using defaults")
            return LoggingConfig({})

    def _setup_handlers(self):
        """設定 handlers"""
        # 清除現有的 handlers
        self.logger.handlers.clear()

        # 設定格式器
        formatter = DeerFlowFormatter()

        # Console Handler (永遠存在)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 根據配置添加檔案或資料庫 handler
        config = self._get_logging_config()

        if config.is_file_provider():
            file_handler = DeerFlowFileHandler(config)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        elif config.is_database_provider():
            db_handler = DeerFlowDBHandler(config)
            db_handler.setFormatter(formatter)
            self.logger.addHandler(db_handler)

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
        thread_id = get_thread_context()
        node = kwargs.get("node", "system")

        # 建立額外資訊
        extra = {"thread_id": thread_id, "node": node, "extra_data": kwargs.get("extra_data", {})}

        # 記錄日誌
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
    # 設定全域日誌級別
    logging.getLogger().setLevel(logging.INFO)
