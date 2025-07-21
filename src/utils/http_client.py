# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import time
import requests
from typing import Dict, Any, Optional, Union
from .network_config import network_config
from .http_logger import http_logger
from ..logging.context import get_thread_context


class HttpClient:
    """HTTP 客戶端包裝器，整合連線紀錄功能"""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """執行 HTTP 請求並記錄連線資訊"""
        start_time = time.time()

        # 準備請求參數
        headers = kwargs.get("headers", {})
        data = kwargs.get("data")
        json_data = kwargs.get("json")
        params = kwargs.get("params")
        proxies = kwargs.get("proxies")
        timeout = kwargs.get("timeout", self.timeout)
        thread_id = get_thread_context()

        # 記錄請求到新的 HTTP 記錄器
        request_id = http_logger.log_request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            json_data=json_data,
            params=params,
            timeout=timeout,
            thread_id=thread_id,
        )

        # 記錄請求到舊的連線記錄器（保持向後相容）
        network_config.log_connection_request(
            method=method,
            url=url,
            headers=headers,
            data=data or json_data,
            proxies=proxies,
            timeout=timeout,
        )

        try:
            # 執行請求
            response = requests.request(method=method, url=url, **kwargs)

            # 計算回應時間
            response_time = time.time() - start_time

            # 記錄回應到新的 HTTP 記錄器
            http_logger.log_response(
                request_id=request_id,
                url=url,
                status_code=response.status_code,
                headers=dict(response.headers),
                content=response.content,
                response_time=response_time,
                thread_id=thread_id,
            )

            # 記錄回應到舊的連線記錄器（保持向後相容）
            network_config.log_connection_response(
                url=url,
                status_code=response.status_code,
                response_headers=dict(response.headers),
                response_size=len(response.content),
                response_time=response_time,
            )

            return response

        except Exception as e:
            # 記錄錯誤到新的 HTTP 記錄器
            http_logger.log_error(
                request_id=request_id,
                url=url,
                error=e,
                method=method,
                thread_id=thread_id,
            )

            # 記錄錯誤到舊的連線記錄器（保持向後相容）
            network_config.log_connection_error(url=url, error=e, method=method)
            raise

    def get(self, url: str, **kwargs) -> requests.Response:
        """執行 GET 請求"""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """執行 POST 請求"""
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> requests.Response:
        """執行 PUT 請求"""
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> requests.Response:
        """執行 DELETE 請求"""
        return self.request("DELETE", url, **kwargs)

    def patch(self, url: str, **kwargs) -> requests.Response:
        """執行 PATCH 請求"""
        return self.request("PATCH", url, **kwargs)


# 全域 HTTP 客戶端實例
http_client = HttpClient()
