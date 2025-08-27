# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 系統模組 V3

此模組包含基於 Microsoft AutoGen 框架的多智能體系統實現，
用於替代原有的 LangGraph 架構。

主要組件：
- agents: V3 智能體實現
- conversations: 對話流程管理
- tools: 工具適配器和集成
- config: 配置管理
- adapters: 適配器層
"""

__version__ = "0.1.0"
__author__ = "DeerFlow Team"

# 匯出主要類別
from .agents.agents_v3 import BaseAgentV3, create_all_agents_v3
from .config.agent_config import AgentConfig, AgentRole

__all__ = [
    "BaseAgentV3",
    "create_all_agents_v3",
    "AgentConfig",
    "AgentRole",
]
