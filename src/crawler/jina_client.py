# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os

import requests

from src.utils.network_config import network_config

logger = logging.getLogger(__name__)


class JinaClient:
    def crawl(self, url: str, return_format: str = "html") -> str:
        headers = {
            "Content-Type": "application/json",
            "X-Return-Format": return_format,
        }
        if os.getenv("JINA_API_KEY"):
            headers["Authorization"] = f"Bearer {os.getenv('JINA_API_KEY')}"
        else:
            logger.warning(
                "Jina API key is not set. Provide your own key to access a higher rate limit. See https://jina.ai/reader for more information."
            )
        data = {"url": url}

        # 更新 headers，加入網路配置
        headers = network_config.update_headers(headers)

        # 取得網路配置
        request_config = network_config.get_request_config("https://r.jina.ai/")

        response = requests.post("https://r.jina.ai/", headers=headers, json=data, **request_config)
        return response.text
