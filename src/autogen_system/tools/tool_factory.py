# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
工具工廠

統一創建和配置所有類型的工具。
"""

import os
import asyncio
from typing import Dict, List, Any, Optional, Callable

from src.tools import (
    get_web_search_tool,
    python_repl_tool,
    crawl_tool,
    get_retriever_tool,
)
from src.server.mcp_utils import load_mcp_tools
from src.config import load_yaml_config
from src.logging import get_logger

from .adapters import global_tool_registry
from .search_tools import create_web_search_tool
from .code_execution_tools import AutoGenPythonExecutor
from .crawl_tools import AutoGenCrawlTool
from .mcp_manager import global_mcp_manager, initialize_mcp_system

logger = get_logger(__name__)


class ToolFactory:
    """
    工具工廠

    負責創建、配置和註冊所有類型的工具到 AutoGen 系統。
    """

    def __init__(self):
        """初始化工具工廠"""
        self.config = None
        self.initialized_tools: Dict[str, Any] = {}
        self._load_config()
        logger.info("工具工廠初始化完成")

    def _load_config(self):
        """載入配置"""
        try:
            self.config = load_yaml_config("conf.yaml")
            logger.info("工具配置載入成功")
        except Exception as e:
            logger.warning(f"工具配置載入失敗，使用預設配置: {e}")
            self.config = {}

    async def create_all_tools(self) -> Dict[str, Callable]:
        """
        創建所有工具

        Returns:
            Dict[str, Callable]: 工具名稱到工具函數的映射
        """
        logger.info("開始創建所有工具")

        # 創建各類工具
        await self._create_search_tools()
        await self._create_code_execution_tools()
        await self._create_crawl_tools()
        await self._create_mcp_tools()
        await self._create_retriever_tools()

        # 返回所有註冊的工具
        tools = {}
        for tool_name in global_tool_registry.list_tools():
            tool_func = global_tool_registry.get_tool(tool_name)
            if tool_func:
                tools[tool_name] = tool_func

        logger.info(f"工具創建完成，共 {len(tools)} 個工具")
        return tools

    async def _create_search_tools(self):
        """創建搜尋工具"""
        try:
            logger.info("創建搜尋工具")

            # 1. 適配原有的 LangChain 搜尋工具
            search_config = self.config.get("SEARCH_ENGINE", {})
            max_results = search_config.get("max_results", 5)

            original_search_tool = get_web_search_tool(max_results)
            global_tool_registry.register_langchain_tool(original_search_tool, category="search")

            # 2. 創建 AutoGen 原生搜尋工具
            autogen_search_tool = create_web_search_tool(max_results)
            global_tool_registry.register_native_tool(
                autogen_search_tool.search,
                name="autogen_web_search",
                description="AutoGen 原生網路搜尋工具",
                category="search",
            )

            self.initialized_tools["search"] = True
            logger.info("搜尋工具創建成功")

        except Exception as e:
            logger.error(f"搜尋工具創建失敗: {e}")

    async def _create_code_execution_tools(self):
        """創建程式碼執行工具"""
        try:
            logger.info("創建程式碼執行工具")

            # 1. 適配原有的 python_repl_tool
            global_tool_registry.register_langchain_tool(python_repl_tool, category="code")

            # 2. 創建 AutoGen 原生程式碼執行器
            python_executor = AutoGenPythonExecutor()
            global_tool_registry.register_native_tool(
                python_executor.execute_code,
                name="autogen_python_executor",
                description="AutoGen 原生 Python 程式碼執行器",
                category="code",
            )

            self.initialized_tools["code"] = True
            logger.info("程式碼執行工具創建成功")

        except Exception as e:
            logger.error(f"程式碼執行工具創建失敗: {e}")

    async def _create_crawl_tools(self):
        """創建爬蟲工具"""
        try:
            logger.info("創建爬蟲工具")

            # 1. 適配原有的 crawl_tool
            global_tool_registry.register_langchain_tool(crawl_tool, category="crawl")

            # 2. 創建 AutoGen 原生爬蟲工具
            autogen_crawl_tool = AutoGenCrawlTool()
            global_tool_registry.register_native_tool(
                autogen_crawl_tool.crawl_url,
                name="autogen_crawl",
                description="AutoGen 原生網頁爬蟲工具",
                category="crawl",
            )

            self.initialized_tools["crawl"] = True
            logger.info("爬蟲工具創建成功")

        except Exception as e:
            logger.error(f"爬蟲工具創建失敗: {e}")

    async def _create_mcp_tools(self):
        """創建 MCP 工具"""
        try:
            logger.info("創建 MCP 工具")

            # 使用全局 MCP 管理器初始化所有伺服器
            initialization_results = await initialize_mcp_system()

            if initialization_results:
                successful_servers = sum(initialization_results.values())
                total_servers = len(initialization_results)
                logger.info(f"MCP 伺服器初始化: {successful_servers}/{total_servers} 成功")

                # 註冊 MCP 工具到全局註冊中心
                global_tool_registry.register_native_tool(
                    global_mcp_manager.execute_mcp_tool,
                    name="mcp_tool_executor",
                    description="執行 MCP 工具",
                    category="mcp",
                )

                # 註冊 MCP 管理工具
                global_tool_registry.register_native_tool(
                    global_mcp_manager.get_available_tools,
                    name="list_mcp_tools",
                    description="列出可用的 MCP 工具",
                    category="mcp",
                )

                global_tool_registry.register_native_tool(
                    global_mcp_manager.get_server_status,
                    name="get_mcp_status",
                    description="獲取 MCP 伺服器狀態",
                    category="mcp",
                )
            else:
                logger.info("無可用的 MCP 伺服器，跳過 MCP 工具創建")

            self.initialized_tools["mcp"] = True
            logger.info("MCP 工具創建成功")

        except Exception as e:
            logger.error(f"MCP 工具創建失敗: {e}")

    async def _create_retriever_tools(self):
        """創建檢索工具"""
        try:
            logger.info("創建檢索工具")

            # 適配原有的檢索工具
            retriever_tool = get_retriever_tool()
            if retriever_tool:
                global_tool_registry.register_langchain_tool(retriever_tool, category="analysis")

            self.initialized_tools["retriever"] = True
            logger.info("檢索工具創建成功")

        except Exception as e:
            logger.error(f"檢索工具創建失敗: {e}")

    def get_tools_for_agent(self, agent_type: str) -> List[Callable]:
        """
        根據智能體類型獲取相應的工具

        Args:
            agent_type: 智能體類型

        Returns:
            List[Callable]: 適用的工具列表
        """
        tools = []

        if agent_type == "researcher":
            # 研究者需要搜尋和爬蟲工具
            tools.extend(global_tool_registry.get_tools_by_category("search"))
            tools.extend(global_tool_registry.get_tools_by_category("crawl"))
            tools.extend(global_tool_registry.get_tools_by_category("analysis"))

        elif agent_type == "coder":
            # 程式設計師需要程式碼執行工具
            tools.extend(global_tool_registry.get_tools_by_category("code"))

        elif agent_type == "coordinator":
            # 協調者可能需要 MCP 工具
            tools.extend(global_tool_registry.get_tools_by_category("mcp"))

        elif agent_type == "all":
            # 獲取所有工具
            for tool_name in global_tool_registry.list_tools():
                tool_func = global_tool_registry.get_tool(tool_name)
                if tool_func:
                    tools.append(tool_func)

        logger.info(f"為 {agent_type} 智能體準備了 {len(tools)} 個工具")
        return tools

    def get_tool_registry_stats(self) -> Dict[str, Any]:
        """獲取工具註冊統計信息"""
        return global_tool_registry.get_registry_stats()

    def export_tool_definitions(self) -> Dict[str, Any]:
        """導出工具定義"""
        return global_tool_registry.export_tool_definitions()


# 全局工具工廠實例
global_tool_factory = ToolFactory()


async def initialize_tools() -> Dict[str, Callable]:
    """
    初始化所有工具

    Returns:
        Dict[str, Callable]: 所有可用的工具
    """
    return await global_tool_factory.create_all_tools()


def get_tools_for_agent_type(agent_type: str) -> List[Callable]:
    """
    根據智能體類型獲取工具

    Args:
        agent_type: 智能體類型

    Returns:
        List[Callable]: 適用的工具列表
    """
    return global_tool_factory.get_tools_for_agent(agent_type)
