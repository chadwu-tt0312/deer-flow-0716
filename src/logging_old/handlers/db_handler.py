# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from ..config import LoggingConfig


class DeerFlowDBHandler(logging.Handler):
    """DeerFlow 資料庫日誌處理器"""

    def __init__(self, config: LoggingConfig):
        super().__init__()
        self.db_config = config.get_database_config()
        self._init_database()

    def _init_database(self):
        """初始化資料庫"""
        if self.db_config["type"] == "sqlite":
            self._init_sqlite()
        elif self.db_config["type"] == "postgresql":
            self._init_postgresql()

    def _init_sqlite(self):
        """初始化 SQLite 資料庫"""
        db_path = self.db_config["path"]

        # 確保目錄存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # 建立表格
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS application_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level VARCHAR(20) NOT NULL,
                    thread_id VARCHAR(50),
                    node VARCHAR(50),
                    message TEXT NOT NULL,
                    extra_data TEXT
                )
            """)

            # 建立索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_thread_id ON application_logs(thread_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON application_logs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_node ON application_logs(node)")

    def _init_postgresql(self):
        """初始化 PostgreSQL 資料庫"""
        # TODO: 實作 PostgreSQL 支援
        # 目前先使用 SQLite 作為替代
        print("PostgreSQL support not implemented yet, using SQLite as fallback")
        self.db_config["type"] = "sqlite"
        self.db_config["path"] = "logs/deerflow.db"
        self._init_sqlite()

    def emit(self, record):
        """發送日誌記錄到資料庫"""
        try:
            if self.db_config["type"] == "sqlite":
                self._write_to_sqlite(record)
            elif self.db_config["type"] == "postgresql":
                self._write_to_postgresql(record)

        except Exception as e:
            # 如果資料庫寫入失敗，至少輸出到 console
            print(f"Database logging error: {e}")

    def _write_to_sqlite(self, record):
        """寫入到 SQLite"""
        db_path = self.db_config["path"]

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO application_logs 
                (timestamp, level, thread_id, node, message, extra_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    datetime.fromtimestamp(record.created),
                    record.levelname,
                    getattr(record, "thread_id", None),
                    getattr(record, "node", None),
                    record.getMessage(),
                    json.dumps(getattr(record, "extra_data", {}), ensure_ascii=False),
                ),
            )

    def _write_to_postgresql(self, record):
        """寫入到 PostgreSQL"""
        # TODO: 實作 PostgreSQL 寫入
        # 目前先使用 SQLite 作為替代
        self._write_to_sqlite(record)
