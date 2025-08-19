# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 搜尋工具

提供網路搜尋功能的 AutoGen 原生實現。
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from src.tools.search import get_web_search_tool
from src.tools.tavily_search.tavily_search_results_with_images import TavilySearchResultsWithImages
from src.tools.grounding_bing_search.grounding_bing_search_tool import GroundingBingSearchTool
from src.config import SearchEngine, SELECTED_SEARCH_ENGINE
from src.logging import get_logger

logger = get_logger(__name__)


class AutoGenWebSearchTool:
    """
    AutoGen 網路搜尋工具

    統一的網路搜尋介面，支援多種搜尋引擎。
    """

    def __init__(self, max_results: int = 5, search_engine: str = None):
        """
        初始化搜尋工具

        Args:
            max_results: 最大搜尋結果數
            search_engine: 指定搜尋引擎（可選）
        """
        self.max_results = max_results
        self.search_engine = search_engine or SELECTED_SEARCH_ENGINE
        self.search_history: List[Dict[str, Any]] = []

        # 獲取底層搜尋工具
        self._setup_search_backend()

        logger.info(
            f"AutoGen 網路搜尋工具初始化：引擎={self.search_engine}, 最大結果={max_results}"
        )

    def _setup_search_backend(self):
        """設定搜尋後端"""
        try:
            self.backend_tool = get_web_search_tool(self.max_results)
            logger.info(f"搜尋後端設定成功: {type(self.backend_tool).__name__}")
        except Exception as e:
            logger.error(f"搜尋後端設定失敗: {e}")
            self.backend_tool = None

    async def search(self, query: str, **kwargs) -> str:
        """
        執行搜尋

        Args:
            query: 搜尋查詢
            **kwargs: 額外參數

        Returns:
            str: 搜尋結果（JSON 格式）
        """
        if not self.backend_tool:
            return json.dumps(
                {
                    "error": "搜尋後端未初始化",
                    "query": query,
                    "timestamp": datetime.now().isoformat(),
                },
                ensure_ascii=False,
            )

        try:
            logger.info(f"執行網路搜尋: {query}")

            # 記錄搜尋歷史
            search_record = {
                "query": query,
                "timestamp": datetime.now(),
                "engine": self.search_engine,
                "max_results": self.max_results,
            }

            # 執行搜尋
            if hasattr(self.backend_tool, "ainvoke"):
                result = await self.backend_tool.ainvoke({"query": query})
            else:
                result = self.backend_tool.invoke({"query": query})

            # 處理結果
            processed_result = self._process_search_result(result, query)

            # 更新搜尋記錄
            search_record["result_count"] = len(processed_result.get("results", []))
            search_record["success"] = True
            self.search_history.append(search_record)

            logger.info(f"搜尋完成: {query}, 結果數: {search_record['result_count']}")

            return json.dumps(processed_result, ensure_ascii=False, indent=2)

        except Exception as e:
            error_msg = f"搜尋執行失敗: {str(e)}"
            logger.error(error_msg)

            # 記錄失敗
            search_record["success"] = False
            search_record["error"] = str(e)
            self.search_history.append(search_record)

            return json.dumps(
                {"error": error_msg, "query": query, "timestamp": datetime.now().isoformat()},
                ensure_ascii=False,
            )

    def _process_search_result(self, raw_result: Any, query: str) -> Dict[str, Any]:
        """處理搜尋結果"""
        processed = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "engine": self.search_engine,
            "results": [],
        }

        try:
            if isinstance(raw_result, list):
                # 列表格式結果
                for item in raw_result[: self.max_results]:
                    if isinstance(item, dict):
                        processed_item = {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "content": item.get("content", ""),
                            "source": item.get("source", "web"),
                        }
                        processed["results"].append(processed_item)

            elif isinstance(raw_result, dict):
                # 字典格式結果
                if "results" in raw_result:
                    processed["results"] = raw_result["results"][: self.max_results]
                else:
                    # 單一結果
                    processed["results"] = [raw_result]

            elif isinstance(raw_result, str):
                # 字串格式結果
                try:
                    parsed = json.loads(raw_result)
                    if isinstance(parsed, list):
                        processed["results"] = parsed[: self.max_results]
                    elif isinstance(parsed, dict):
                        processed["results"] = [parsed]
                except json.JSONDecodeError:
                    # 純文字結果
                    processed["results"] = [
                        {"title": f"搜尋結果: {query}", "content": raw_result, "source": "text"}
                    ]

            else:
                # 其他格式，轉為字串
                processed["results"] = [
                    {"title": f"搜尋結果: {query}", "content": str(raw_result), "source": "unknown"}
                ]

        except Exception as e:
            logger.error(f"處理搜尋結果失敗: {e}")
            processed["results"] = [
                {"title": "處理錯誤", "content": f"無法處理搜尋結果: {str(e)}", "source": "error"}
            ]

        return processed

    def get_search_history(self) -> List[Dict[str, Any]]:
        """獲取搜尋歷史"""
        return [
            {
                "query": record["query"],
                "timestamp": record["timestamp"].isoformat(),
                "engine": record["engine"],
                "result_count": record.get("result_count", 0),
                "success": record.get("success", True),
            }
            for record in self.search_history
        ]

    def clear_history(self):
        """清除搜尋歷史"""
        self.search_history.clear()
        logger.info("搜尋歷史已清除")


