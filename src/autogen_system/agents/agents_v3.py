# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen Agent V3 實現

基於 AutoGen 框架的第三版智能體實現，取代原有的 LangGraph 節點。
使用 AutoGen 原生的 AssistantAgent 作為基底，整合現有的工具和模型配置。
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

# AutoGen 核心導入
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient

# 專案內部導入
from src.config.agents import AGENT_LLM_MAP, LLMType
from src.deerflow_logging import get_thread_logger


def _get_logger():
    """獲取當前 thread 的 logger"""
    try:
        return get_thread_logger()
    except RuntimeError:
        # 如果沒有設定 thread context，使用簡單的 logger
        from src.deerflow_logging import get_simple_logger

        return get_simple_logger(__name__)


from src.autogen_system.adapters.llm_adapter import create_autogen_model_client
from src.autogen_system.tools.tools_integration import get_tools_for_agent_type
# 暫時註釋掉 message_framework 的引用，因為它可能已被刪除
# from src.autogen_system.controllers.message_framework import (
#     MessageType,
#     StepType,
#     WorkflowStep,
#     PlanMessage,
#     ResearchResultMessage,
#     CodeExecutionMessage,
#     ReportMessage,
#     create_coordination_message,
#     create_error_message,
# )

# 模板系統導入
try:
    from src.prompts.template import apply_prompt_template
    from src.config.configuration import Configuration
except ImportError:
    # 如果模板系統不可用，定義一個簡單的 fallback 函數
    def apply_prompt_template(template_name: str, state: Dict[str, Any]) -> List[Dict[str, str]]:
        _get_logger().warning(f"模板系統不可用，無法載入 {template_name} 模板")
        return []


# logger 已移除，使用 _get_logger() 函數


class BaseAgentV3:
    """智能體 V3 基類"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        self.name = name
        self.description = description
        self.system_message = system_message
        self._model_client = model_client
        self.tools = tools or []

        # 創建 AutoGen AssistantAgent
        # AutoGen 支持 tools 參數，可以傳遞工具列表
        try:
            self._agent = AssistantAgent(
                name=name,
                model_client=model_client,
                tools=self.tools,  # 啟用工具參數
                description=description,
                system_message=system_message,
            )
        except Exception as e:
            _get_logger().warning(f"AssistantAgent 初始化失敗（嘗試不帶 description）: {e}")
            # 如果帶 description 失敗，嘗試最簡化的初始化
            self._agent = AssistantAgent(
                name=name,
                model_client=model_client,
                system_message=system_message,
            )

        _get_logger().info(f"智能體 {name} 初始化完成，工具數量: {len(self.tools)}")
        # 紀錄所有工具名稱
        for tool in self.tools:
            tool_name = getattr(tool, "name", getattr(tool, "__name__", str(tool)))
            _get_logger().info(f"工具名稱: {tool_name}")

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """通用工廠方法：創建智能體實例"""
        # 從 kwargs 獲取 agent_key，用於識別不同的智能體配置
        agent_key = kwargs.get("agent_key")
        if not agent_key:
            raise ValueError("必須提供 agent_key 參數")

        agent_config = config.get("agents", {}).get(agent_key, {})
        role = agent_config.get("role", agent_key.replace("_v3", ""))
        _get_logger().info(f"role: {role}")

        # 獲取基本配置
        name = agent_config.get("name", cls.__name__)
        description = agent_config.get("description", f"負責{role}相關任務")

        # 嘗試讀取模板
        system_message = None
        try:
            template_state = {
                "messages": [],
                "locale": "zh-TW",  # 預設語言
                "research_topic": "",
                "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
            }

            # 根據角色應用對應模板
            template_messages = apply_prompt_template(role, template_state)
            if template_messages and len(template_messages) > 0:
                system_message = template_messages[0].get("content", "")
                _get_logger().info(f"成功載入{role}模板")
            else:
                raise ValueError("模板應用失敗")

        except Exception as e:
            _get_logger().warning(f"載入{role}模板失敗，使用配置檔案中的系統訊息: {e}")
            system_message = agent_config.get(
                "system_message", f"你是{role}智能體，負責{role}相關任務。"
            )

        # 獲取 LLM 客戶端（根據智能體類型選擇合適的 LLM）
        llm_type = cls._get_llm_type(role)
        model_client = create_autogen_model_client(llm_type, config)

        # 獲取工具（根據角色獲取對應工具）
        tools = await cls._get_tools_for_role(role)

        return cls(name, description, system_message, model_client, tools)

    @classmethod
    def _get_llm_type(cls, role: str) -> str:
        """根據角色獲取合適的 LLM 類型"""
        return AGENT_LLM_MAP.get(role, "basic")

    @classmethod
    async def _get_tools_for_role(cls, role: str) -> List[Callable]:
        """根據角色獲取對應的工具"""
        # 預設工具映射
        role_tools_map = {
            "coordinator": [],  # 協調者不需要特定工具
            "planner": [],  # 規劃者通常不需要特定工具
            "researcher": ["web_search", "crawl_website"],  # 研究者需要搜尋和爬蟲工具
            "coder": ["python_repl"],  # 程式設計師需要程式碼執行工具
            "reporter": [],  # 報告者通常不需要特定工具
            "background_investigator": [
                "web_search",
                "crawl_website",
            ],  # 背景調查者需要搜尋和爬蟲工具
            "human_feedbacker": [],  # 人類反饋智能體不需要特定工具
        }

        # 獲取工具名稱列表
        tool_names = role_tools_map.get(role, [])

        # 從全局工具整合器獲取實際工具實例
        if tool_names:
            try:
                from src.autogen_system.tools.tools_integration import global_tools_integrator

                # 確保工具整合器已初始化
                if not global_tools_integrator.initialized:
                    await global_tools_integrator.initialize_tools()

                # 獲取工具實例
                tools = []
                for tool_name in tool_names:
                    tool = global_tools_integrator.get_tool_by_name(tool_name)
                    if tool:
                        tools.append(tool)

                return tools

            except Exception as e:
                _get_logger().error(f"獲取工具失敗: {e}")
                return []

        return []

    def get_agent(self) -> AssistantAgent:
        """獲取底層的 AutoGen Agent"""
        return self._agent

    async def process_message(self, message: str, **kwargs) -> str:
        """處理訊息（子類可覆寫以實現特定邏輯）"""
        # 默認直接使用 AutoGen Agent 處理
        response = await self._agent.on_messages(message, cancellation_token=None)
        return response.content if hasattr(response, "content") else str(response)


class CoordinatorAgentV3(BaseAgentV3):
    """協調者智能體 V3"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        super().__init__(name, description, system_message, model_client, tools)

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """創建協調者智能體"""
        return await super().create(config, agent_key="coordinator_v3")


