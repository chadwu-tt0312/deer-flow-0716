# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
協調者智能體 - AutoGen 框架版本

基於真正的 AutoGen 框架實現，參考 coordinator_node() 的功能。
使用 autogen_core 的消息格式和 ChatCompletionClient。
"""

import json
import re
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime

# AutoGen 核心組件
from autogen_core import CancellationToken, FunctionCall
from autogen_core.models import (
    ChatCompletionClient,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    LLMMessage,
)

# AutoGen AgentChat 基礎類
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage

# 項目內部導入
import logging
from ..config.agent_config import AgentRole

# 嘗試導入線程管理功能，如果失敗則使用標準 logging
try:
    from src.logging import (
        setup_thread_logging,
        set_thread_context,
        get_current_thread_id,
        get_current_thread_logger,
    )

    HAS_THREAD_LOGGING = True
except ImportError:
    HAS_THREAD_LOGGING = False

# 嘗試導入提示模板功能
try:
    from src.prompts.template import apply_prompt_template
    from src.config.configuration import Configuration

    HAS_PROMPT_TEMPLATES = True
except ImportError:
    HAS_PROMPT_TEMPLATES = False

# 導入 Command 系統
try:
    from ..core.command import (
        AutoGenCommand,
        create_handoff_command,
        create_completion_command,
        parse_flow_control_to_command,
    )

    HAS_COMMAND_SYSTEM = True
except ImportError:
    HAS_COMMAND_SYSTEM = False

logger = logging.getLogger(__name__)


# 工具定義
HANDOFF_TO_PLANNER_TOOL = {
    "type": "function",
    "function": {
        "name": "handoff_to_planner",
        "description": "Handoff to planner agent to do plan.",
        "parameters": {
            "type": "object",
            "properties": {
                "research_topic": {
                    "type": "string",
                    "description": "The topic of the research task to be handed off.",
                },
                "locale": {
                    "type": "string",
                    "description": "The user's detected language locale (e.g., en-US, zh-CN).",
                },
            },
            "required": ["research_topic", "locale"],
        },
    },
}


class CoordinatorAgent(BaseChatAgent):
    """
    協調者智能體 - 使用真正的 AutoGen 框架

    功能對標 coordinator_node()：
    1. 線程上下文管理
    2. 動態提示模板應用
    3. 真正的工具綁定和 LLM 調用
    4. 智能決策邏輯
    5. 狀態更新和流程控制
    6. 背景調查決策
    """

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        description: str = "協調者智能體 - 處理用戶輸入並決定工作流程",
        system_messages: Optional[List[SystemMessage]] = None,
    ):
        """
        初始化協調者智能體

        Args:
            name: 智能體名稱
            model_client: ChatCompletionClient 實例
            description: 智能體描述
            system_messages: 系統消息列表
        """
        super().__init__(name=name, description=description)

        self._model_client = model_client
        self._system_messages = system_messages or []
        self._chat_history: List[LLMMessage] = []

        # 線程管理
        self._current_thread_id: Optional[str] = None
        self._thread_logger = None

        # 狀態管理
        self._state: Dict[str, Any] = {}
        self._configuration: Optional[Any] = None

        # 添加角色屬性（兼容 BaseResearchAgent 接口）
        self.role = AgentRole.COORDINATOR  # "coordinator"

        logger.info(f"CoordinatorAgent 初始化完成: {name}")

    def _setup_thread_context(self, thread_id: str):
        """設置線程上下文和日誌

        參考 coordinator_node 的實現模式：
        1. 獲取 thread_id
        2. 設置線程特定日誌系統
        3. 設置線程上下文
        4. 記錄日誌
        """
        self._current_thread_id = thread_id

        if HAS_THREAD_LOGGING:
            try:
                # 使用真正的線程特定日誌系統（與 coordinator_node 一致）
                self._thread_logger = setup_thread_logging(thread_id)
                set_thread_context(thread_id)

                if self._thread_logger:
                    self._thread_logger.info("CoordinatorAgent talking.")
                else:
                    logger.info("CoordinatorAgent talking.")

            except Exception as e:
                logger.warning(f"線程日誌設置失敗，使用標準 logger: {e}")
                self._thread_logger = logger
                logger.info("CoordinatorAgent talking.")
        else:
            # 降級到標準 logger
            self._thread_logger = logger
            logger.info("CoordinatorAgent talking.")

    def _get_thread_id_from_context(
        self, cancellation_token: Optional[CancellationToken] = None
    ) -> str:
        """
        從上下文獲取線程 ID

        對應 coordinator_node 中的 get_thread_id_from_config() 實現
        """
        # 1. 嘗試從已設置的線程 ID 獲取
        if self._current_thread_id:
            return self._current_thread_id

        # 2. 嘗試從現有線程上下文獲取
        if HAS_THREAD_LOGGING:
            try:
                current_thread_id = get_current_thread_id()
                if current_thread_id:
                    return current_thread_id
            except Exception:
                pass

        # 3. 嘗試從 cancellation_token 獲取（AutoGen 特定）
        if cancellation_token:
            # TODO: 實際實現需要了解 AutoGen CancellationToken 的內部結構
            # 現在先檢查是否有相關屬性
            if hasattr(cancellation_token, "context"):
                context = getattr(cancellation_token, "context", None)
                if context and hasattr(context, "thread_id"):
                    return getattr(context, "thread_id")

        # 4. 生成新的線程 ID（降級方案）
        thread_id = f"autogen_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        logger.debug(f"生成新線程 ID: {thread_id}")
        return thread_id

    def _apply_dynamic_system_message(self, state: Dict[str, Any]) -> List[SystemMessage]:
        """
        應用動態提示模板，類似 coordinator_node 中的 apply_prompt_template()
        """
        if HAS_PROMPT_TEMPLATES:
            try:
                # 使用真正的 apply_prompt_template 功能

                # 轉換狀態為 apply_prompt_template 所需的格式
                template_state = {
                    "messages": state.get("messages", []),
                    "locale": state.get("locale", "en-US"),
                    "research_topic": state.get("research_topic", ""),
                    **state,  # 包含其他狀態變量
                }

                if self._thread_logger:
                    self._thread_logger.debug(f"模板狀態: {template_state}")
                    self._thread_logger.debug(f"配置對象: {type(self._configuration)}")

                # 應用協調者模板
                if self._configuration and HAS_PROMPT_TEMPLATES:
                    # 檢查配置類型，如果是 dict 則轉換為 Configuration 實例
                    if isinstance(self._configuration, dict):
                        try:
                            from src.config.configuration import Configuration

                            config_obj = Configuration.from_runnable_config(
                                {"configurable": self._configuration}
                            )
                            template_messages = apply_prompt_template(
                                "coordinator", template_state, config_obj
                            )
                        except Exception as config_error:
                            if self._thread_logger:
                                self._thread_logger.warning(
                                    f"配置轉換失敗，使用無配置版本: {config_error}"
                                )
                            template_messages = apply_prompt_template("coordinator", template_state)
                    else:
                        # 已經是 Configuration 實例
                        template_messages = apply_prompt_template(
                            "coordinator", template_state, self._configuration
                        )
                else:
                    template_messages = apply_prompt_template("coordinator", template_state)

                if self._thread_logger:
                    self._thread_logger.debug(f"模板消息: {template_messages}")

                # 轉換為 AutoGen SystemMessage 格式
                system_messages = []
                for msg in template_messages:
                    if isinstance(msg, dict) and msg.get("role") == "system":
                        system_messages.append(SystemMessage(content=msg["content"]))

                if system_messages:
                    if self._thread_logger:
                        self._thread_logger.info("成功應用動態提示模板")
                    return system_messages

            except Exception as e:
                error_details = f"動態提示模板應用失敗: {type(e).__name__}: {str(e)}"
                if self._thread_logger:
                    self._thread_logger.warning(error_details)
                    self._thread_logger.debug(f"失敗詳情: {e}")
                else:
                    logger.warning(error_details)
                    logger.debug(f"失敗詳情: {e}")

    #         # 降級到預設系統消息
    #         if self._thread_logger:
    #             self._thread_logger.info("使用預設系統提示")
    #         else:
    #             logger.info("使用預設系統提示")

    #         default_content = """你是 DeerFlow，一個友善的AI助手。你專門處理問候和閒聊，同時將研究任務交給專門的計劃者。

    # 請分析用戶輸入：
    # - 如果是簡單問候或閒聊，直接回應
    # - 如果是研究請求，使用 handoff_to_planner 工具交給計劃者
    # - 始終以與用戶相同的語言回應"""

    #         return [SystemMessage(content=default_content)]

    def _detect_locale(self, text: str) -> str:
        """檢測輸入文本的語言"""
        chinese_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        total_chars = len([char for char in text if char.isalpha()])

        if total_chars > 0 and chinese_chars / total_chars > 0.3:
            return "zh-TW"

        return "en-US"

    def _extract_research_topic(self, user_input: str) -> str:
        """提取研究主題"""
        return user_input.strip()

    def _classify_request(self, user_input: str) -> str:
        """分類用戶請求"""
        user_input_lower = user_input.lower().strip()

        # 問候和閒聊 - 更精確的匹配
        simple_greetings = ["你好", "hi", "hello", "嗨", "早安", "good morning"]

        # 檢查是否為單純問候（不包含其他內容）
        is_simple_greeting = any(
            user_input_lower == greeting
            or user_input_lower.startswith(greeting + " ")
            and len(user_input_lower.split()) <= 3
            for greeting in simple_greetings
        )

        # 額外的問候模式
        greeting_patterns = ["how are you", "你好嗎", "what's your name", "你叫什麼"]
        is_greeting_question = any(pattern in user_input_lower for pattern in greeting_patterns)

        if is_simple_greeting or is_greeting_question:
            return "greeting"

        # 不當請求
        harmful_patterns = [
            "system prompt",
            "reveal",
            "bypass",
            "hack",
            "jailbreak",
            "ignore instructions",
        ]
        if any(pattern in user_input_lower for pattern in harmful_patterns):
            return "harmful"

        # 其他都視為研究請求
        return "research"

    def _generate_direct_response(self, request_type: str, locale: str) -> str:
        """生成直接回應（問候或拒絕）"""
        if request_type == "greeting":
            if locale == "zh-TW":
                return "你好！我是 DeerFlow，很高興為你服務。我可以幫助你進行各種研究和資訊查詢。請告訴我你想了解什麼？"
            else:
                return "Hello! I'm DeerFlow, nice to meet you. I can help you with various research and information queries. What would you like to know?"

        elif request_type == "harmful":
            if locale == "zh-TW":
                return "抱歉，我不能協助處理這類請求。讓我們聊聊我可以幫助你的其他事情吧，比如研究問題或資訊查詢。"
            else:
                return "I'm sorry, but I can't assist with that type of request. Let's talk about other things I can help you with, like research questions or information queries."

        return "我不確定如何回應這個請求。"

    def _process_tool_calls(
        self, response_content: Any, detected_locale: str = "en-US"
    ) -> Dict[str, Any]:
        """
        處理 LLM 回應中的工具調用

        類似 coordinator_node 中檢查 response.tool_calls 的邏輯

        Args:
            response_content: LLM 回應內容
            detected_locale: 檢測到的語言環境，優先使用此值
        """
        result = {
            "has_tool_calls": False,
            "action": "direct_response",
            "research_topic": "",
            "locale": detected_locale,  # 優先使用檢測到的 locale
            "goto": "__end__",
        }

        # 檢查是否為工具調用列表
        if isinstance(response_content, list):
            for item in response_content:
                if isinstance(item, FunctionCall):
                    if item.name == "handoff_to_planner":
                        try:
                            args = json.loads(item.arguments)

                            # 優先使用檢測到的 locale，只有在檢測失敗時才使用 LLM 返回的
                            llm_locale = args.get("locale", "en-US")
                            final_locale = (
                                detected_locale if detected_locale != "en-US" else llm_locale
                            )

                            result.update(
                                {
                                    "has_tool_calls": True,
                                    "action": "handoff_to_planner",
                                    "research_topic": args.get("research_topic", ""),
                                    "locale": final_locale,  # 使用最終確定的 locale
                                    "goto": "planner",
                                }
                            )

                            if self._thread_logger:
                                self._thread_logger.info(f"工具調用成功: {item.name}, args: {args}")
                                self._thread_logger.debug(
                                    f"Locale 處理: 檢測={detected_locale}, LLM={llm_locale}, 最終={final_locale}"
                                )

                            return result

                        except json.JSONDecodeError as e:
                            if self._thread_logger:
                                self._thread_logger.error(f"工具調用參數解析失敗: {e}")

        # 沒有工具調用
        if self._thread_logger:
            self._thread_logger.warning("回應中沒有工具調用，將終止工作流執行")

        return result

    def _should_enable_background_investigation(self) -> bool:
        """
        檢查是否應啟用背景調查

        對應 coordinator_node 中的 state.get("enable_background_investigation")
        """
        # 暫時簡化 - 從狀態中獲取
        return self._state.get("enable_background_investigation", False)

    def _determine_goto_target(self, tool_result: Dict[str, Any]) -> str:
        """
        決定下一個目標節點

        實現 coordinator_node 中的條件邏輯
        """
        if not tool_result.get("has_tool_calls"):
            return "__end__"

        if tool_result.get("action") == "handoff_to_planner":
            if self._should_enable_background_investigation():
                return "background_investigator"
            else:
                return "planner"

        return "__end__"

    async def on_messages(
        self, messages: List[TextMessage], cancellation_token: Optional[CancellationToken] = None
    ) -> TextMessage:
        """
        處理輸入消息的主要方法

        這是 AutoGen 框架的標準接口，對應原來的 process_user_input()
        """
        try:
            # 獲取最新的用戶消息
            if not messages:
                return TextMessage(content="沒有收到消息", source=self.name)

            latest_message = messages[-1]
            user_input = (
                latest_message.content
                if hasattr(latest_message, "content")
                else str(latest_message)
            )

            # 設置線程上下文
            thread_id = self._get_thread_id_from_context(cancellation_token)
            self._setup_thread_context(thread_id)

            if self._thread_logger:
                self._thread_logger.info(f"CoordinatorAgent 開始處理用戶輸入: {user_input}")

            # 分析用戶輸入
            request_type = self._classify_request(user_input)
            locale = self._detect_locale(user_input)
            research_topic = self._extract_research_topic(user_input)

            # 更新狀態
            self._state.update(
                {
                    "messages": [{"role": "user", "content": user_input}],
                    "locale": locale,
                    "research_topic": research_topic,
                }
            )

            # 直接處理問候和不當請求
            if request_type in ["greeting", "harmful"]:
                response_content = self._generate_direct_response(request_type, locale)

                if self._thread_logger:
                    self._thread_logger.info(f"生成直接回應: {request_type}")

                return TextMessage(content=response_content, source=self.name)

            # 研究請求 - 使用 LLM 和工具調用
            response_data = await self._call_llm_with_tools(user_input, cancellation_token)

            return response_data

        except Exception as e:
            error_msg = f"處理用戶輸入失敗: {str(e)}"
            logger.error(error_msg)

            if self._thread_logger:
                self._thread_logger.error(error_msg)

            return TextMessage(content=f"抱歉，處理您的請求時出現錯誤：{str(e)}", source=self.name)

    async def _call_llm_with_tools(
        self, user_input: str, cancellation_token: Optional[CancellationToken] = None
    ) -> TextMessage:
        """
        使用 LLM 和工具調用處理研究請求

        對應 coordinator_node 中的 LLM 調用和工具處理邏輯
        """
        try:
            # 準備動態系統消息
            system_messages = self._apply_dynamic_system_message(self._state)

            # 準備消息列表
            messages = (
                system_messages
                + self._chat_history
                + [UserMessage(content=user_input, source="user")]
            )

            if self._thread_logger:
                self._thread_logger.info("調用 LLM API 進行協調分析...")

            # 調用 LLM with tools (類似 coordinator_node)
            response = await self._model_client.create(
                messages=messages,
                tools=[HANDOFF_TO_PLANNER_TOOL],
                cancellation_token=cancellation_token,
            )

            # 處理回應
            response_content = response.content

            if self._thread_logger:
                self._thread_logger.info("LLM API 調用成功")
                self._thread_logger.debug(f"LLM 回應: {response_content}")

            # 處理工具調用，傳入檢測到的 locale
            detected_locale = self._state.get("locale", "en-US")
            tool_result = self._process_tool_calls(response_content, detected_locale)

            # 決定下一步流程
            goto_target = self._determine_goto_target(tool_result)

            # 準備回應消息
            if tool_result["has_tool_calls"]:
                # 有工具調用，準備流程控制信息
                flow_info = {
                    "action": "handoff_to_planner",
                    "research_topic": tool_result["research_topic"],
                    "locale": tool_result["locale"],
                    "goto": goto_target,
                    "enable_background_investigation": self._should_enable_background_investigation(),
                }

                # 生成確認消息
                if tool_result["locale"] == "zh-TW":
                    confirmation = f"我了解您想要研究「{tool_result['research_topic']}」。讓我為您安排研究團隊來處理這個任務。"
                else:
                    confirmation = f'I understand you want to research "{tool_result["research_topic"]}". Let me arrange the research team to handle this task.'

                # 將流程信息附加到消息中（用於後續處理）
                response_msg = TextMessage(content=confirmation, source=self.name)

                # 將流程控制信息存儲在消息的元數據中
                if hasattr(response_msg, "metadata"):
                    response_msg.metadata = flow_info
                else:
                    # 如果沒有 metadata 屬性，將信息編碼到內容中
                    response_msg.content = (
                        f"{confirmation}\n\n[FLOW_CONTROL]{json.dumps(flow_info)}[/FLOW_CONTROL]"
                    )

                return response_msg

            else:
                # 沒有工具調用，返回 LLM 的直接回應
                if isinstance(response_content, str):
                    return TextMessage(content=response_content, source=self.name)
                else:
                    return TextMessage(content=str(response_content), source=self.name)

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.error(f"LLM API 調用失敗: {e}")

            # 不使用降級邏輯，直接拋出異常
            raise e

    def set_configuration(self, configuration: Any):
        """設置配置對象"""
        self._configuration = configuration

        if self._thread_logger:
            self._thread_logger.info(f"配置已更新: {type(configuration).__name__}")
            if configuration:
                self._thread_logger.debug(f"配置內容: {configuration}")
        else:
            logger.info(f"配置已更新: {type(configuration).__name__}")
            if configuration:
                logger.debug(f"配置內容: {configuration}")

    def diagnose_template_issues(self) -> Dict[str, Any]:
        """診斷模板相關問題"""
        diagnosis = {
            "has_thread_logging": HAS_THREAD_LOGGING,
            "has_prompt_templates": HAS_PROMPT_TEMPLATES,
            "configuration_type": type(self._configuration).__name__
            if self._configuration
            else None,
            "state_keys": list(self._state.keys()) if self._state else [],
        }

        if HAS_PROMPT_TEMPLATES:
            try:
                # 測試模板導入
                from src.prompts.template import apply_prompt_template

                diagnosis["template_import_success"] = True

                # 測試基本模板應用
                test_state = {"messages": [], "locale": "en-US", "research_topic": "test"}
                test_result = apply_prompt_template("coordinator", test_state)
                diagnosis["template_test_success"] = True
                diagnosis["template_result_type"] = type(test_result).__name__

            except Exception as e:
                diagnosis["template_import_success"] = False
                diagnosis["template_error"] = f"{type(e).__name__}: {str(e)}"

        return diagnosis

    def set_configuration_from_runnable_config(self, runnable_config: Dict[str, Any]):
        """
        從 RunnableConfig 格式設置配置

        對應 coordinator_node 中的 Configuration.from_runnable_config(config)
        """
        try:
            if HAS_PROMPT_TEMPLATES:
                # 嘗試使用真正的 Configuration 類
                from src.config.configuration import Configuration

                config = Configuration.from_runnable_config(runnable_config)
                self.set_configuration(config)

                if self._thread_logger:
                    self._thread_logger.info(f"成功創建 Configuration 實例: {type(config)}")
                else:
                    logger.info(f"成功創建 Configuration 實例: {type(config)}")

            else:
                # 降級到字典配置
                configurable = runnable_config.get("configurable", {})
                self.set_configuration(configurable)

                if self._thread_logger:
                    self._thread_logger.info("使用字典配置（降級模式）")
                else:
                    logger.info("使用字典配置（降級模式）")

        except Exception as e:
            error_msg = f"配置轉換失敗: {type(e).__name__}: {str(e)}"
            if self._thread_logger:
                self._thread_logger.warning(error_msg)
            else:
                logger.warning(error_msg)

            # 使用原始配置，但記錄警告
            self.set_configuration(runnable_config)

    def update_state(self, state_updates: Dict[str, Any]):
        """更新智能體狀態"""
        self._state.update(state_updates)

    def get_state(self) -> Dict[str, Any]:
        """獲取當前狀態"""
        return self._state.copy()

    def generate_command_from_response(self, response: TextMessage) -> Optional[AutoGenCommand]:
        """
        從回應生成 Command 對象（類似 coordinator_node 的返回值）

        Args:
            response: 智能體的回應消息

        Returns:
            AutoGenCommand 對象或 None
        """
        if not HAS_COMMAND_SYSTEM:
            return None

        try:
            # 提取流程控制信息
            flow_info = self.extract_flow_control_info(response)

            if flow_info:
                # 轉換為 Command
                command = parse_flow_control_to_command(flow_info)

                if self._thread_logger:
                    self._thread_logger.info(
                        f"生成 Command: goto={command.goto}, action={command.metadata.get('action')}"
                    )

                return command
            else:
                # 沒有流程控制信息，生成完成 Command
                return create_completion_command(
                    final_message=response.content, additional_updates={"direct_response": True}
                )

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.error(f"生成 Command 失敗: {e}")
            return None

    def extract_flow_control_info(self, message: TextMessage) -> Dict[str, Any]:
        """
        提取流程控制信息（從現有方法移動過來，便於複用）
        """
        flow_info = {}

        try:
            # 檢查是否有 metadata 屬性
            if hasattr(message, "metadata") and message.metadata:
                flow_info = message.metadata

            # 檢查內容中是否有 [FLOW_CONTROL] 標記
            elif hasattr(message, "content") and "[FLOW_CONTROL]" in message.content:
                pattern = r"\[FLOW_CONTROL\](.*?)\[/FLOW_CONTROL\]"
                matches = re.findall(pattern, message.content, re.DOTALL)

                if matches:
                    try:
                        flow_info = json.loads(matches[0])
                    except json.JSONDecodeError as e:
                        if self._thread_logger:
                            self._thread_logger.warning(f"流程控制信息解析失敗: {e}")

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.warning(f"提取流程控制信息失敗: {e}")

        return flow_info

    def reset(self):
        """重置智能體狀態"""
        self._chat_history.clear()
        self._state.clear()
        self._current_thread_id = None
        self._thread_logger = None

    # 實現 BaseChatAgent 的抽象方法
    async def on_reset(self) -> None:
        """處理重置事件"""
        self.reset()

    @property
    def produced_message_types(self) -> List[type]:
        """返回此智能體產生的消息類型"""
        return [TextMessage]

    def get_role_info(self) -> Dict[str, Any]:
        """取得角色資訊（兼容 BaseResearchAgent 接口）"""
        return {
            "name": self.name,
            "description": self.description,
            "role": "coordinator",  # 固定為協調者角色
            "tools": ["handoff_to_planner"],  # 協調者的工具
            "config": None,  # CoordinatorAgent 沒有 config 屬性
        }

    async def _analyze_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        分析用戶輸入，提取關鍵信息

        Args:
            user_input: 用戶輸入的內容

        Returns:
            Dict[str, Any]: 分析結果
        """
        try:
            # 檢測語言環境
            locale = self._detect_locale(user_input)

            # 提取研究主題
            research_topic = self._extract_research_topic(user_input)

            # 分類請求類型
            request_type = self._classify_request(user_input)

            # 判斷是否需要背景調查
            enable_background_investigation = self._should_enable_background_investigation()

            analysis_result = {
                "locale": locale,
                "research_topic": research_topic,
                "request_type": request_type,
                "enable_background_investigation": enable_background_investigation,
                "user_input_length": len(user_input),
                "analysis_timestamp": datetime.now().isoformat(),
            }

            if self._thread_logger:
                self._thread_logger.debug(f"用戶輸入分析完成: {analysis_result}")

            return analysis_result

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.error(f"用戶輸入分析失敗: {e}")
            else:
                logger.error(f"用戶輸入分析失敗: {e}")

            return {
                "locale": "zh-TW",
                "research_topic": user_input[:50] + "..." if len(user_input) > 50 else user_input,
                "request_type": "unknown",
                "enable_background_investigation": False,
                "error": str(e),
            }

    async def _generate_coordination_response(
        self, user_input: str, analysis_result: Dict[str, Any]
    ) -> str:
        """
        生成協調回應

        Args:
            user_input: 用戶輸入的內容
            analysis_result: 分析結果

        Returns:
            str: 協調回應
        """
        try:
            locale = analysis_result.get("locale", "zh-TW")
            request_type = analysis_result.get("request_type", "unknown")
            research_topic = analysis_result.get("research_topic", "")

            # 檢查是否是簡單請求，可以直接回應
            if request_type in ["greeting", "help", "status"]:
                return self._generate_direct_response(request_type, locale)

            # 對於研究任務，生成簡化的協調回應
            if request_type == "research" or request_type == "research_task":
                if locale == "zh-TW" or locale == "zh-CN":
                    return f"我已經收到您的研究請求「{research_topic}」。我會協調研究團隊來處理這個任務，包括制定計劃、收集資料和生成報告。"
                else:
                    return f"I have received your research request '{research_topic}'. I will coordinate the research team to handle this task, including planning, data collection, and report generation."

            # 降級回應
            if locale == "zh-TW" or locale == "zh-CN":
                return f"我已經收到您的請求「{research_topic}」，正在分析如何最好地協助您完成這項任務。"
            else:
                return f"I have received your request '{research_topic}' and am analyzing how to best assist you with this task."

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.error(f"生成協調回應失敗: {e}")
            else:
                logger.error(f"生成協調回應失敗: {e}")

            # 錯誤降級回應
            locale = analysis_result.get("locale", "zh-TW")
            if locale == "zh-TW" or locale == "zh-CN":
                return f"我正在處理您的請求，請稍等片刻。"
            else:
                return "I am processing your request, please wait a moment."

    async def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        處理用戶輸入（兼容 BaseResearchAgent 接口）

        Args:
            user_input: 用戶輸入的內容

        Returns:
            Dict[str, Any]: 包含回應的字典
        """
        try:
            # 設置線程上下文
            thread_id = self._get_thread_id_from_context()
            self._setup_thread_context(thread_id)

            # 檢測語言環境
            locale = self._detect_locale(user_input)

            # 分析用戶輸入
            analysis_result = await self._analyze_user_input(user_input)

            # 生成協調回應
            response = await self._generate_coordination_response(user_input, analysis_result)

            return {
                "response": response,
                "locale": locale,
                "analysis": analysis_result,
                "status": "success",
            }

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.error(f"處理用戶輸入失敗: {e}")
            else:
                logger.error(f"處理用戶輸入失敗: {e}")

            # 返回錯誤回應
            return {
                "response": f"抱歉，處理您的請求時發生錯誤：{str(e)}",
                "locale": "zh-TW",
                "analysis": {"error": str(e)},
                "status": "error",
            }
