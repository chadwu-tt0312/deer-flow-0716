# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
LangGraph 相容性層

提供與現有 LangGraph 接口的完全相容性。
"""

import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
from datetime import datetime


# 使用實際的 AutoGen 類別
from autogen_core.models import ChatCompletionClient

from src.deerflow_logging import get_logger
from src.config.report_style import ReportStyle
from src.rag.retriever import Resource

# 移除不存在的導入
from .api_adapter import AutoGenAPIAdapter

logger = get_logger(__name__)


class LangGraphCompatibilityLayer:
    """
    LangGraph 相容性層

    模擬 LangGraph 的接口行為，內部使用 AutoGen 系統。
    """

    def __init__(self, model_client: ChatCompletionClient):
        """
        初始化相容性層

        Args:
            model_client: 聊天完成客戶端
        """
        self.model_client = model_client
        self.api_adapter = AutoGenAPIAdapter(model_client)
        self._state_storage: Dict[str, Dict[str, Any]] = {}

        logger.info("LangGraph 相容性層初始化完成")

    async def astream(
        self,
        input_data: Union[Dict[str, Any], Any],
        config: Dict[str, Any] = None,
        stream_mode: List[str] = None,
        subgraphs: bool = True,
    ) -> AsyncGenerator[tuple, None]:
        """
        模擬 LangGraph 的 astream 方法

        Args:
            input_data: 輸入數據
            config: 配置參數
            stream_mode: 流模式
            subgraphs: 是否包含子圖

        Yields:
            tuple: (agent, metadata, event_data) 格式的元組
        """
        logger.info("LangGraph 相容性層 - astream 開始")

        try:
            # 解析輸入數據
            messages, thread_id = self._parse_input_data(input_data)

            # 解析配置
            adapter_config = self._parse_config(config or {})

            # 從配置中移除 thread_id，避免重複傳遞
            if "thread_id" in adapter_config:
                del adapter_config["thread_id"]

            # 執行 AutoGen 工作流
            async for event in self.api_adapter.process_chat_request(
                messages=messages, thread_id=thread_id, **adapter_config
            ):
                # 轉換為 LangGraph 格式
                langgraph_event = self._convert_to_langgraph_format(event)
                yield langgraph_event

        except Exception as e:
            logger.error(f"LangGraph 相容性層執行失敗: {e}")
            # 產生錯誤事件
            yield self._create_langgraph_error(str(e))

    def _parse_input_data(
        self, input_data: Union[Dict[str, Any], Any]
    ) -> tuple[List[Dict[str, Any]], str]:
        """解析輸入數據"""
        if isinstance(input_data, dict):
            messages = input_data.get("messages", [])
            thread_id = "default_thread"

            # 處理 LangGraph 格式的訊息
            if messages and isinstance(messages, list):
                # 將 LangGraph 訊息格式轉換為標準格式
                converted_messages = []
                for msg in messages:
                    if isinstance(msg, dict):
                        converted_messages.append(msg)
                    else:
                        # 處理 LangChain 訊息對象
                        converted_msg = {
                            "role": getattr(msg, "type", "user"),
                            "content": getattr(msg, "content", str(msg)),
                        }
                        converted_messages.append(converted_msg)

                return converted_messages, thread_id

            # 處理其他格式的輸入
            elif "research_topic" in input_data:
                research_topic = input_data["research_topic"]
                messages = [{"role": "user", "content": research_topic}]
                return messages, thread_id

        # 處理字符串輸入
        elif isinstance(input_data, str):
            messages = [{"role": "user", "content": input_data}]
            return messages, "default_thread"

        # 預設處理
        return [], "default_thread"

    def _parse_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """解析配置參數"""
        return {
            "thread_id": config.get("thread_id", "default_thread"),
            "resources": config.get("resources", []),
            "max_plan_iterations": config.get("max_plan_iterations", 1),
            "max_step_num": config.get("max_step_num", 3),
            "max_search_results": config.get("max_search_results", 3),
            "auto_accepted_plan": config.get("auto_accepted_plan", True),
            "interrupt_feedback": config.get("interrupt_feedback"),
            "mcp_settings": config.get("mcp_settings", {}),
            "enable_background_investigation": config.get("enable_background_investigation", True),
            "report_style": self._parse_report_style(config.get("report_style", "academic")),
            "enable_deep_thinking": config.get("enable_deep_thinking", False),
        }

    def _parse_report_style(self, style: Union[str, ReportStyle]) -> ReportStyle:
        """解析報告風格"""
        if isinstance(style, ReportStyle):
            return style

        style_mapping = {
            "academic": ReportStyle.ACADEMIC,
            "popular_science": ReportStyle.POPULAR_SCIENCE,
            "news": ReportStyle.NEWS,
            "social_media": ReportStyle.SOCIAL_MEDIA,
        }

        return style_mapping.get(str(style).lower(), ReportStyle.ACADEMIC)

    def _convert_to_langgraph_format(self, autogen_event: Dict[str, Any]) -> tuple:
        """將 AutoGen 事件轉換為 LangGraph 格式"""
        event_type = autogen_event.get("event", "message_chunk")
        data = autogen_event.get("data", {})

        # 創建 agent 標識
        agent_name = data.get("agent", "autogen")
        agent = (f"{agent_name}:default",)

        # 創建元數據
        metadata = {
            "thread_id": data.get("thread_id", "default"),
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
        }

        # 根據事件類型創建不同的事件數據
        if event_type == "interrupt":
            # 中斷事件
            event_data = {
                "__interrupt__": [
                    (
                        type(
                            "Interrupt",
                            (),
                            {
                                "ns": [data.get("id", "interrupt")],
                                "value": data.get("content", "中斷請求"),
                            },
                        )()
                    )
                ]
            }
        elif event_type == "error":
            # 錯誤事件
            event_data = self._create_message_chunk(data, is_error=True)
        else:
            # 普通訊息事件
            event_data = self._create_message_chunk(data)

        return agent, metadata, event_data

    def _create_message_chunk(self, data: Dict[str, Any], is_error: bool = False) -> tuple:
        """創建訊息塊"""
        from langchain_core.messages import AIMessageChunk

        content = data.get("content", "")
        message_id = data.get("id", f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")

        # 創建 AIMessageChunk
        message_chunk = AIMessageChunk(content=content, id=message_id, response_metadata={})

        # 添加完成原因
        finish_reason = data.get("finish_reason")
        if finish_reason:
            message_chunk.response_metadata["finish_reason"] = finish_reason

        # 添加錯誤標記
        if is_error:
            message_chunk.response_metadata["error"] = True

        # 創建元數據
        chunk_metadata = {
            "agent": data.get("agent", "autogen"),
            "thread_id": data.get("thread_id", "default"),
            "timestamp": datetime.now().isoformat(),
        }

        return message_chunk, chunk_metadata

    def _create_langgraph_error(self, error_message: str) -> tuple:
        """創建 LangGraph 格式的錯誤事件"""
        agent = ("error:default",)
        metadata = {
            "thread_id": "default",
            "event_type": "error",
            "timestamp": datetime.now().isoformat(),
        }

        error_data = {
            "content": f"❌ {error_message}",
            "id": f"error_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "agent": "error",
            "finish_reason": "error",
        }

        event_data = self._create_message_chunk(error_data, is_error=True)

        return agent, metadata, event_data

    def invoke(self, input_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        模擬 LangGraph 的 invoke 方法（同步版本）

        Args:
            input_data: 輸入數據
            config: 配置參數

        Returns:
            Dict[str, Any]: 執行結果
        """
        logger.info("LangGraph 相容性層 - invoke 開始")

        # 使用 asyncio 運行異步版本
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(self.ainvoke(input_data, config))
            return result
        finally:
            loop.close()

    async def ainvoke(
        self, input_data: Dict[str, Any], config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        模擬 LangGraph 的 ainvoke 方法（異步版本）

        Args:
            input_data: 輸入數據
            config: 配置參數

        Returns:
            Dict[str, Any]: 執行結果
        """
        logger.info("LangGraph 相容性層 - ainvoke 開始")

        try:
            # 解析輸入數據
            messages, thread_id = self._parse_input_data(input_data)

            # 解析配置
            adapter_config = self._parse_config(config or {})

            # 從配置中移除 thread_id，避免重複傳遞
            if "thread_id" in adapter_config:
                del adapter_config["thread_id"]

            # 收集所有事件
            events = []
            final_content = ""

            async for event in self.api_adapter.process_chat_request(
                messages=messages, thread_id=thread_id, **adapter_config
            ):
                events.append(event)

                # 收集最終內容
                data = event.get("data", {})
                if data.get("agent") == "reporter" and data.get("content"):
                    final_content += data["content"]

            # 返回 LangGraph 風格的結果
            return {
                "messages": messages + [{"role": "assistant", "content": final_content}],
                "final_report": final_content,
                "thread_id": thread_id,
                "events": events,
                "execution_metadata": {
                    "total_events": len(events),
                    "completed_at": datetime.now().isoformat(),
                    "success": True,
                },
            }

        except Exception as e:
            logger.error(f"LangGraph 相容性層 ainvoke 失敗: {e}")
            return {
                "messages": [],
                "final_report": "",
                "thread_id": "error",
                "events": [],
                "execution_metadata": {
                    "error": str(e),
                    "completed_at": datetime.now().isoformat(),
                    "success": False,
                },
            }

    def get_state(self, thread_id: str) -> Dict[str, Any]:
        """獲取執行緒狀態"""
        return self._state_storage.get(thread_id, {})

    def update_state(self, thread_id: str, state: Dict[str, Any]):
        """更新執行緒狀態"""
        if thread_id not in self._state_storage:
            self._state_storage[thread_id] = {}
        self._state_storage[thread_id].update(state)


# 便利函數
def create_langgraph_compatible_graph(
    model_client: ChatCompletionClient,
) -> LangGraphCompatibilityLayer:
    """創建 LangGraph 相容的圖對象"""
    return LangGraphCompatibilityLayer(model_client)
