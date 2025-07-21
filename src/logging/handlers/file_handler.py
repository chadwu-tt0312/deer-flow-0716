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

    def __init__(self, config: LoggingConfig):
        super().__init__()
        self.log_dir = Path(config.file_settings.get("log_dir", "logs"))
        self.max_days = config.file_settings.get("max_days", 10)
        self.compress_old_files = config.file_settings.get("compress_old_files", True)

        # 確保日誌目錄存在
        self.log_dir.mkdir(exist_ok=True)

        # 清理舊檔案
        self._cleanup_old_files()

    def emit(self, record):
        """發送日誌記錄到檔案"""
        try:
            # 取得檔案路徑
            # 從 record 的屬性取得 thread_id
            thread_id = getattr(record, "thread_id", "default")
            file_path = self._get_log_file_path(thread_id)

            # 寫入日誌
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(self.format(record) + "\n")

        except Exception as e:
            # 如果檔案寫入失敗，至少輸出到 console
            print(f"File logging error: {e}")

    def _get_log_file_path(self, thread_id: str) -> Path:
        """取得日誌檔案路徑"""
        date_str = datetime.now().strftime("%Y%m%d")

        # 處理 thread_id 為 None 或 "default" 的情況
        if thread_id and thread_id != "unknown" and thread_id != "default":
            # 只取前8碼來縮短檔名
            short_thread_id = thread_id[:8]
            return self.log_dir / f"{date_str}-{short_thread_id}.log"
        else:
            return self.log_dir / f"{date_str}-default.log"

    def _cleanup_old_files(self):
        """清理舊的日誌檔案"""
        cutoff_date = datetime.now() - timedelta(days=self.max_days)

        for log_file in self.log_dir.glob("*.log*"):
            try:
                # 從檔名解析日期
                date_str = log_file.stem.split("-")[0]
                file_date = datetime.strptime(date_str, "%Y%m%d")

                if file_date < cutoff_date:
                    # 壓縮舊檔案
                    if self.compress_old_files and not log_file.name.endswith(".gz"):
                        self._compress_file(log_file)
                    else:
                        # 刪除超過保留期限的檔案
                        log_file.unlink()

            except Exception as e:
                print(f"Cleanup error for {log_file}: {e}")

    def _compress_file(self, file_path: Path):
        """壓縮檔案"""
        try:
            with open(file_path, "rb") as f_in:
                with gzip.open(f"{file_path}.gz", "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            file_path.unlink()  # 刪除原檔案
        except Exception as e:
            print(f"Compression error for {file_path}: {e}")
