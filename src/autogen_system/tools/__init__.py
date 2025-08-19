# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 工具模組

提供工具適配、註冊和管理功能。
"""

from .adapters import (
    LangChainToolAdapter,
    AutoGenToolRegistry,
    ToolMetadata,
    global_tool_registry,
)
from .search_tools import (
    AutoGenWebSearchTool,
    AutoGenTavilySearchTool,
    create_web_search_tool,
    create_tavily_search_tool,
    web_search_function,
    tavily_search_function,
)
from .mcp_manager import (
    global_mcp_manager,
    initialize_mcp_system,
    execute_mcp_tool,
    get_mcp_tools,
    get_mcp_status,
)
from .mcp_config import (
    global_mcp_config_manager,
    MCPServerConfig,
)

__all__ = [
    # 適配器相關
    "LangChainToolAdapter",
    "AutoGenToolRegistry",
    "ToolMetadata",
    "global_tool_registry",
    # 搜尋工具
    "AutoGenWebSearchTool",
    "AutoGenTavilySearchTool",
    "create_web_search_tool",
    "create_tavily_search_tool",
    "web_search_function",
    "tavily_search_function",
    # MCP 工具
    "global_mcp_manager",
    "initialize_mcp_system",
    "execute_mcp_tool",
    "get_mcp_tools",
    "get_mcp_status",
    "global_mcp_config_manager",
    "MCPServerConfig",
]
