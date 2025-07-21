# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import json
from datetime import datetime


class DeerFlowFormatter(logging.Formatter):
    """DeerFlow 專用的日誌格式化器"""

    def format(self, record):
        """格式化日誌記錄"""
        # 基本格式
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level = record.levelname
        message = record.getMessage()

        # 取得額外資訊
        node = getattr(record, "node", "system")
        extra_data = getattr(record, "extra_data", {})

        # 格式化輸出（移除 thread_id，因為檔名已經包含）
        formatted = f"{timestamp} [{level}] [node:{node}] {message}"

        # 如果有額外資料，添加 JSON 格式
        if extra_data:
            formatted += f" | {json.dumps(extra_data, ensure_ascii=False)}"

        return formatted
