# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
日誌檔案管理器

負責管理日誌檔案的創建、路徑生成和安全性檢查。
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading


class LogFileManager:
    """日誌檔案管理器"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self._lock = threading.Lock()

        # Thread ID 驗證正則表達式（只允許字母、數字、連字符、底線）
        self._thread_id_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")

    def _validate_thread_id(self, thread_id: str) -> bool:
        """
        驗證 thread_id 的安全性

        Args:
            thread_id: 執行緒 ID

        Returns:
            bool: 是否有效
        """
        if not thread_id or len(thread_id) > 100:
            return False

        return bool(self._thread_id_pattern.match(thread_id))

    def _ensure_log_dir(self):
        """確保日誌目錄存在"""
        with self._lock:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def get_log_file_path(self, thread_id: str) -> Path:
        """
        獲取指定 thread_id 的日誌檔案路徑

        Args:
            thread_id: 執行緒 ID

        Returns:
            Path: 日誌檔案路徑

        Raises:
            ValueError: 如果 thread_id 無效
        """
        if not self._validate_thread_id(thread_id):
            raise ValueError(f"Invalid thread_id: {thread_id}")

        # 確保日誌目錄存在
        self._ensure_log_dir()

        # 生成檔案名：YYMMDD-{thread_id}.log
        date_str = datetime.now().strftime("%y%m%d")
        filename = f"{date_str}-{thread_id}.log"

        return self.log_dir / filename

    def get_all_log_files(self, thread_id: Optional[str] = None) -> list[Path]:
        """
        獲取所有日誌檔案

        Args:
            thread_id: 如果指定，只返回該 thread_id 的檔案

        Returns:
            list[Path]: 日誌檔案列表
        """
        if not self.log_dir.exists():
            return []

        if thread_id:
            if not self._validate_thread_id(thread_id):
                return []
            pattern = f"*-{thread_id}.log"
        else:
            pattern = "*.log"

        return list(self.log_dir.glob(pattern))

    def cleanup_old_logs(self, days: int = 30):
        """
        清理舊日誌檔案

        Args:
            days: 保留天數
        """
        if not self.log_dir.exists():
            return

        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)

        for log_file in self.log_dir.glob("*.log"):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
            except OSError:
                # 檔案可能正在使用或已被刪除
                pass

    def get_file_size(self, thread_id: str) -> int:
        """
        獲取指定 thread_id 的日誌檔案大小

        Args:
            thread_id: 執行緒 ID

        Returns:
            int: 檔案大小（位元組），如果檔案不存在則返回 0
        """
        try:
            log_file = self.get_log_file_path(thread_id)
            if log_file.exists():
                return log_file.stat().st_size
        except (ValueError, OSError):
            pass

        return 0
