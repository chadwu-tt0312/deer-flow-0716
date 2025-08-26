# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
基礎智能體模組

提供所有 AutoGen 智能體的基礎類別和通用功能。
"""

from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime

try:
    from autogen_agentchat.agents import BaseChatAgent, UserProxyAgent, AssistantAgent
    from autogen_agentchat.teams import BaseGroupChat

    # 使用 BaseGroupChat 作為 GroupChatManager 的替代
    GroupChatManager = BaseGroupChat
except ImportError:
    pass


from ..config.agent_config import AgentConfig, AgentRole
from src.logging import get_logger

logger = get_logger(__name__)


class BaseResearchAgent(BaseChatAgent):
    """
    研究系統基礎智能體類別

    繼承自 AutoGen 的 BaseChatAgent，提供 DeerFlow 特定功能和統一的基礎架構。
    這個類別提供所有研究智能體的通用功能，包括工具管理、角色行為、狀態管理等。
    """

    def __init__(self, config: AgentConfig, tools: Optional[List[Callable]] = None, **kwargs):
        """
        初始化基礎研究智能體

        Args:
            config: 智能體配置
            tools: 可用工具列表
            **kwargs: 其他 AutoGen 參數
        """
        # 設置基本屬性
        self.config = config
        self.role = config.role
        self.tools = tools or []
        self._name = config.name  # 使用內部變數

        # 初始化工具映射
        self._function_map = {}
        self._tool_descriptions = {}

        # 狀態管理
        self._conversation_history = []
        self._task_state = {}
        self._performance_metrics = {
            "messages_processed": 0,
            "tools_used": 0,
            "errors_encountered": 0,
        }

        # 準備 AutoGen 配置
        autogen_config = config.to_autogen_config()
        autogen_config.update(kwargs)

        # 註冊工具
        if self.tools:
            self._register_tools()

        try:
            # BaseChatAgent 只需要 name 和 description
            super().__init__(name=config.name, description=config.description)
            logger.info(f"成功初始化智能體: {config.name} (角色: {config.role.value})")
        except Exception as e:
            logger.error(f"初始化智能體失敗: {config.name}, 錯誤: {e}")
            raise

        # 設定角色特定的行為
        self._setup_role_specific_behavior()

    @property
    def name(self) -> str:
        """獲取智能體名稱"""
        return self._name

    @name.setter
    def name(self, value: str):
        """設置智能體名稱"""
        self._name = value

    @property
    def description(self) -> str:
        """獲取智能體描述"""
        return getattr(self, "_description", "")

    @description.setter
    def description(self, value: str):
        """設置智能體描述"""
        self._description = value

    def _register_tools(self):
        """註冊工具到智能體"""
        for tool in self.tools:
            if hasattr(tool, "__name__"):
                tool_name = tool.__name__
                self._function_map[tool_name] = tool

                # 獲取工具描述
                if hasattr(tool, "__doc__") and tool.__doc__:
                    self._tool_descriptions[tool_name] = tool.__doc__.strip()
                else:
                    self._tool_descriptions[tool_name] = f"Tool: {tool_name}"

                logger.debug(f"註冊工具: {tool_name}")

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
        self._task_state["coordination_mode"] = True
        self._task_state["can_delegate"] = True

    def _setup_planner_behavior(self):
        """設定計劃者行為"""
        self.description = "負責分析需求並制定詳細的執行計劃"
        self._task_state["planning_mode"] = True
        self._task_state["can_create_plans"] = True

    def _setup_researcher_behavior(self):
        """設定研究者行為"""
        self.description = "負責進行網路搜尋和資訊收集"
        self._task_state["research_mode"] = True
        self._task_state["can_search"] = True

    def _setup_coder_behavior(self):
        """設定程式設計師行為"""
        self.description = "負責程式碼分析、執行和技術處理"
        self._task_state["coding_mode"] = True
        self._task_state["can_execute_code"] = True

    def _setup_reporter_behavior(self):
        """設定報告者行為"""
        self.description = "負責整理資訊並生成最終報告"
        self._task_state["reporting_mode"] = True
        self._task_state["can_generate_reports"] = True

    def add_tool(self, tool: Callable):
        """添加工具到智能體"""
        if tool not in self.tools:
            self.tools.append(tool)
            if hasattr(tool, "__name__"):
                tool_name = tool.__name__
                self._function_map[tool_name] = tool

                # 更新工具描述
                if hasattr(tool, "__doc__") and tool.__doc__:
                    self._tool_descriptions[tool_name] = tool.__doc__.strip()
                else:
                    self._tool_descriptions[tool_name] = f"Tool: {tool_name}"

                logger.info(f"為智能體 {self.name} 添加工具: {tool_name}")

    def remove_tool(self, tool_name: str):
        """移除智能體的工具"""
        self.tools = [t for t in self.tools if getattr(t, "__name__", str(t)) != tool_name]
        if tool_name in self._function_map:
            del self._function_map[tool_name]
        if tool_name in self._tool_descriptions:
            del self._tool_descriptions[tool_name]
        logger.info(f"從智能體 {self.name} 移除工具: {tool_name}")

    def get_tools_info(self) -> Dict[str, str]:
        """取得工具資訊"""
        return self._tool_descriptions.copy()

    def can_handle_task(self, task_type: str) -> bool:
        """檢查智能體是否能處理特定類型的任務"""
        task_capabilities = {
            "coordination": self.role == AgentRole.COORDINATOR,
            "planning": self.role == AgentRole.PLANNER,
            "research": self.role == AgentRole.RESEARCHER,
            "coding": self.role == AgentRole.CODER,
            "reporting": self.role == AgentRole.REPORTER,
        }
        return task_capabilities.get(task_type, False)

    def get_role_info(self) -> Dict[str, Any]:
        """取得角色資訊"""
        return {
            "name": getattr(self, "name", self.config.name),
            "role": self.role.value,
            "description": getattr(self, "description", self.config.description),
            "tools": list(self._function_map.keys()),
            "config": self.config,
            "capabilities": self._task_state,
            "performance": self._performance_metrics,
        }

    def update_task_state(self, updates: Dict[str, Any]):
        """更新任務狀態"""
        self._task_state.update(updates)
        logger.debug(f"智能體 {self.name} 任務狀態更新: {updates}")

    def get_task_state(self) -> Dict[str, Any]:
        """取得當前任務狀態"""
        return self._task_state.copy()

    def add_to_conversation_history(self, message: Dict[str, Any]):
        """添加消息到對話歷史"""
        self._conversation_history.append(
            {"timestamp": datetime.now().isoformat(), "message": message, "agent": self.name}
        )
        self._performance_metrics["messages_processed"] += 1

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """取得對話歷史"""
        return self._conversation_history.copy()

    def record_tool_usage(self, tool_name: str, success: bool = True):
        """記錄工具使用情況"""
        self._performance_metrics["tools_used"] += 1
        if not success:
            self._performance_metrics["errors_encountered"] += 1

        logger.debug(f"智能體 {self.name} 使用工具: {tool_name}, 成功: {success}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """取得性能指標"""
        return self._performance_metrics.copy()

    def reset_performance_metrics(self):
        """重置性能指標"""
        self._performance_metrics = {
            "messages_processed": 0,
            "tools_used": 0,
            "errors_encountered": 0,
        }

    async def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        處理用戶輸入的統一接口

        Args:
            user_input: 用戶輸入的內容

        Returns:
            Dict[str, Any]: 包含回應和狀態的字典
        """
        try:
            # 記錄消息
            self.add_to_conversation_history({"type": "user_input", "content": user_input})

            # 分析輸入
            analysis = self._analyze_input(user_input)

            # 生成回應
            response = await self._generate_response(user_input, analysis)

            # 記錄回應
            self.add_to_conversation_history(
                {"type": "agent_response", "content": response, "analysis": analysis}
            )

            return {
                "response": response,
                "analysis": analysis,
                "status": "success",
                "agent_name": self.name,
                "role": self.role.value,
            }

        except Exception as e:
            self._performance_metrics["errors_encountered"] += 1
            logger.error(f"處理用戶輸入失敗: {e}")

            return {
                "response": f"抱歉，處理您的請求時發生錯誤：{str(e)}",
                "status": "error",
                "error": str(e),
                "agent_name": self.name,
                "role": self.role.value,
            }

    def _analyze_input(self, user_input: str) -> Dict[str, Any]:
        """分析用戶輸入"""
        return {
            "input_length": len(user_input),
            "contains_questions": "?" in user_input,
            "contains_code": any(
                keyword in user_input.lower() for keyword in ["code", "function", "class", "def"]
            ),
            "urgency_level": "urgent"
            if any(word in user_input.lower() for word in ["urgent", "asap", "immediately"])
            else "normal",
            "complexity": "high"
            if len(user_input.split()) > 20
            else "medium"
            if len(user_input.split()) > 10
            else "low",
        }

    async def _generate_response(self, user_input: str, analysis: Dict[str, Any]) -> str:
        """生成回應"""
        # 根據角色和輸入分析生成適當的回應
        if self.role == AgentRole.COORDINATOR:
            return self._generate_coordinator_response(user_input, analysis)
        elif self.role == AgentRole.PLANNER:
            return self._generate_planner_response(user_input, analysis)
        elif self.role == AgentRole.RESEARCHER:
            return self._generate_researcher_response(user_input, analysis)
        elif self.role == AgentRole.CODER:
            return self._generate_coder_response(user_input, analysis)
        elif self.role == AgentRole.REPORTER:
            return self._generate_reporter_response(user_input, analysis)
        else:
            return f"我已經收到您的請求：{user_input}。我正在分析如何最好地協助您。"

    def _generate_coordinator_response(self, user_input: str, analysis: Dict[str, Any]) -> str:
        """生成協調者回應"""
        return f"我已經收到您的請求「{user_input}」。作為協調者，我會分析任務需求並安排適當的團隊成員來處理。任務複雜度評估：{analysis['complexity']}"

    def _generate_planner_response(self, user_input: str, analysis: Dict[str, Any]) -> str:
        """生成計劃者回應"""
        return f"我已經收到您的請求「{user_input}」。作為計劃者，我會制定詳細的執行計劃。根據分析，這是一個{analysis['complexity']}複雜度的任務。"

    def _generate_researcher_response(self, user_input: str, analysis: Dict[str, Any]) -> str:
        """生成研究者回應"""
        return f"我已經收到您的研究請求「{user_input}」。作為研究者，我會進行深入的資訊收集和分析。任務複雜度：{analysis['complexity']}"

    def _generate_coder_response(self, user_input: str, analysis: Dict[str, Any]) -> str:
        """生成程式設計師回應"""
        if analysis["contains_code"]:
            return f"我已經收到您的程式碼相關請求「{user_input}」。作為程式設計師，我會仔細分析並提供技術解決方案。"
        else:
            return f"我已經收到您的請求「{user_input}」。作為程式設計師，我可以協助您處理各種技術問題和程式碼相關任務。"

    def _generate_reporter_response(self, user_input: str, analysis: Dict[str, Any]) -> str:
        """生成報告者回應"""
        return f"我已經收到您的請求「{user_input}」。作為報告者，我會整理資訊並生成清晰的報告。任務複雜度：{analysis['complexity']}"

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
            # 記錄發送的消息
            self.add_to_conversation_history(
                {
                    "type": "sent_message",
                    "recipient": recipient.name,
                    "content": message,
                    "request_reply": request_reply,
                }
            )

            # 使用 BaseChatAgent 的 on_messages 方法
            if hasattr(self, "on_messages"):
                # 轉換為 TextMessage 格式
                from autogen_agentchat.messages import TextMessage

                text_message = TextMessage(content=str(message), source=self.name)
                return await self.on_messages([text_message])
            else:
                # 降級為同步方法
                return self.send_message(
                    message=message, recipient=recipient, request_reply=request_reply, silent=silent
                )
        except Exception as e:
            logger.error(f"發送消息失敗: {self.name} -> {recipient.name}, 錯誤: {e}")
            raise

    # 實現 BaseChatAgent 的抽象方法
    async def on_messages(self, messages, cancellation_token=None):
        """處理消息的抽象方法實現"""
        from autogen_agentchat.messages import TextMessage

        # 提取消息內容
        if messages and hasattr(messages[0], "content"):
            user_input = messages[0].content
        else:
            user_input = str(messages[0]) if messages else ""

        # 使用我們的 process_user_input 方法
        result = await self.process_user_input(user_input)

        # 返回 TextMessage
        return TextMessage(content=result["response"], source=self.name)

    async def on_reset(self):
        """處理重置事件的抽象方法實現"""
        self.reset_performance_metrics()
        self._conversation_history.clear()
        self._task_state.clear()
        logger.info(f"智能體 {self.name} 已重置")

    @property
    def produced_message_types(self):
        """返回此智能體產生的消息類型的抽象方法實現"""
        from autogen_agentchat.messages import TextMessage

        return [TextMessage]