class AutoGenTavilySearchTool:
    """
    AutoGen Tavily 搜尋工具

    專門用於 Tavily 搜尋引擎的實現。
    """

    def __init__(self, max_results: int = 5, include_images: bool = True):
        """
        初始化 Tavily 搜尋工具

        Args:
            max_results: 最大搜尋結果數
            include_images: 是否包含圖片結果
        """
        self.max_results = max_results
        self.include_images = include_images

        try:
            self.tavily_tool = TavilySearchResultsWithImages(
                max_results=max_results, include_images=include_images
            )
            logger.info("Tavily 搜尋工具初始化成功")
        except Exception as e:
            logger.error(f"Tavily 搜尋工具初始化失敗: {e}")
            self.tavily_tool = None

    async def search_with_images(
        self, query: str, include_domains: List[str] = None, exclude_domains: List[str] = None
    ) -> str:
        """
        執行包含圖片的搜尋

        Args:
            query: 搜尋查詢
            include_domains: 包含的域名列表
            exclude_domains: 排除的域名列表

        Returns:
            str: 搜尋結果（包含圖片）
        """
        if not self.tavily_tool:
            return json.dumps(
                {"error": "Tavily 搜尋工具未初始化", "query": query}, ensure_ascii=False
            )

        try:
            logger.info(f"執行 Tavily 搜尋（含圖片）: {query}")

            search_params = {"query": query}
            if include_domains:
                search_params["include_domains"] = include_domains
            if exclude_domains:
                search_params["exclude_domains"] = exclude_domains

            result = await self.tavily_tool.ainvoke(search_params)

            # 處理結果格式
            if isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                except json.JSONDecodeError:
                    parsed_result = {"content": result}
            else:
                parsed_result = result

            formatted_result = {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "engine": "tavily",
                "include_images": self.include_images,
                "results": parsed_result,
            }

            return json.dumps(formatted_result, ensure_ascii=False, indent=2)

        except Exception as e:
            error_msg = f"Tavily 搜尋失敗: {str(e)}"
            logger.error(error_msg)
            return json.dumps(
                {"error": error_msg, "query": query, "timestamp": datetime.now().isoformat()},
                ensure_ascii=False,
            )


# 便利函數
def create_web_search_tool(max_results: int = 5) -> AutoGenWebSearchTool:
    """創建網路搜尋工具"""
    return AutoGenWebSearchTool(max_results=max_results)


def create_tavily_search_tool(
    max_results: int = 5, include_images: bool = True
) -> AutoGenTavilySearchTool:
    """創建 Tavily 搜尋工具"""
    return AutoGenTavilySearchTool(max_results=max_results, include_images=include_images)


# 工具函數（用於直接註冊到 AutoGen 代理）
async def web_search_function(query: str, max_results: int = 5) -> str:
    """網路搜尋函數"""
    tool = create_web_search_tool(max_results)
    return await tool.search(query)


async def tavily_search_function(
    query: str, max_results: int = 5, include_images: bool = True
) -> str:
    """Tavily 搜尋函數"""
    tool = create_tavily_search_tool(max_results, include_images)
    return await tool.search_with_images(query)
