# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from ..config import LoggingConfig


class DeerFlowFileHandler(logging.Handler):
    """DeerFlow 檔案日誌處理器"""

    def __init__(self, config: LoggingConfig = None):
        super().__init__()

        # 如果沒有傳入 config，嘗試從 conf.yaml 讀取
        if config is None:
            config = self._load_config_from_yaml()

        self.log_dir = Path(config.file_settings.get("log_dir", "logs"))
        self.max_days = config.file_settings.get("max_days", 10)
        self.compress_old_files = config.file_settings.get("compress_old_files", True)

        # 確保日誌目錄存在
        self.log_dir.mkdir(exist_ok=True)

        # 清理舊檔案
        self._cleanup_old_files()

    def _load_config_from_yaml(self) -> LoggingConfig:
        """從 conf.yaml 讀取配置"""
        try:
            from ...config import load_yaml_config

            config = load_yaml_config("conf.yaml")
            logging_config = config.get("LOGGING", {})
            return LoggingConfig(logging_config)
        except Exception as e:
            print(f"⚠️ 無法從 conf.yaml 讀取日誌配置: {e}")
            # 返回預設配置
            return LoggingConfig(
                {
                    "provider": "file",
                    "level": "INFO",
                    "file_settings": {
                        "log_dir": "logs",
                        "max_days": 10,
                        "compress_old_files": True,
                    },
                }
            )

    def emit(self, record):
        """發送日誌記錄到檔案"""
        try:
            # 取得檔案路徑
            # 優先使用新的 Thread-specific 日誌系統的 context
            thread_id = None

            # 嘗試從 record 的屬性取得 thread_id
            if hasattr(record, "thread_id"):
                thread_id = record.thread_id

            # 如果沒有，嘗試從 extra 取得
            if not thread_id and hasattr(record, "extra_data"):
                extra_data = getattr(record, "extra_data", {})
                if isinstance(extra_data, dict):
                    thread_id = extra_data.get("thread_id")

            # 如果還是沒有，使用預設值
            if not thread_id:
                thread_id = "default"

            file_path = self._get_log_file_path(thread_id)

            # 寫入日誌
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(self.format(record) + "\n")

        except Exception as e:
            # 如果檔案寫入失敗，至少輸出到 console
            print(f"File logging error: {e}")

    def _get_log_file_path(self, thread_id: str) -> Path:
        """取得日誌檔案路徑"""
        date_str = datetime.now().strftime("%y%m%d")

        # 處理 thread_id 為 None 或 "default" 的情況
        if thread_id and thread_id != "unknown" and thread_id != "default":
            # 只取前8碼來縮短檔名
            short_thread_id = thread_id[:8]
            return self.log_dir / f"{date_str}-{short_thread_id}.log"
        else:
            # 不使用 "default" 後綴，直接使用主日誌檔案
            return self.log_dir / f"{date_str}.log"

    def _cleanup_old_files(self):
        """清理舊的日誌檔案"""
        cutoff_date = datetime.now() - timedelta(days=self.max_days)

        for log_file in self.log_dir.glob("*.log*"):
            try:
                # 檢查檔案修改時間
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    # 如果啟用壓縮，先壓縮再刪除
                    if self.compress_old_files and log_file.suffix == ".log":
                        compressed_file = log_file.with_suffix(".log.gz")
                        with open(log_file, "rb") as f_in:
                            with gzip.open(compressed_file, "wb") as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        log_file.unlink()  # 刪除原始檔案
                        print(f"📦 已壓縮並刪除舊日誌檔案: {log_file.name}")
                    else:
                        log_file.unlink()  # 直接刪除
                        print(f"🗑️ 已刪除舊日誌檔案: {log_file.name}")
            except Exception as e:
                print(f"⚠️ 清理日誌檔案時發生錯誤: {e}")

    def close(self):
        """關閉處理器"""
        super().close()
