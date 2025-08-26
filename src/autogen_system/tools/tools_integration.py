# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
工具整合模組

為 AutoGen SelectorGroupChat 範例整合所有現有工具，
包括 web_search, crawl_tool, python_repl, local_search 等。
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional
from functools import wraps

from src.logging import get_logger
from src.tools import (
    get_web_search_tool,
    python_repl_tool,
    crawl_tool,
    get_retriever_tool,
)
from src.autogen_system.tools.tool_factory import global_tool_factory

logger = get_logger(__name__)


def autogen_tool_wrapper(func: Callable) -> Callable:
    """
    AutoGen 工具包裝器

    將現有的工具函數包裝為 AutoGen 兼容的格式。
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            # 如果原函數是異步的
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # 確保返回字串格式
            if isinstance(result, str):
                return result
            elif hasattr(result, "content"):
                return result.content
            else:
                return str(result)

        except Exception as e:
            error_msg = f"工具執行錯誤: {str(e)}"
            logger.error(error_msg)
            return error_msg

    return async_wrapper


class ToolsIntegrator:
    """工具整合器"""

    def __init__(self):
        self.tools_cache: Dict[str, Callable] = {}
        self.initialized = False
        logger.info("工具整合器初始化")

    async def initialize_tools(self) -> Dict[str, Callable]:
        """初始化所有工具"""
        if self.initialized:
            return self.tools_cache

        logger.info("開始初始化工具...")

        try:
            # 1. 網路搜尋工具
            await self._setup_search_tools()

            # 2. 程式碼執行工具
            await self._setup_code_tools()

            # 3. 網頁爬蟲工具
            await self._setup_crawl_tools()

            # 4. 本地檢索工具
            # await self._setup_retrieval_tools()

            # 5. 使用工具工廠獲取額外工具
            await self._setup_factory_tools()

            self.initialized = True
            logger.info(f"工具初始化完成，共 {len(self.tools_cache)} 個工具")

        except Exception as e:
            logger.error(f"工具初始化失敗: {e}")

        return self.tools_cache

    async def _setup_search_tools(self):
        """設置搜尋工具"""
        try:
            # 原有的網路搜尋工具
            search_tool = get_web_search_tool(max_search_results=5)

            @autogen_tool_wrapper
            async def web_search(query: str) -> str:
                """網路搜尋工具 - 搜尋網路上的相關資訊"""
                result = search_tool.invoke({"query": query})
                return str(result)

            self.tools_cache["web_search"] = web_search
            logger.info("✅ 網路搜尋工具設置完成")

        except Exception as e:
            logger.error(f"❌ 網路搜尋工具設置失敗: {e}")

    async def _setup_code_tools(self):
        """設置程式碼執行工具"""
        try:
            # Python REPL 工具
            @autogen_tool_wrapper
            async def python_repl(code: str) -> str:
                """Python 程式碼執行工具 - 執行 Python 程式碼並返回結果"""
                result = python_repl_tool.invoke({"query": code})
                return str(result)

            self.tools_cache["python_repl"] = python_repl
            logger.info("✅ Python REPL 工具設置完成")

        except Exception as e:
            logger.error(f"❌ Python REPL 工具設置失敗: {e}")

    async def _setup_crawl_tools(self):
        """設置爬蟲工具"""
        try:
            # 網頁爬蟲工具
            @autogen_tool_wrapper
            async def crawl_website(url: str) -> str:
                """網頁爬蟲工具 - 爬取指定網頁的內容"""
                result = crawl_tool.invoke({"url": url})
                return str(result)

            self.tools_cache["crawl_website"] = crawl_website
            logger.info("✅ 網頁爬蟲工具設置完成")

        except Exception as e:
            logger.error(f"❌ 網頁爬蟲工具設置失敗: {e}")

    # async def _setup_retrieval_tools(self):
    #     """設置檢索工具"""
    #     try:
    #         # 本地檢索工具 - 需要提供資源列表，目前跳過
    #         # TODO: 在有資源配置時啟用檢索工具
    #         # retriever_tool = get_retriever_tool(resources=[])
    #         retriever_tool = None
    #         if retriever_tool:

    #             @autogen_tool_wrapper
    #             async def local_search(query: str) -> str:
    #                 """本地搜尋工具 - 在本地知識庫中搜尋相關資訊"""
    #                 result = retriever_tool.invoke({"query": query})
    #                 return str(result)

    #             self.tools_cache["local_search"] = local_search
    #             logger.info("✅ 本地檢索工具設置完成")
    #         else:
    #             logger.warning("⚠️ 本地檢索工具無法獲取，跳過")

    #     except Exception as e:
    #         logger.error(f"❌ 本地檢索工具設置失敗: {e}")

    async def _setup_factory_tools(self):
        """使用工具工廠設置額外工具"""
        try:
            # 從工具工廠獲取工具
            factory_tools = await global_tool_factory.create_all_tools()

            for tool_name, tool_func in factory_tools.items():
                # 避免重複添加
                if tool_name not in self.tools_cache:
                    # 包裝工具函數
                    wrapped_tool = autogen_tool_wrapper(tool_func)
                    self.tools_cache[f"factory_{tool_name}"] = wrapped_tool

            logger.info(f"✅ 工具工廠工具設置完成，新增 {len(factory_tools)} 個工具")

        except Exception as e:
            logger.error(f"❌ 工具工廠工具設置失敗: {e}")

    def get_tools_for_agent(self, agent_type: str) -> List[Callable]:
        """
        根據智能體類型獲取相應的工具

        Args:
            agent_type: 智能體類型

        Returns:
            List[Callable]: 適用的工具列表
        """
        if not self.initialized:
            logger.warning("工具尚未初始化，返回空列表")
            return []

        tools = []

        if agent_type == "coordinator":
            # 協調者可能需要狀態查詢工具
            tools.extend(
                [
                    tool
                    for name, tool in self.tools_cache.items()
                    if "status" in name or "factory_mcp" in name
                ]
            )

        elif agent_type == "researcher":
            # 研究者需要搜尋和爬蟲工具
            research_tools = [
                self.tools_cache.get("web_search"),
                self.tools_cache.get("crawl_website"),
                self.tools_cache.get("local_search"),
            ]
            # 加入工廠搜尋工具
            research_tools.extend(
                [
                    tool
                    for name, tool in self.tools_cache.items()
                    if "search" in name or "crawl" in name
                ]
            )
            tools.extend([tool for tool in research_tools if tool is not None])

        elif agent_type == "coder":
            # 程式設計師需要程式碼執行工具
            code_tools = [
                self.tools_cache.get("python_repl"),
            ]
            # 加入工廠程式碼工具
            code_tools.extend(
                [
                    tool
                    for name, tool in self.tools_cache.items()
                    if "python" in name or "code" in name or "executor" in name
                ]
            )
            tools.extend([tool for tool in code_tools if tool is not None])

        elif agent_type == "all":
            # 獲取所有工具
            tools = list(self.tools_cache.values())

        logger.info(f"為 {agent_type} 智能體準備了 {len(tools)} 個工具")
        return tools

    def get_available_tools(self) -> Dict[str, str]:
        """獲取可用工具列表及其描述"""
        tools_info = {}

        for name, tool in self.tools_cache.items():
            doc = tool.__doc__ or "無描述"
            tools_info[name] = doc.strip()

        return tools_info

    def get_tool_by_name(self, name: str) -> Optional[Callable]:
        """根據名稱獲取工具"""
        return self.tools_cache.get(name)


# 全局工具整合器實例
global_tools_integrator = ToolsIntegrator()


async def initialize_all_tools() -> Dict[str, Callable]:
    """
    初始化所有工具的便利函數

    Returns:
        Dict[str, Callable]: 所有可用的工具
    """
    return await global_tools_integrator.initialize_tools()


def get_tools_for_agent_type(agent_type: str) -> List[Callable]:
    """
    根據智能體類型獲取工具的便利函數

    Args:
        agent_type: 智能體類型

    Returns:
        List[Callable]: 適用的工具列表
    """
    return global_tools_integrator.get_tools_for_agent(agent_type)


def get_available_tools_info() -> Dict[str, str]:
    """獲取可用工具資訊的便利函數"""
    return global_tools_integrator.get_available_tools()


async def test_tools_integration():
    """測試工具整合"""
    logger.info("🧪 開始測試工具整合...")

    # 初始化工具
    tools = await initialize_all_tools()

    # 顯示工具資訊
    logger.info(f"📊 可用工具總數: {len(tools)}")

    for agent_type in ["coordinator", "researcher", "coder"]:
        agent_tools = get_tools_for_agent_type(agent_type)
        logger.info(f"🤖 {agent_type} 智能體工具數: {len(agent_tools)}")

    # 簡單功能測試
    try:
        if "web_search" in tools:
            logger.info("🔍 測試網路搜尋工具...")
            result = await tools["web_search"]("測試搜尋")
            logger.info(f"✅ 搜尋測試完成: {len(str(result))} 字符")
    except Exception as e:
        logger.error(f"❌ 搜尋測試失敗: {e}")

    logger.info("🎉 工具整合測試完成")


if __name__ == "__main__":
    asyncio.run(test_tools_integration())
