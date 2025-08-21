# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
基礎智能體模組

提供所有 AutoGen 智能體的基礎類別和通用功能。
"""

from typing import Dict, List, Any, Optional, Union, Callable
from abc import ABC, abstractmethod

try:
    from autogen_agentchat.agents import ConversableAgent, UserProxyAgent, AssistantAgent
    from autogen_agentchat.teams import BaseGroupChat as GroupChat

    # 使用 BaseGroupChat 作為 GroupChatManager 的替代
    GroupChatManager = BaseGroupChat
except ImportError:
    # 如果 AutoGen 未安裝，提供改進的模擬類別
    class ConversableAgent:
        def __init__(self, **kwargs):
            # 設置必要的屬性
            self.name = kwargs.get("name", "UnknownAgent")
            self.description = kwargs.get("description", "")
            self.system_message = kwargs.get("system_message", "")
            self.human_input_mode = kwargs.get("human_input_mode", "NEVER")
            self.max_consecutive_auto_reply = kwargs.get("max_consecutive_auto_reply", 0)
            self.llm_config = kwargs.get("llm_config", {})
            self._function_map = kwargs.get("function_map", {})

            # 設置其他可能的屬性
            for key, value in kwargs.items():
                if not hasattr(self, key):
                    setattr(self, key, value)

    class UserProxyAgent(ConversableAgent):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.human_input_mode = kwargs.get("human_input_mode", "TERMINATE")
            self.max_consecutive_auto_reply = kwargs.get("max_consecutive_auto_reply", 0)

    class AssistantAgent(ConversableAgent):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.human_input_mode = kwargs.get("human_input_mode", "NEVER")
            self.max_consecutive_auto_reply = kwargs.get("max_consecutive_auto_reply", 1)

    class GroupChat:
        def __init__(self, agents=None, messages=None, max_round=1, **kwargs):
            self.agents = agents or []
            self.messages = messages or []
            self.max_round = max_round

    class GroupChatManager(ConversableAgent):
        def __init__(self, groupchat=None, **kwargs):
            super().__init__(**kwargs)
            self.groupchat = groupchat


from ..config.agent_config import AgentConfig, AgentRole
from src.logging import get_logger

logger = get_logger(__name__)


class BaseResearchAgent(ConversableAgent):
    """
    研究系統基礎智能體類別

    繼承自 AutoGen 的 ConversableAgent，提供 DeerFlow 特定功能。
    """

    def __init__(self, config: AgentConfig, tools: Optional[List[Callable]] = None, **kwargs):
        """
        初始化基礎研究智能體

        Args:
            config: 智能體配置
            tools: 可用工具列表
            **kwargs: 其他 AutoGen 參數
        """
        self.config = config
        self.role = config.role
        self.tools = tools or []

        # 準備 AutoGen 配置
        autogen_config = config.to_autogen_config()
        autogen_config.update(kwargs)

        # 註冊工具
        if self.tools:
            autogen_config["function_map"] = {
                tool.__name__: tool for tool in self.tools if hasattr(tool, "__name__")
            }

        try:
            super().__init__(**autogen_config)
            # 確保有 name 屬性
            if not hasattr(self, "name"):
                self.name = config.name
            logger.info(f"成功初始化智能體: {config.name} (角色: {config.role.value})")
        except Exception as e:
            logger.error(f"初始化智能體失敗: {config.name}, 錯誤: {e}")
            raise

        # 設定角色特定的行為
        self._setup_role_specific_behavior()

    def _setup_role_specific_behavior(self):
        """設定角色特定的行為"""
        if self.role == AgentRole.COORDINATOR:
            self._setup_coordinator_behavior()
        elif self.role == AgentRole.PLANNER:
            self._setup_planner_behavior()
        elif self.role == AgentRole.RESEARCHER:
            self._setup_researcher_behavior()
        elif self.role == AgentRole.CODER:
            self._setup_coder_behavior()
        elif self.role == AgentRole.REPORTER:
            self._setup_reporter_behavior()

    def _setup_coordinator_behavior(self):
        """設定協調者行為"""
        self.description = "負責協調整個工作流程，管理智能體間的互動"

    def _setup_planner_behavior(self):
        """設定計劃者行為"""
        self.description = "負責分析需求並制定詳細的執行計劃"

    def _setup_researcher_behavior(self):
        """設定研究者行為"""
        self.description = "負責進行網路搜尋和資訊收集"

    def _setup_coder_behavior(self):
        """設定程式設計師行為"""
        self.description = "負責程式碼分析、執行和技術處理"

    def _setup_reporter_behavior(self):
        """設定報告者行為"""
        self.description = "負責整理資訊並生成最終報告"

    def add_tool(self, tool: Callable):
        """添加工具到智能體"""
        if tool not in self.tools:
            self.tools.append(tool)
            if hasattr(self, "_function_map"):
                tool_name = getattr(tool, "__name__", str(tool))
                self._function_map[tool_name] = tool
            tool_name = getattr(tool, "__name__", str(tool))
            logger.info(f"為智能體 {self.name} 添加工具: {tool_name}")

    def remove_tool(self, tool_name: str):
        """移除智能體的工具"""
        self.tools = [t for t in self.tools if getattr(t, "__name__", str(t)) != tool_name]
        if hasattr(self, "_function_map") and tool_name in self._function_map:
            del self._function_map[tool_name]
        logger.info(f"從智能體 {self.name} 移除工具: {tool_name}")

    def get_role_info(self) -> Dict[str, Any]:
        """取得角色資訊"""
        return {
            "name": getattr(self, "name", self.config.name),
            "role": self.role.value,
            "description": getattr(self, "description", self.config.description),
            "tools": [getattr(tool, "__name__", str(tool)) for tool in self.tools],
            "config": self.config,
        }

    async def a_send_message(
        self,
        message: Union[Dict, str],
        recipient: "BaseResearchAgent",
        request_reply: bool = None,
        silent: bool = False,
    ):
        """
        異步發送消息

        包裝原始的 AutoGen 發送方法，添加記錄功能。
        """
        logger.info(f"{self.name} 向 {recipient.name} 發送消息")

        try:
            if hasattr(super(), "a_send"):
                return await super().a_send(
                    message=message, recipient=recipient, request_reply=request_reply, silent=silent
                )
            else:
                # 降級為同步方法
                return self.send(
                    message=message, recipient=recipient, request_reply=request_reply, silent=silent
                )
        except Exception as e:
            logger.error(f"發送消息失敗: {self.name} -> {recipient.name}, 錯誤: {e}")
            raise


class UserProxyResearchAgent(BaseResearchAgent, UserProxyAgent):
    """
    用戶代理研究智能體

    用於人機互動和工作流控制。
    """

    def __init__(self, config: AgentConfig, **kwargs):
        # UserProxyAgent 的特定配置
        kwargs.setdefault("human_input_mode", "TERMINATE")
        kwargs.setdefault("max_consecutive_auto_reply", 0)

        BaseResearchAgent.__init__(self, config, **kwargs)

        logger.info(f"初始化用戶代理智能體: {config.name}")


class AssistantResearchAgent(BaseResearchAgent, AssistantAgent):
    """
    助手研究智能體

    用於各種專業任務執行。
    """

    def __init__(self, config: AgentConfig, tools: Optional[List[Callable]] = None, **kwargs):
        BaseResearchAgent.__init__(self, config, tools, **kwargs)

        logger.info(f"初始化助手智能體: {config.name}")


def create_research_agent(
    config: AgentConfig, tools: Optional[List[Callable]] = None, agent_type: str = "assistant"
) -> BaseResearchAgent:
    """
    智能體工廠函數

    根據配置和類型創建適當的智能體實例。

    Args:
        config: 智能體配置
        tools: 可用工具列表
        agent_type: 智能體類型 ("assistant", "user_proxy")

    Returns:
        BaseResearchAgent: 創建的智能體實例
    """
    if agent_type == "user_proxy":
        return UserProxyResearchAgent(config)
    elif agent_type == "assistant":
        return AssistantResearchAgent(config, tools)
    else:
        raise ValueError(f"不支援的智能體類型: {agent_type}")


class AgentFactory:
    """智能體工廠類別"""

    @staticmethod
    def create_coordinator(config: AgentConfig) -> "CoordinatorAgent":
        """創建協調者智能體"""
        from .coordinator_agent import CoordinatorAgent

        config.role = AgentRole.COORDINATOR
        return CoordinatorAgent(config)

    @staticmethod
    def create_planner(config: AgentConfig) -> "PlannerAgent":
        """創建計劃者智能體"""
        from .planner_agent import PlannerAgent

        config.role = AgentRole.PLANNER
        return PlannerAgent(config)

    @staticmethod
    def create_researcher(config: AgentConfig, tools: List[Callable] = None) -> "ResearcherAgent":
        """創建研究者智能體"""
        from .researcher_agent import ResearcherAgent

        config.role = AgentRole.RESEARCHER
        return ResearcherAgent(config, tools)

    @staticmethod
    def create_coder(config: AgentConfig, tools: List[Callable] = None) -> "CoderAgent":
        """創建程式設計師智能體"""
        from .coder_agent import CoderAgent

        config.role = AgentRole.CODER
        return CoderAgent(config, tools)

    @staticmethod
    def create_reporter(config: AgentConfig) -> "ReporterAgent":
        """創建報告者智能體"""
        from .reporter_agent import ReporterAgent

        config.role = AgentRole.REPORTER
        return ReporterAgent(config)

    @staticmethod
    def create_human_proxy(config: AgentConfig) -> BaseResearchAgent:
        """創建人機互動智能體"""
        config.role = AgentRole.HUMAN_PROXY
        return create_research_agent(config, agent_type="user_proxy")
