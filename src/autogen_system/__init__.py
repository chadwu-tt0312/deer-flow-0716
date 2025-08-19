# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 系統模組

此模組包含基於 Microsoft AutoGen 框架的多智能體系統實現，
用於替代原有的 LangGraph 架構。

主要組件：
- agents: 智能體實現
- conversations: 對話流程管理
- tools: 工具適配器和集成
- config: 配置管理
- controllers: 工作流控制器
"""

__version__ = "0.1.0"
__author__ = "DeerFlow Team"

# 匯出主要類別
from .controllers.workflow_controller import WorkflowController
from .controllers.ledger_orchestrator import LedgerOrchestrator
from .agents.base_agent import BaseResearchAgent, AgentFactory
from .config.agent_config import AgentConfig, WorkflowConfig, AgentRole, WorkflowType

__all__ = [
    "WorkflowController",
    "LedgerOrchestrator",
    "BaseResearchAgent",
    "AgentFactory",
    "AgentConfig",
    "WorkflowConfig",
    "AgentRole",
    "WorkflowType",
]
