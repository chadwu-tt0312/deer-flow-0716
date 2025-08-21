# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 系統 API 相容性層

提供與現有 LangGraph API 的無縫相容性。
"""

from .api_adapter import AutoGenAPIAdapter, create_autogen_api_adapter
from .langgraph_compatibility import LangGraphCompatibilityLayer, create_langgraph_compatible_graph
from .response_mapper import (
    ResponseMapper,
    StreamResponseMapper,
    map_autogen_to_frontend,
    stream_autogen_to_frontend,
)
from .autogen_api_server import (
    autogen_api_server,
    get_autogen_chat_stream,
    invoke_autogen_workflow,
    stream_autogen_workflow,
)
from .system_switcher import (
    SystemSwitcher,
    SystemType,
    global_system_switcher,
    run_workflow_with_auto_switch,
    get_current_system,
    switch_to_autogen,
    switch_to_langgraph,
    system_health_check,
    get_system_performance_stats,
)
from .test_compatibility import (
    CompatibilityTester,
    run_compatibility_tests,
    quick_compatibility_check,
)

__all__ = [
    # 核心組件
    "AutoGenAPIAdapter",
    "LangGraphCompatibilityLayer",
    "ResponseMapper",
    "StreamResponseMapper",
    # 工廠函數
    "create_autogen_api_adapter",
    "create_langgraph_compatible_graph",
    "map_autogen_to_frontend",
    "stream_autogen_to_frontend",
    # API 服務器
    "autogen_api_server",
    "get_autogen_chat_stream",
    "invoke_autogen_workflow",
    "stream_autogen_workflow",
    # 系統切換器
    "SystemSwitcher",
    "SystemType",
    "global_system_switcher",
    "run_workflow_with_auto_switch",
    "get_current_system",
    "switch_to_autogen",
    "switch_to_langgraph",
    "system_health_check",
    "get_system_performance_stats",
    # 測試工具
    "CompatibilityTester",
    "run_compatibility_tests",
    "quick_compatibility_check",
]