class PlannerAgentV3(BaseAgentV3):
    """規劃者智能體 V3"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        super().__init__(name, description, system_message, model_client, tools)

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """創建規劃者智能體"""
        return await super().create(config, agent_key="planner_v3")


class ResearcherAgentV3(BaseAgentV3):
    """研究者智能體 V3"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        super().__init__(name, description, system_message, model_client, tools)

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """創建研究者智能體"""
        return await super().create(config, agent_key="researcher_v3")


class CoderAgentV3(BaseAgentV3):
    """程式設計師智能體 V3"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        super().__init__(name, description, system_message, model_client, tools)

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """創建程式設計師智能體"""
        return await super().create(config, agent_key="coder_v3")


class ReporterAgentV3(BaseAgentV3):
    """報告者智能體 V3"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        super().__init__(name, description, system_message, model_client, tools)

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """創建報告者智能體"""
        return await super().create(config, agent_key="reporter_v3")


class BackgroundInvestigatorAgentV3(BaseAgentV3):
    """背景調查者智能體 V3"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        super().__init__(name, description, system_message, model_client, tools)

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """創建背景調查者智能體"""
        return await super().create(config, agent_key="background_investigator_v3")


class HumanFeedbackerAgentV3(BaseAgentV3):
    """人類反饋智能體 V3"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        super().__init__(name, description, system_message, model_client, tools)

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """創建人類反饋智能體"""
        return await super().create(config, agent_key="human_feedbacker_v3")


# 便利函數
async def create_all_agents_v3(config: Dict[str, Any]) -> Dict[str, BaseAgentV3]:
    """
    創建所有 V3 智能體

    Args:
        config: 配置字典

    Returns:
        Dict[str, BaseAgentV3]: 智能體字典
    """
    _get_logger().info("開始創建所有 V3 智能體...")

    agents = {}

    # 創建各個智能體
    agents["coordinator"] = await CoordinatorAgentV3.create(config)
    agents["planner"] = await PlannerAgentV3.create(config)
    agents["researcher"] = await ResearcherAgentV3.create(config)
    agents["coder"] = await CoderAgentV3.create(config)
    agents["reporter"] = await ReporterAgentV3.create(config)
    agents["background_investigator"] = await BackgroundInvestigatorAgentV3.create(config)
    agents["human_feedbacker"] = await HumanFeedbackerAgentV3.create(config)

    _get_logger().info(f"V3 智能體創建完成，共 {len(agents)} 個")
    return agents


# def get_agent_list_for_selector(agents: Dict[str, BaseAgentV3]) -> List[AssistantAgent]:
#     """
#     獲取用於 SelectorGroupChat 的智能體列表

#     Args:
#         agents: 智能體字典

#     Returns:
#         List[AssistantAgent]: AutoGen AssistantAgent 列表
#     """
#     return [agent.get_agent() for agent in agents.values()]
