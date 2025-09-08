# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
from src.deerflow_logging import get_logger
import os
import time
from typing import Dict, List, Optional

import requests
from pydantic import BaseModel, Field

from src.utils.network_config import network_config
from src.utils.http_client import http_client

logger = get_logger(__name__)


class GroundingBingSearchConfig(BaseModel):
    """Grounding Bing Search 配置"""

    base_url: str = Field(default="http://172.16.128.4:11009/api/projects/searchProject")
    api_version: str = Field(default="2025-05-15-preview")
    client_id: str = Field(default="")
    client_secret: str = Field(default="")
    tenant_id: str = Field(default="")
    connection_id: str = Field(default="")
    count: int = Field(default=10)
    market: str = Field(default="zh-tw")
    set_lang: str = Field(default="zh-hant")


class GroundingBingSearchAPIWrapper:
    """Grounding Bing Search API 包裝器"""

    def __init__(self, config: Optional[GroundingBingSearchConfig] = None):
        self.config = config or GroundingBingSearchConfig()
        self._token = None
        self._token_expires_at = 0

    def _get_token(self) -> str:
        """取得 Azure AD 存取權杖"""
        current_time = time.time()

        # 如果權杖還有 5 分鐘才過期，直接返回
        if self._token and current_time < self._token_expires_at - 300:
            return self._token

        url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"
        payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "client_credentials",
            "scope": "https://ai.azure.com/.default",
        }

        try:
            # 使用新的 HTTP 客戶端，自動記錄連線資訊
            response = http_client.post(url, data=payload)
            response.raise_for_status()
            token_data = response.json()

            self._token = token_data.get("access_token")
            # 設定權杖過期時間（提前 5 分鐘）
            self._token_expires_at = current_time + token_data.get("expires_in", 3600) - 300

            return self._token
        except Exception as e:
            logger.error(f"取得 Azure AD 權杖失敗: {e}")
            raise

    def _api_request(self, method: str, path: str, payload: Optional[Dict] = None) -> Dict:
        """統一處理 API 請求"""
        url = f"{self.config.base_url}/{path}?api-version={self.config.api_version}"
        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

        # 更新 headers，加入網路配置
        headers = network_config.update_headers(headers)

        try:
            # 使用新的 HTTP 客戶端，自動記錄連線資訊
            if method.upper() == "GET":
                response = http_client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = http_client.post(url, headers=headers, json=payload)
            elif method.upper() == "DELETE":
                response = http_client.delete(url, headers=headers)
            else:
                raise ValueError(f"不支援的 HTTP 方法: {method}")

            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API 請求失敗: {e}")
            raise

    def search(self, query: str, max_results: Optional[int] = None) -> Dict:
        """執行 Grounding Bing Search"""
        # 建立 Assistant
        assistant_payload = {
            "instructions": "You are a helpful search assistant that provides accurate and relevant information.",
            "name": "GroundingBingSearchAssistant",
            "tools": [
                {
                    "type": "bing_grounding",
                    "bing_grounding": {
                        "search_configurations": [
                            {
                                "connection_id": self.config.connection_id,
                                "count": max_results or self.config.count,
                                "market": self.config.market,
                                "set_lang": self.config.set_lang,
                            }
                        ]
                    },
                }
            ],
            "model": "gpt-4o-mini",
        }

        try:
            # 建立 Assistant
            assistant_result = self._api_request("POST", "assistants", assistant_payload)
            assistant_id = assistant_result.get("id")

            # 建立 Thread
            thread_result = self._api_request("POST", "threads")
            thread_id = thread_result.get("id")

            # 新增訊息到 Thread
            message_payload = {"role": "user", "content": query}
            message_result = self._api_request(
                "POST", f"threads/{thread_id}/messages", message_payload
            )

            # 執行 Thread
            run_payload = {"assistant_id": assistant_id}
            run_result = self._api_request("POST", f"threads/{thread_id}/runs", run_payload)
            run_id = run_result.get("id")

            # 等待執行完成
            max_wait_time = 60  # 最多等待 60 秒
            wait_time = 0
            while wait_time < max_wait_time:
                run_status = self._api_request("GET", f"threads/{thread_id}/runs/{run_id}")
                status = run_status.get("status")

                if status == "completed":
                    break
                elif status in ["failed", "cancelled", "expired"]:
                    raise Exception(f"Thread 執行失敗: {status}")

                time.sleep(2)
                wait_time += 2

            if wait_time >= max_wait_time:
                raise Exception("Thread 執行超時")

            # 取得結果
            messages = self._api_request("GET", f"threads/{thread_id}/messages")

            # 清理資源
            try:
                self._api_request("DELETE", f"threads/{thread_id}")
                self._api_request("DELETE", f"assistants/{assistant_id}")
            except Exception as e:
                logger.warning(f"清理資源失敗: {e}")

            # 解析結果
            return self._parse_search_results(messages, query)

        except Exception as e:
            logger.error(f"Grounding Bing Search 失敗: {e}")
            raise

    def _parse_search_results(self, messages: Dict, query: str) -> Dict:
        """解析搜尋結果"""
        try:
            # 找到最新的 assistant 訊息
            assistant_messages = [
                msg for msg in messages.get("data", []) if msg.get("role") == "assistant"
            ]

            if not assistant_messages:
                return {"query": query, "results": [], "error": "未找到搜尋結果"}

            latest_message = assistant_messages[0]
            content = latest_message.get("content", [])

            # 解析內容
            results = []
            for item in content:
                if item.get("type") == "text":
                    text_content = item.get("text", {}).get("value", "")
                    # 這裡可以進一步解析文本內容，提取結構化資訊
                    results.append({"type": "text", "content": text_content})

            return {
                "query": query,
                "results": results,
                "message_id": latest_message.get("id"),
                "created_at": latest_message.get("created_at"),
            }

        except Exception as e:
            logger.error(f"解析搜尋結果失敗: {e}")
            return {"query": query, "results": [], "error": f"解析結果失敗: {str(e)}"}
