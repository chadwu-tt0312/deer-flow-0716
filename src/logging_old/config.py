# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from urllib.parse import urlparse
from typing import Dict, Any


class LoggingConfig:
    """DeerFlow 日誌配置類別"""

    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get("provider", "file")
        self.level = config.get("level", "INFO")
        self.file_settings = config.get("file_settings", {})

    def is_file_provider(self) -> bool:
        """檢查是否為檔案提供者"""
        return self.provider == "file"

    def is_database_provider(self) -> bool:
        """檢查是否為資料庫提供者"""
        return self.provider.startswith(("sqlite://", "postgresql://"))

    def get_database_config(self) -> Dict[str, Any]:
        """解析資料庫連接配置"""
        if not self.is_database_provider():
            raise ValueError("Not a database provider")

        parsed = urlparse(self.provider)

        if parsed.scheme == "sqlite":
            return {"type": "sqlite", "path": parsed.path.lstrip("/")}
        elif parsed.scheme == "postgresql":
            return {
                "type": "postgresql",
                "host": parsed.hostname,
                "port": parsed.port or 5432,
                "database": parsed.path.lstrip("/"),
                "username": parsed.username,
                "password": parsed.password,
            }
        else:
            raise ValueError(f"Unsupported database scheme: {parsed.scheme}")
