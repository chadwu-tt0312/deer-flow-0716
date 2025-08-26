# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
LLM 適配器

將現有的 LLM 系統適配為 AutoGen 的 ChatCompletionClient 接口。
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Union, Sequence

from autogen_core import CancellationToken
from autogen_core.models import (
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    CreateResult,
    RequestUsage,
    FinishReasons,
)

import logging

# 使用標準 logging 避免循環導入
logger = logging.getLogger(__name__)

# 暫時簡化 - 避免復雜依賴
try:
    from src.llms.llm import get_llm_by_type
    from src.config.agents import AGENT_LLM_MAP

    HAS_LLM_SYSTEM = True
except ImportError:
    HAS_LLM_SYSTEM = False
    logger.warning("無法導入 LLM 系統，將使用模擬實現")


class LLMChatCompletionAdapter(ChatCompletionClient):
    """
    將現有 LLM 適配為 ChatCompletionClient 的適配器類
    """

    def __init__(self, llm_type: str = "basic"):
        """
        初始化適配器

        Args:
            llm_type: LLM 類型，對應 AGENT_LLM_MAP 中的值
        """
        self.llm_type = llm_type
        self._llm = None
        self._initialize_llm()

    def _initialize_llm(self):
        """初始化底層 LLM"""
        if not HAS_LLM_SYSTEM:
            logger.warning("LLM 系統不可用，使用模擬實現")
            self._llm = None
            return

        try:
            self._llm = get_llm_by_type(self.llm_type)
            logger.info(f"LLM 適配器初始化成功: {self.llm_type}")
        except Exception as e:
            logger.error(f"LLM 適配器初始化失敗: {e}")
            # 不使用降級邏輯，直接設為 None
            self._llm = None

    def _convert_messages_to_legacy_format(
        self, messages: Sequence[LLMMessage]
    ) -> List[Dict[str, str]]:
        """
        將 AutoGen 消息格式轉換為現有系統的格式
        """
        legacy_messages = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                legacy_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, UserMessage):
                legacy_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AssistantMessage):
                legacy_messages.append({"role": "assistant", "content": msg.content})
            else:
                # 未知類型，嘗試提取內容
                content = getattr(msg, "content", str(msg))
                legacy_messages.append({"role": "user", "content": content})

        return legacy_messages

    def _has_tool_calls_support(self) -> bool:
        """檢查 LLM 是否支持工具調用"""
        # 檢查 LLM 是否有 bind_tools 方法或類似功能
        return hasattr(self._llm, "bind_tools") or hasattr(self._llm, "with_structured_output")

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        cancellation_token: Optional[CancellationToken] = None,
        **kwargs,
    ) -> CreateResult:
        """
        創建聊天完成

        實現 ChatCompletionClient 的核心方法
        """
        try:
            if not self._llm:
                raise RuntimeError("LLM 未正確初始化")

            # 轉換消息格式
            legacy_messages = self._convert_messages_to_legacy_format(messages)
            logger.debug(f"轉換後的消息: {legacy_messages}")

            # 處理工具調用
            tools = kwargs.get("tools", [])
            response_content = None

            if tools and self._has_tool_calls_support():
                # 有工具且 LLM 支持工具調用
                # 移除 tools 參數避免衝突
                filtered_kwargs = {k: v for k, v in kwargs.items() if k != "tools"}
                response_content = await self._create_with_tools(
                    legacy_messages, tools, **filtered_kwargs
                )
            else:
                # 標準文本生成
                response_content = await self._create_standard(legacy_messages, **kwargs)

            # 構造回應
            usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

            return CreateResult(
                content=response_content,
                finish_reason="stop",
                usage=usage,
                cached=False,
                logprobs=None,
            )

        except Exception as e:
            logger.error(f"LLM API 調用失敗: {e}")
            raise e

    async def _create_with_tools(
        self, messages: List[Dict[str, str]], tools: List[Dict], **kwargs
    ) -> Union[str, List]:
        """
        使用工具調用的 LLM 創建
        """
        try:
            # 嘗試使用 bind_tools
            if hasattr(self._llm, "bind_tools"):
                # 轉換工具格式
                converted_tools = self._convert_tools_format(tools)
                llm_with_tools = self._llm.bind_tools(converted_tools)

                # 調用 LLM
                if asyncio.iscoroutinefunction(llm_with_tools.invoke):
                    response = await llm_with_tools.invoke(messages)
                else:
                    response = llm_with_tools.invoke(messages)

                # 檢查是否有工具調用
                if hasattr(response, "tool_calls") and response.tool_calls:
                    # 轉換為 AutoGen FunctionCall 格式
                    from autogen_core import FunctionCall

                    function_calls = []

                    for i, tool_call in enumerate(response.tool_calls):
                        function_calls.append(
                            FunctionCall(
                                id=f"call_{i}",
                                name=tool_call.get("name", ""),
                                arguments=json.dumps(tool_call.get("args", {})),
                            )
                        )

                    return function_calls
                else:
                    # 沒有工具調用，返回文本內容
                    return getattr(response, "content", str(response))

            else:
                # LLM 不支持工具調用，返回文本回應
                logger.warning(f"LLM {self.llm_type} 不支持工具調用，降級為標準回應")
                return await self._create_standard(messages)

        except Exception as e:
            logger.error(f"工具調用失敗: {e}")
            # 不使用降級邏輯，直接拋出異常
            raise e

    async def _create_standard(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        標準文本生成
        """
        if not self._llm:
            # 模擬回應
            logger.info("使用模擬 LLM 回應")
            last_message = messages[-1] if messages else {}
            user_content = last_message.get("content", "")

            # 簡單的模擬邏輯
            if any(greeting in user_content.lower() for greeting in ["你好", "hello", "hi", "嗨"]):
                return "你好！我是 DeerFlow，很高興為你服務。我可以幫助你進行各種研究和資訊查詢。"
            else:
                return f"我瞭解您的請求：「{user_content}」。讓我為您安排研究團隊來處理這個任務。"

        try:
            # 調用現有 LLM
            if asyncio.iscoroutinefunction(self._llm.invoke):
                response = await self._llm.invoke(messages)
            else:
                response = self._llm.invoke(messages)

            # 提取內容
            if hasattr(response, "content"):
                return response.content
            else:
                return str(response)

        except Exception as e:
            logger.error(f"標準 LLM 調用失敗: {e}")
            # 不使用降級邏輯，直接拋出異常
            raise e

    def _convert_tools_format(self, tools: List[Dict]) -> List[Dict]:
        """
        轉換工具格式以適配現有 LLM
        """
        converted_tools = []

        for tool in tools:
            if tool.get("type") == "function":
                function_def = tool.get("function", {})

                # 轉換為 LangChain 工具格式
                converted_tool = {
                    "name": function_def.get("name"),
                    "description": function_def.get("description"),
                    "parameters": function_def.get("parameters", {}),
                }

                converted_tools.append(converted_tool)

        return converted_tools

    @property
    def capabilities(self) -> Dict[str, Any]:
        """返回 LLM 能力"""
        return {
            "completion": True,
            "chat_completion": True,
            "function_calling": self._has_tool_calls_support(),
            "json_output": hasattr(self._llm, "with_structured_output"),
        }

    def remaining_tokens(self, messages: Sequence[LLMMessage]) -> int:
        """
        計算剩餘 token 數量

        簡化實現，返回一個合理的估計值
        """
        # 簡單估計：每條消息平均 100 tokens
        estimated_used = len(messages) * 100

        # 假設最大 token 數為 4096（GPT-3.5 的限制）
        max_tokens = 4096

        return max(0, max_tokens - estimated_used)

    # 實現 ChatCompletionClient 的抽象方法
    def count_tokens(self, messages: Sequence[LLMMessage], **kwargs) -> int:
        """計算 token 數量"""
        return len(messages) * 100  # 簡化估計

    def actual_usage(self) -> Dict[str, Any]:
        """返回實際使用情況"""
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def total_usage(self) -> Dict[str, Any]:
        """返回總使用情況"""
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    @property
    def model_info(self) -> Dict[str, Any]:
        """返回模型信息"""
        # AutoGen SelectorGroupChat 需要 family 字段
        family = "gpt-4o-mini" if self.llm_type == "reasoning" else "gpt-4o"

        return {
            "model": self.llm_type,
            "family": family,  # 必需的字段
            "type": "LLMChatCompletionAdapter",
            "capabilities": self.capabilities,
            "vision": False,  # 額外的標準字段
            "function_calling": True,
            "json_mode": True,
        }

    async def create_stream(self, messages: Sequence[LLMMessage], **kwargs):
        """創建流式回應（簡化實現）"""
        result = await self.create(messages, **kwargs)
        yield result

    async def close(self):
        """關閉客戶端"""
        pass


def create_chat_client(role: str) -> ChatCompletionClient:
    """
    為協調者創建 ChatCompletionClient
    """
    if HAS_LLM_SYSTEM:
        llm_type = AGENT_LLM_MAP.get(role, "basic")
    else:
        llm_type = "basic"
    return LLMChatCompletionAdapter(llm_type)


def create_chat_client_for_agent(agent_name: str) -> ChatCompletionClient:
    """
    為指定智能體創建 ChatCompletionClient

    Args:
        agent_name: 智能體名稱（對應 AGENT_LLM_MAP 中的鍵）

    Returns:
        ChatCompletionClient 實例
    """
    if HAS_LLM_SYSTEM:
        llm_type = AGENT_LLM_MAP.get(agent_name, "basic")
    else:
        llm_type = "basic"
    return LLMChatCompletionAdapter(llm_type)


def create_autogen_model_client(llm_type: str, config: Dict[str, Any]) -> ChatCompletionClient:
    """
    根據 LLM 類型和配置創建 AutoGen 模型客戶端

    Args:
        llm_type: LLM 類型 ("basic" 或 "reasoning")
        config: 配置字典

    Returns:
        ChatCompletionClient 實例
    """
    return LLMChatCompletionAdapter(llm_type)
