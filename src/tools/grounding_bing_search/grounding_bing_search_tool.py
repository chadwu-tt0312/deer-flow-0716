# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
from typing import Dict, List, Optional, Tuple, Union

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from pydantic import Field

from .grounding_bing_search_api_wrapper import (
    GroundingBingSearchAPIWrapper,
    GroundingBingSearchConfig,
)


class GroundingBingSearchTool(BaseTool):
    """Grounding Bing Search 工具

    使用 Azure OpenAI 的 Bing Grounding 功能進行搜尋，提供更準確和相關的搜尋結果。

    設定:
        需要在環境變數中設定以下參數:
        - GROUNDING_BING_CLIENT_ID: Azure AD 應用程式 ID
        - GROUNDING_BING_CLIENT_SECRET: Azure AD 應用程式密碼
        - GROUNDING_BING_TENANT_ID: Azure AD 租用戶 ID
        - GROUNDING_BING_CONNECTION_ID: Bing Search 連線 ID
        - GROUNDING_BING_BASE_URL: API 基礎 URL (可選)

    實例化:
        .. code-block:: python

            from src.tools.grounding_bing_search import GroundingBingSearchTool

            tool = GroundingBingSearchTool(
                max_results=10,
                market="zh-tw",
                set_lang="zh-hant"
            )

    直接調用:
        .. code-block:: python

            tool.invoke({'query': '最新的人工智慧發展'})

    回傳格式:
        .. code-block:: json

            {
                "query": "最新的人工智慧發展",
                "results": [
                    {
                        "type": "text",
                        "content": "根據最新的研究報告，人工智慧在 2024 年有重大突破..."
                    }
                ],
                "message_id": "msg_xxx",
                "created_at": "2024-01-01T00:00:00Z"
            }
    """

    name: str = "grounding_bing_search"
    description: str = (
        "使用 Azure OpenAI 的 Bing Grounding 功能進行搜尋，提供準確和相關的搜尋結果。"
        "適用於需要高品質搜尋結果的場景。"
    )

    max_results: int = Field(default=10, description="最大搜尋結果數量")
    market: str = Field(default="zh-tw", description="搜尋市場區域")
    set_lang: str = Field(default="zh-hant", description="搜尋語言設定")

    api_wrapper: GroundingBingSearchAPIWrapper = Field(
        default_factory=lambda: GroundingBingSearchAPIWrapper()
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 從環境變數取得配置
        config = GroundingBingSearchConfig(
            client_id=kwargs.get("client_id") or "",
            client_secret=kwargs.get("client_secret") or "",
            tenant_id=kwargs.get("tenant_id") or "",
            connection_id=kwargs.get("connection_id") or "",
            count=self.max_results,
            market=self.market,
            set_lang=self.set_lang,
            base_url=kwargs.get("base_url", "http://172.16.128.4:11009/api/projects/searchProject"),
        )

        self.api_wrapper = GroundingBingSearchAPIWrapper(config)

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Union[List[Dict[str, str]], str]:
        """執行搜尋"""
        try:
            results = self.api_wrapper.search(query, self.max_results)

            # 格式化結果以符合其他搜尋工具的格式
            formatted_results = []
            for result in results.get("results", []):
                if result.get("type") == "text":
                    formatted_results.append(
                        {
                            "title": f"Grounding Bing Search Result",
                            "content": result.get("content", ""),
                            "url": "",  # Grounding Bing Search 不提供直接 URL
                            "source": "grounding_bing_search",
                        }
                    )

            return formatted_results

        except Exception as e:
            return f"Grounding Bing Search 失敗: {str(e)}"

    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Union[List[Dict[str, str]], str]:
        """非同步執行搜尋"""
        # 目前實作為同步調用
        return self._run(query, run_manager)

    def invoke(
        self,
        input: Union[str, Dict],
        config: Optional[Dict] = None,
        **kwargs,
    ) -> Union[List[Dict[str, str]], str]:
        """調用工具"""
        if isinstance(input, str):
            query = input
        elif isinstance(input, dict):
            query = input.get("query", "")
        else:
            raise ValueError("輸入必須是字串或包含 'query' 鍵的字典")

        return self._run(query)
