# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Thread-specific 日誌系統

為每個 thread_id 提供獨立的日誌檔案和 logger 實例，
確保多使用者環境下日誌不會混淆和誤植。
"""

import logging as std_logging
import threading
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
from contextlib import contextmanager

from .file_manager import LogFileManager
from .formatters import get_thread_formatter


class ThreadLogger:
    """Thread-specific 日誌器"""

    def __init__(self, thread_id: str, log_dir: str = "logs"):
        self.thread_id = thread_id
        self.log_dir = Path(log_dir)
        self.file_manager = LogFileManager(log_dir)
        self._logger: Optional[std_logging.Logger] = None
        self._handler: Optional[std_logging.FileHandler] = None
        self._lock = threading.Lock()

    @property
    def logger(self) -> std_logging.Logger:
        """獲取 logger 實例（延遲初始化）"""
        if self._logger is None:
            with self._lock:
                if self._logger is None:
                    self._initialize_logger()
        return self._logger

    def _initialize_logger(self):
        """初始化 logger"""
        # 創建 logger
        logger_name = f"deerflow.{self.thread_id}"
        self._logger = std_logging.getLogger(logger_name)
        self._logger.setLevel(std_logging.INFO)

        # 防止重複添加 handler
        if self._logger.handlers:
            return

        # 獲取日誌檔案路徑
        log_file = self.file_manager.get_log_file_path(self.thread_id)

        # 創建 file handler
        self._handler = std_logging.FileHandler(log_file, encoding="utf-8")
        self._handler.setLevel(std_logging.INFO)

        # 設定格式化器
        formatter = get_thread_formatter(self.thread_id)
        self._handler.setFormatter(formatter)

        # 添加 handler
        self._logger.addHandler(self._handler)
        self._logger.propagate = False  # 防止傳播到根 logger

    def cleanup(self):
        """清理資源"""
        if self._handler:
            self._handler.close()
            if self._logger:
                self._logger.removeHandler(self._handler)
        self._handler = None
        self._logger = None


class ThreadLoggerManager:
    """Thread Logger 管理器"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self._loggers: Dict[str, ThreadLogger] = {}
        self._lock = threading.Lock()
        self._local = threading.local()

    def get_logger(self, thread_id: str) -> std_logging.Logger:
        """
        獲取指定 thread_id 的 logger

        Args:
            thread_id: 執行緒 ID

        Returns:
            logging.Logger: Thread-specific logger
        """
        if thread_id not in self._loggers:
            with self._lock:
                if thread_id not in self._loggers:
                    self._loggers[thread_id] = ThreadLogger(thread_id, self.log_dir)

        return self._loggers[thread_id].logger

    def set_current_thread_id(self, thread_id: str):
        """設定當前執行緒的 thread_id"""
        self._local.thread_id = thread_id

    def get_current_thread_id(self) -> Optional[str]:
        """獲取當前執行緒的 thread_id"""
        return getattr(self._local, "thread_id", None)

    def get_current_logger(self) -> std_logging.Logger:
        """獲取當前執行緒的 logger"""
        thread_id = self.get_current_thread_id()
        if thread_id is None:
            raise RuntimeError(
                "No thread_id set for current thread. Call set_thread_context() first."
            )
        return self.get_logger(thread_id)

    def cleanup_thread(self, thread_id: str):
        """清理指定 thread 的資源"""
        if thread_id in self._loggers:
            with self._lock:
                if thread_id in self._loggers:
                    self._loggers[thread_id].cleanup()
                    del self._loggers[thread_id]

    def cleanup_all(self):
        """清理所有資源"""
        with self._lock:
            for logger in self._loggers.values():
                logger.cleanup()
            self._loggers.clear()


# 全域管理器實例
_manager = ThreadLoggerManager()


def init_thread_logging(log_dir: str = "logs") -> None:
    """
    初始化 thread 日誌系統

    Args:
        log_dir: 日誌目錄
    """
    global _manager
    _manager = ThreadLoggerManager(log_dir)


def set_thread_context(thread_id: str) -> None:
    """
    設定當前執行緒的 thread_id 上下文

    Args:
        thread_id: 執行緒 ID
    """
    _manager.set_current_thread_id(thread_id)


def get_thread_context() -> Optional[str]:
    """
    獲取當前執行緒的 thread_id 上下文

    Returns:
        Optional[str]: 當前 thread_id，如果未設定則返回 None
    """
    return _manager.get_current_thread_id()


def clear_thread_context() -> None:
    """清除當前執行緒的 thread_id 上下文"""
    _manager._local.thread_id = None


def get_thread_logger(thread_id: Optional[str] = None) -> std_logging.Logger:
    """
    獲取 thread-specific logger

    Args:
        thread_id: 執行緒 ID，如果為 None 則使用當前執行緒的上下文

    Returns:
        logging.Logger: Thread-specific logger
    """
    if thread_id is None:
        return _manager.get_current_logger()
    else:
        return _manager.get_logger(thread_id)


def cleanup_thread_logging(thread_id: Optional[str] = None) -> None:
    """
    清理 thread 日誌資源

    Args:
        thread_id: 執行緒 ID，如果為 None 則清理所有
    """
    if thread_id is None:
        _manager.cleanup_all()
    else:
        _manager.cleanup_thread(thread_id)


@contextmanager
def thread_logging_context(thread_id: str):
    """
    Thread 日誌上下文管理器

    Args:
        thread_id: 執行緒 ID
    """
    old_thread_id = get_thread_context()
    try:
        set_thread_context(thread_id)
        yield get_thread_logger()
    finally:
        if old_thread_id is not None:
            set_thread_context(old_thread_id)
        else:
            clear_thread_context()
