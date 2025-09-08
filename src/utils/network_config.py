# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
import json
from typing import Dict, Optional, Any
from urllib.parse import urlparse
from datetime import datetime

from src.deerflow_logging import get_logger

logger = get_logger(__name__)


class NetworkConfig:
    """網路配置工具類別，處理代理伺服器和 User-Agent 設定"""

    def __init__(self):
        self._proxies = None
        self._headers = None
        self._is_ssl_required = False
        self._connection_logging_enabled = (
            os.getenv("ENABLE_CONNECTION_LOGGING", "false").lower() == "true"
        )
        self._connection_log_file = os.getenv("CONNECTION_LOG_FILE", "logs/connection.log")

    def _should_use_proxy_and_headers(self, url: str) -> bool:
        """判斷是否需要使用代理伺服器和自訂 headers"""
        try:
            parsed_url = urlparse(url)
            # 檢查是否為 HTTPS 或特定的內部網路端點
            is_https = parsed_url.scheme.lower() == "https"

            # 檢查是否為 Azure OpenAI 端點或 BASIC_MODEL__BASE_URL
            azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            basic_model_base_url = os.getenv("BASIC_MODEL__BASE_URL", "")

            # 只有 HTTPS URL 或匹配特定的端點才需要代理和 headers
            if is_https:
                return True
            elif azure_openai_endpoint and url.startswith(azure_openai_endpoint):
                return True
            elif basic_model_base_url and url.startswith(basic_model_base_url):
                return True

            return False
        except Exception as e:
            logger.warning(f"解析 URL 失敗: {e}")
            return False

    def _get_proxies(self) -> Optional[Dict[str, str]]:
        """取得代理伺服器設定"""
        if self._proxies is not None:
            return self._proxies

        http_proxy = os.getenv("HTTP_PROXY")
        https_proxy = os.getenv("HTTPS_PROXY")

        if not http_proxy and not https_proxy:
            self._proxies = None
            return None

        self._proxies = {}
        if http_proxy:
            self._proxies["http"] = http_proxy
        if https_proxy:
            self._proxies["https"] = https_proxy

        logger.info(f"設定代理伺服器: {self._proxies}")
        return self._proxies

    def _get_headers(self) -> Optional[Dict[str, str]]:
        """取得自訂 headers"""
        if self._headers is not None:
            return self._headers

        user_agent = os.getenv("USER_AGENT")
        if not user_agent:
            # 預設的 User-Agent
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/135.0.3179.54"

        self._headers = {"User-Agent": user_agent}

        # 添加 USER_ID 到 headers
        user_id = os.getenv("USER_ID")
        if user_id:
            self._headers["X-User-ID"] = user_id
            logger.info(f"設定 User-ID: {user_id}")

        logger.info(f"設定 User-Agent: {user_agent}")
        return self._headers

    def get_request_config(self, url: str) -> Dict[str, any]:
        """取得請求配置，包含代理伺服器和 headers"""
        config = {}

        if self._should_use_proxy_and_headers(url):
            proxies = self._get_proxies()
            headers = self._get_headers()

            if proxies:
                config["proxies"] = proxies
            if headers:
                config["headers"] = headers

            logger.debug(f"為 URL {url} 套用網路配置: {config}")

        return config

    def update_headers(self, existing_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """更新現有的 headers，加入 User-Agent"""
        if not self._should_use_proxy_and_headers("https://example.com"):  # 檢查是否需要 headers
            return existing_headers or {}

        custom_headers = self._get_headers()
        if existing_headers:
            # 合併現有 headers 和自訂 headers
            merged_headers = existing_headers.copy()
            merged_headers.update(custom_headers)
            return merged_headers
        else:
            return custom_headers

    def get_proxies_for_url(self, url: str) -> Optional[Dict[str, str]]:
        """為特定 URL 取得代理伺服器設定"""
        if self._should_use_proxy_and_headers(url):
            return self._get_proxies()
        return None

    def log_connection_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Any] = None,
        proxies: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """記錄連線請求的詳細資訊"""
        if not self._connection_logging_enabled:
            return

        try:
            # 準備連線紀錄
            connection_log = {
                "timestamp": datetime.now().isoformat(),
                "method": method.upper(),
                "url": url,
                "headers": self._sanitize_headers(headers or {}),
                "proxies": self._sanitize_proxies(proxies or {}),
                "timeout": timeout,
                "data_size": len(str(data)) if data else 0,
                "data_preview": str(data)[:200] + "..."
                if data and len(str(data)) > 200
                else str(data)
                if data
                else None,
            }

            # 確保日誌目錄存在
            log_dir = os.path.dirname(self._connection_log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # 寫入連線紀錄
            with open(self._connection_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(connection_log, ensure_ascii=False, indent=2) + "\n")

            logger.debug(f"連線紀錄已寫入: {self._connection_log_file}")

        except Exception as e:
            logger.warning(f"寫入連線紀錄失敗: {e}")

    def log_connection_response(
        self,
        url: str,
        status_code: int,
        response_headers: Optional[Dict[str, str]] = None,
        response_size: Optional[int] = None,
        response_time: Optional[float] = None,
    ) -> None:
        """記錄連線回應的詳細資訊"""
        if not self._connection_logging_enabled:
            return

        try:
            # 準備回應紀錄
            response_log = {
                "timestamp": datetime.now().isoformat(),
                "url": url,
                "status_code": status_code,
                "response_headers": self._sanitize_headers(response_headers or {}),
                "response_size": response_size,
                "response_time_ms": round(response_time * 1000, 2) if response_time else None,
            }

            # 確保日誌目錄存在
            log_dir = os.path.dirname(self._connection_log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # 寫入回應紀錄
            with open(self._connection_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(response_log, ensure_ascii=False, indent=2) + "\n")

            logger.debug(f"回應紀錄已寫入: {self._connection_log_file}")

        except Exception as e:
            logger.warning(f"寫入回應紀錄失敗: {e}")

    def log_connection_error(self, url: str, error: Exception, method: str = "UNKNOWN") -> None:
        """記錄連線錯誤的詳細資訊"""
        if not self._connection_logging_enabled:
            return

        try:
            # 準備錯誤紀錄
            error_log = {
                "timestamp": datetime.now().isoformat(),
                "method": method.upper(),
                "url": url,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_details": {"args": error.args, "str": str(error)},
            }

            # 確保日誌目錄存在
            log_dir = os.path.dirname(self._connection_log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # 寫入錯誤紀錄
            with open(self._connection_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_log, ensure_ascii=False, indent=2) + "\n")

            logger.debug(f"錯誤紀錄已寫入: {self._connection_log_file}")

        except Exception as e:
            logger.warning(f"寫入錯誤紀錄失敗: {e}")

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """清理 headers，移除敏感資訊"""
        sanitized = {}
        sensitive_keys = ["authorization", "api-key", "x-api-key", "cookie", "set-cookie"]

        for key, value in headers.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_proxies(self, proxies: Dict[str, str]) -> Dict[str, str]:
        """清理代理設定，移除認證資訊"""
        sanitized = {}

        for protocol, proxy_url in proxies.items():
            if "@" in proxy_url:
                # 移除認證資訊
                parts = proxy_url.split("@")
                if len(parts) == 2:
                    sanitized[protocol] = f"***REDACTED***@{parts[1]}"
                else:
                    sanitized[protocol] = "***REDACTED***"
            else:
                sanitized[protocol] = proxy_url

        return sanitized

    def enable_connection_logging(
        self, enabled: bool = True, log_file: Optional[str] = None
    ) -> None:
        """啟用或停用連線紀錄"""
        self._connection_logging_enabled = enabled
        if log_file:
            self._connection_log_file = log_file

        status = "啟用" if enabled else "停用"
        logger.info(f"連線紀錄已{status}，日誌檔案: {self._connection_log_file}")

    def is_connection_logging_enabled(self) -> bool:
        """檢查連線紀錄是否已啟用"""
        return self._connection_logging_enabled

    def get_connection_log_file(self) -> str:
        """取得連線紀錄檔案路徑"""
        return self._connection_log_file


# 全域網路配置實例
network_config = NetworkConfig()
