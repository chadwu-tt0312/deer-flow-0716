# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
工具整合模組

為 AutoGen V3 智能體系統整合核心工具。
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional
from functools import wraps

from src.deerflow_logging import get_thread_logger


def _get_logger():
    """獲取當前 thread 的 logger"""
    try:
        return get_thread_logger()
    except RuntimeError:
        # 如果沒有設定 thread context，使用簡單的 logger
        from src.deerflow_logging import get_simple_logger

        return get_simple_logger(__name__)


from src.tools import (
    get_web_search_tool,
    python_repl_tool,
    crawl_tool,
)


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
            _get_logger().error(error_msg)
            return error_msg

    return async_wrapper


class ToolsIntegrator:
    """工具整合器"""

    def __init__(self):
        self.tools_cache: Dict[str, Callable] = {}
        self.initialized = False
        _get_logger().info("工具整合器初始化")

    async def initialize_tools(self) -> Dict[str, Callable]:
        """初始化所有工具"""
        if self.initialized:
            return self.tools_cache

        _get_logger().info("開始初始化工具...")

        try:
            # 1. 網路搜尋工具
            await self._setup_search_tools()

            # 2. 程式碼執行工具
            await self._setup_code_tools()

            # 3. 網頁爬蟲工具
            await self._setup_crawl_tools()

            self.initialized = True
            _get_logger().info(f"工具初始化完成，共 {len(self.tools_cache)} 個工具")

        except Exception as e:
            _get_logger().error(f"工具初始化失敗: {e}")

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
            _get_logger().info("✅ web_search 工具設置完成")

        except Exception as e:
            _get_logger().error(f"❌ web_search 工具設置失敗: {e}")

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
            _get_logger().info("✅ Python REPL 工具設置完成")

        except Exception as e:
            _get_logger().error(f"❌ Python REPL 工具設置失敗: {e}")

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
            _get_logger().info("✅ crawl_website 工具設置完成")

        except Exception as e:
            _get_logger().error(f"❌ crawl_website 工具設置失敗: {e}")

    def get_tools_for_agent(self, agent_type: str) -> List[Callable]:
        """
        根據智能體類型獲取相應的工具

        Args:
            agent_type: 智能體類型

        Returns:
            List[Callable]: 適用的工具列表
        """
        if not self.initialized:
            _get_logger().warning("工具尚未初始化，返回空列表")
            return []

        tools = []

        if agent_type == "coordinator":
            # 協調者不需要特殊工具
            pass

        elif agent_type == "researcher":
            # 研究者需要搜尋和爬蟲工具
            tools.extend(
                [
                    self.tools_cache.get("web_search"),
                    self.tools_cache.get("crawl_website"),
                ]
            )

        elif agent_type == "coder":
            # 程式設計師需要程式碼執行工具
            tools.extend(
                [
                    self.tools_cache.get("python_repl"),
                ]
            )

        elif agent_type == "all":
            # 獲取所有工具
            tools = list(self.tools_cache.values())

        # 過濾掉 None 值
        tools = [tool for tool in tools if tool is not None]

        # 移除重複的日誌輸出，只在初始化時輸出一次
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
    _get_logger().info("🧪 開始測試工具整合...")

    # 初始化工具
    tools = await initialize_all_tools()

    # 顯示工具資訊
    _get_logger().info(f"📊 可用工具總數: {len(tools)}")

    for agent_type in ["coordinator", "researcher", "coder"]:
        agent_tools = get_tools_for_agent_type(agent_type)
        _get_logger().info(f"🤖 {agent_type} 智能體工具數: {len(agent_tools)}")

    # 簡單功能測試
    try:
        if "web_search" in tools:
            _get_logger().info("🔍 測試網路搜尋工具...")
            result = await tools["web_search"]("測試搜尋")
            _get_logger().info(f"✅ 搜尋測試完成: {len(str(result))} 字符")
    except Exception as e:
        _get_logger().error(f"❌ 搜尋測試失敗: {e}")

    _get_logger().info("🎉 工具整合測試完成")


if __name__ == "__main__":
    asyncio.run(test_tools_integration())