class UserProxyResearchAgent(BaseResearchAgent):
    """
    用戶代理研究智能體

    用於人機互動和工作流控制。
    """

    def __init__(self, config: AgentConfig, **kwargs):
        # UserProxyAgent 的特定配置
        kwargs.setdefault("human_input_mode", "TERMINATE")
        kwargs.setdefault("max_consecutive_auto_reply", 0)

        super().__init__(config, **kwargs)

        logger.info(f"初始化用戶代理智能體: {config.name}")


class AssistantResearchAgent(BaseResearchAgent):
    """
    助手研究智能體

    用於各種專業任務執行。
    """

    def __init__(self, config: AgentConfig, tools: Optional[List[Callable]] = None, **kwargs):
        super().__init__(config, tools, **kwargs)

        logger.info(f"init AssistantResearchAgent: {config.name}")


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
        from ..adapters.llm_adapter import create_chat_client

        config.role = AgentRole.COORDINATOR
        return CoordinatorAgent(
            name=config.name,
            model_client=create_chat_client(config.role),
            description=config.system_message,
        )

    @staticmethod
    def create_planner(config: AgentConfig) -> "PlannerAgent":
        """創建計劃者智能體"""
        from .planner_agent import PlannerAgent
        from ..adapters.llm_adapter import create_chat_client

        config.role = AgentRole.PLANNER
        return PlannerAgent(
            name=config.name,
            model_client=create_chat_client(config.role),
            description=config.system_message,
        )

    @staticmethod
    def create_researcher(config: AgentConfig, tools: List[Callable] = None) -> "ResearcherAgent":
        """創建研究者智能體"""
        from .researcher_agent import ResearcherAgent
        from ..adapters.llm_adapter import create_chat_client

        config.role = AgentRole.RESEARCHER
        return ResearcherAgent(
            name=config.name,
            model_client=create_chat_client(config.role),
            description=config.system_message,
            tools=tools,
        )

    @staticmethod
    def create_coder(config: AgentConfig, tools: List[Callable] = None) -> "CoderAgent":
        """創建程式設計師智能體"""
        from .coder_agent import CoderAgent
        from ..adapters.llm_adapter import create_chat_client

        config.role = AgentRole.CODER
        return CoderAgent(
            name=config.name,
            model_client=create_chat_client(config.role),
            description=config.system_message,
            tools=tools,
        )

    @staticmethod
    def create_reporter(config: AgentConfig) -> "ReporterAgent":
        """創建報告者智能體"""
        from .reporter_agent import ReporterAgent
        from ..adapters.llm_adapter import create_chat_client

        config.role = AgentRole.REPORTER
        return ReporterAgent(
            name=config.name,
            model_client=create_chat_client(config.role),
            description=config.system_message,
        )

    @staticmethod
    def create_human_proxy(config: AgentConfig) -> BaseResearchAgent:
        """創建人機互動智能體"""
        config.role = AgentRole.HUMAN_PROXY
        return create_research_agent(config, agent_type="user_proxy")
