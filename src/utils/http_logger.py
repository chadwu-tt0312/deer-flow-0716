# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class HttpLogger:
    """完整的 HTTP 請求/回應記錄器"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.enabled = True

    def log_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Any] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: Optional[float] = None,
        thread_id: Optional[str] = None,
    ) -> str:
        """記錄 HTTP 請求"""
        if not self.enabled:
            return ""

        try:
            # 生成請求 ID
            request_id = f"req_{int(time.time() * 1000)}_{hash(url) % 10000}"

            # 準備請求記錄
            request_log = {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "type": "request",
                "method": method.upper(),
                "url": url,
                "headers": self._sanitize_headers(headers or {}),
                "params": self._ensure_serializable(params),
                "data": self._ensure_serializable(self._sanitize_data(data)),
                "json_data": self._ensure_serializable(self._sanitize_data(json_data)),
                "timeout": timeout,
                "thread_id": thread_id,
            }

            # 寫入請求記錄
            log_file = self._get_log_file(thread_id)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(request_log, ensure_ascii=False, indent=2) + "\n")

            return request_id

        except Exception as e:
            logger.warning(f"記錄 HTTP 請求失敗: {e}")
            return ""

    def log_response(
        self,
        request_id: str,
        url: str,
        status_code: int,
        headers: Optional[Dict[str, str]] = None,
        content: Optional[Union[str, bytes]] = None,
        response_time: Optional[float] = None,
        thread_id: Optional[str] = None,
    ) -> None:
        """記錄 HTTP 回應"""
        if not self.enabled:
            return

        try:
            # 準備回應記錄
            response_log = {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "type": "response",
                "url": url,
                "status_code": status_code,
                "headers": self._sanitize_headers(headers or {}),
                "content_preview": self._get_content_preview(content),
                "content_size": len(content) if content else 0,
                "response_time_ms": round(response_time * 1000, 2) if response_time else None,
                "thread_id": thread_id,
            }

            # 寫入回應記錄
            log_file = self._get_log_file(thread_id)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(response_log, ensure_ascii=False, indent=2) + "\n")

        except Exception as e:
            logger.warning(f"記錄 HTTP 回應失敗: {e}")

    def log_error(
        self,
        request_id: str,
        url: str,
        error: Exception,
        method: str = "UNKNOWN",
        thread_id: Optional[str] = None,
    ) -> None:
        """記錄 HTTP 錯誤"""
        if not self.enabled:
            return

        try:
            # 準備錯誤記錄
            error_log = {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "type": "error",
                "method": method.upper(),
                "url": url,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_details": {
                    "args": list(error.args),
                    "str": str(error),
                },
                "thread_id": thread_id,
            }

            # 寫入錯誤記錄
            log_file = self._get_log_file(thread_id)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_log, ensure_ascii=False, indent=2) + "\n")

        except Exception as e:
            logger.warning(f"記錄 HTTP 錯誤失敗: {e}")

    def _get_log_file(self, thread_id: Optional[str] = None) -> Path:
        """取得日誌檔案路徑"""
        date_str = datetime.now().strftime("%Y%m%d")

        if thread_id and thread_id != "unknown" and thread_id != "default":
            # 只取前8碼來縮短檔名
            short_thread_id = thread_id[:8]
            return self.log_dir / f"{date_str}-{short_thread_id}-http.log"
        else:
            return self.log_dir / f"{date_str}-default-http.log"

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """清理 headers，移除敏感資訊"""
        sensitive_keys = {
            "authorization",
            "cookie",
            "x-api-key",
            "api-key",
            "token",
            "password",
            "secret",
            "key",
            "auth",
        }

        sanitized = {}
        for key, value in headers.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_data(self, data: Any) -> Any:
        """清理資料，移除敏感資訊"""
        if isinstance(data, dict):
            sensitive_keys = {
                "password",
                "secret",
                "key",
                "token",
                "api_key",
                "api-key",
                "authorization",
                "auth",
                "credential",
            }

            sanitized = {}
            for key, value in data.items():
                if isinstance(key, str) and key.lower() in sensitive_keys:
                    sanitized[key] = "***REDACTED***"
                else:
                    sanitized[key] = value

            return sanitized
        elif isinstance(data, str):
            # 檢查是否包含敏感資訊
            sensitive_patterns = [
                "password",
                "secret",
                "key",
                "token",
                "api_key",
                "authorization",
                "auth",
                "credential",
            ]

            for pattern in sensitive_patterns:
                if pattern.lower() in data.lower():
                    return "***REDACTED***"

            return data
        elif isinstance(data, bytes):
            # 處理 bytes 資料
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return f"[Binary data, size: {len(data)} bytes]"
        else:
            return str(data) if data is not None else None

    def _ensure_serializable(self, data: Any) -> Any:
        """確保資料可以被 JSON 序列化"""
        if data is None:
            return None
        elif isinstance(data, (str, int, float, bool)):
            return data
        elif isinstance(data, bytes):
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return f"[Binary data, size: {len(data)} bytes]"
        elif isinstance(data, dict):
            return {str(k): self._ensure_serializable(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._ensure_serializable(item) for item in data]
        else:
            return str(data)

    def _get_content_preview(self, content: Optional[Union[str, bytes]]) -> Optional[str]:
        """取得內容預覽"""
        if not content:
            return None

        if isinstance(content, bytes):
            try:
                content = content.decode("utf-8")
            except UnicodeDecodeError:
                return f"[Binary data, size: {len(content)} bytes]"

        if isinstance(content, str):
            # 限制預覽長度
            max_preview = 500
            if len(content) > max_preview:
                return content[:max_preview] + "..."
            return content

        return str(content)

    def enable(self, enabled: bool = True) -> None:
        """啟用或停用記錄"""
        self.enabled = enabled
        status = "啟用" if enabled else "停用"
        logger.info(f"HTTP 記錄已{status}")


# 全域 HTTP 記錄器實例
http_logger = HttpLogger()
