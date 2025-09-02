# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen API 服務器

提供與現有 API 完全相容的 AutoGen 接口。
"""

import asyncio
from typing import List, Dict, Any, Optional
from uuid import uuid4

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from src.config.report_style import ReportStyle
from src.llms.llm import get_configured_llm_models
from src.rag.retriever import Resource
from src.server.chat_request import ChatRequest
from src.deerflow_logging import (
    get_simple_logger as get_logger,
    set_thread_context,
    clear_thread_context,
    setup_thread_logging,
)

from .api_adapter import AutoGenAPIAdapter
from .langgraph_compatibility import LangGraphCompatibilityLayer
from .response_mapper import StreamResponseMapper


# 使用實際的 AutoGen 類別
from autogen_core.models import ChatCompletionClient as OpenAIChatCompletionClient

logger = get_logger(__name__)


class AutoGenAPIServer:
    """
    AutoGen API 服務器

    提供與現有 FastAPI 端點相容的 AutoGen 接口。
    """

    def __init__(self):
        """初始化 API 服務器"""
        self.model_clients = {}
        self.api_adapters = {}
        self.compatibility_layers = {}

        # 初始化模型客戶端
        self._initialize_model_clients()

        logger.info("AutoGen API 服務器初始化完成")

    def _initialize_model_clients(self):
        """初始化模型客戶端"""
        try:
            configured_models = get_configured_llm_models()

            # 檢查 configured_models 的結構
            if isinstance(configured_models, dict):
                # 如果是字典，轉換為模型配置列表
                model_configs = []
                for llm_type, model_names in configured_models.items():
                    if isinstance(model_names, list):
                        for model_name in model_names:
                            model_configs.append(
                                {
                                    "name": f"{llm_type}_{model_name}",
                                    "model": model_name,
                                    "type": llm_type,
                                }
                            )
                    else:
                        # 如果 model_names 不是列表，直接使用
                        model_configs.append(
                            {
                                "name": f"{llm_type}_{model_names}",
                                "model": model_names,
                                "type": llm_type,
                            }
                        )
            else:
                # 如果已經是列表，直接使用
                model_configs = configured_models

            # 為每個配置的模型創建客戶端
            for model_config in model_configs:
                if isinstance(model_config, dict):
                    model_name = model_config.get("name", "default")
                    model_value = model_config.get("model", "gpt-4")
                else:
                    # 如果 model_config 不是字典，跳過
                    continue

                # 這裡應該根據實際的模型配置創建客戶端
                # 暫時使用模擬的客戶端
                try:
                    # 使用 AutoGen 適配器創建客戶端
                    from src.autogen_system.adapters.llm_adapter import create_autogen_model_client

                    client = create_autogen_model_client(
                        llm_type="basic", config={"model": model_value}
                    )
                    self.model_clients[model_name] = client

                    # 創建對應的適配器和相容性層
                    try:
                        from .api_adapter import AutoGenAPIAdapter
                        from .langgraph_compatibility import LangGraphCompatibilityLayer

                        self.api_adapters[model_name] = AutoGenAPIAdapter(client)
                        self.compatibility_layers[model_name] = LangGraphCompatibilityLayer(client)
                        logger.info(f"成功創建模型 {model_name} 的適配器和相容性層")
                    except Exception as e:
                        logger.error(f"創建適配器失敗 {model_name}: {e}")
                        # 即使適配器創建失敗，也要確保有預設的適配器

                except Exception as e:
                    logger.warning(f"無法創建模型客戶端 {model_name}: {e}")

        except Exception as e:
            logger.error(f"初始化模型客戶端失敗: {e}")

        # 確保至少有預設客戶端和適配器
        if "default" not in self.model_clients:
            try:
                from src.autogen_system.adapters.llm_adapter import create_autogen_model_client

                default_client = create_autogen_model_client(
                    llm_type="basic", config={"model": "gpt-4o-mini"}
                )
                self.model_clients["default"] = default_client
                logger.info("創建預設模型客戶端")
            except Exception as e:
                logger.error(f"創建預設模型客戶端失敗: {e}")
                # 創建一個最基本的適配器
                from src.autogen_system.adapters.llm_adapter import LLMChatCompletionAdapter

                self.model_clients["default"] = LLMChatCompletionAdapter("basic")

        if "default" not in self.api_adapters:
            try:
                from .api_adapter import AutoGenAPIAdapter

                self.api_adapters["default"] = AutoGenAPIAdapter(self.model_clients["default"])
                logger.info("創建預設 API 適配器")
            except Exception as e:
                logger.error(f"創建預設 API 適配器失敗: {e}")
                # 創建一個最基本的模擬適配器
                self.api_adapters["default"] = self._create_mock_adapter()

        if "default" not in self.compatibility_layers:
            try:
                from .langgraph_compatibility import LangGraphCompatibilityLayer

                self.compatibility_layers["default"] = LangGraphCompatibilityLayer(
                    self.model_clients["default"]
                )
                logger.info("創建預設相容性層")
            except Exception as e:
                logger.error(f"創建預設相容性層失敗: {e}")
                # 創建一個最基本的模擬相容性層
                self.compatibility_layers["default"] = self._create_mock_compatibility_layer()

        logger.info(
            f"初始化完成 - 模型客戶端: {len(self.model_clients)}, 適配器: {len(self.api_adapters)}, 相容性層: {len(self.compatibility_layers)}"
        )

    def _create_mock_adapter(self):
        """創建模擬適配器作為備用"""

        class MockAdapter:
            async def process_chat_request(self, messages, thread_id="default", **kwargs):
                yield {
                    "type": "error",
                    "data": {
                        "message": "AutoGen 系統暫時不可用，請檢查配置",
                        "thread_id": thread_id,
                        "timestamp": "2025-01-08T16:00:00Z",
                    },
                }

        return MockAdapter()

    def _create_mock_compatibility_layer(self):
        """創建模擬相容性層作為備用"""

        class MockCompatibilityLayer:
            async def ainvoke(self, input_data, config=None):
                return {
                    "error": "AutoGen 相容性層暫時不可用，請檢查配置",
                    "timestamp": "2025-01-08T16:00:00Z",
                }

        return MockCompatibilityLayer()

    def get_model_client(self, model_name: str = "default"):
        """獲取模型客戶端"""
        return self.model_clients.get(model_name, self.model_clients.get("default"))

    def get_api_adapter(self, model_name: str = "default") -> AutoGenAPIAdapter:
        """獲取 API 適配器"""
        return self.api_adapters.get(model_name, self.api_adapters.get("default"))

    def get_compatibility_layer(self, model_name: str = "default") -> LangGraphCompatibilityLayer:
        """獲取相容性層"""
        return self.compatibility_layers.get(model_name, self.compatibility_layers.get("default"))

    async def handle_chat_stream(self, request: ChatRequest) -> StreamingResponse:
        """
        處理聊天流式請求

        Args:
            request: 聊天請求

        Returns:
            StreamingResponse: 流式響應
        """
        thread_id = request.thread_id
        if thread_id == "__default__":
            thread_id = str(uuid4())

        # 記錄 API 呼叫
        logger.info("AutoGen Chat stream started")

        # 設置執行緒上下文
        clear_thread_context()
        logger.info(f"Thread [{thread_id}] started")

        return StreamingResponse(
            self._autogen_stream_generator(request, thread_id),
            media_type="text/event-stream",
        )

    async def _autogen_stream_generator(self, request: ChatRequest, thread_id: str):
        """AutoGen 流式生成器"""
        try:
            # 設定執行緒上下文
            # 使用新的 Thread-specific 日誌系統
            thread_logger = setup_thread_logging(thread_id)
            set_thread_context(thread_id)

            # 記錄 thread 開始
            thread_logger.info(f"開始處理 AutoGen 對話: {thread_id}")

            # 獲取 API 適配器
            adapter = self.get_api_adapter()

            # 轉換請求參數
            messages = [msg.dict() for msg in request.messages] if request.messages else []

            # 執行 AutoGen 工作流
            autogen_stream = adapter.process_chat_request(
                messages=messages,
                thread_id=thread_id,
                resources=request.resources or [],
                max_plan_iterations=request.max_plan_iterations or 1,
                max_step_num=request.max_step_num or 3,
                max_search_results=request.max_search_results or 3,
                auto_accepted_plan=request.auto_accepted_plan or False,
                interrupt_feedback=request.interrupt_feedback,
                mcp_settings=request.mcp_settings or {},
                enable_background_investigation=request.enable_background_investigation or True,
                report_style=request.report_style or ReportStyle.ACADEMIC,
                enable_deep_thinking=request.enable_deep_thinking or False,
            )

            # 將 AutoGen 流轉換為 SSE 格式
            async for sse_event in StreamResponseMapper.map_stream_events(autogen_stream):
                yield sse_event

        except Exception as e:
            if thread_logger:
                thread_logger.error(f"AutoGen 流式生成失敗: {e}")
            else:
                logger.error(f"AutoGen 流式生成失敗: {e}")
            # 發送錯誤事件
            error_sse = StreamResponseMapper._create_error_sse(str(e))
            yield error_sse

        finally:
            # 記錄 thread 結束
            if thread_logger:
                thread_logger.info(f"AutoGen 對話處理完成: {thread_id}")
            # 清理執行緒上下文
            clear_thread_context()

    async def handle_langgraph_compatibility(
        self, input_data: Dict[str, Any], config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        處理 LangGraph 相容性請求

        Args:
            input_data: 輸入數據
            config: 配置參數

        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            compatibility_layer = self.get_compatibility_layer()
            result = await compatibility_layer.ainvoke(input_data, config)
            return result

        except Exception as e:
            logger.error(f"LangGraph 相容性處理失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def handle_langgraph_astream(
        self,
        input_data: Dict[str, Any],
        config: Dict[str, Any] = None,
        stream_mode: List[str] = None,
        subgraphs: bool = True,
    ):
        """
        處理 LangGraph astream 相容性請求

        Args:
            input_data: 輸入數據
            config: 配置參數
            stream_mode: 流模式
            subgraphs: 是否包含子圖

        Yields:
            tuple: LangGraph 格式的事件
        """
        try:
            compatibility_layer = self.get_compatibility_layer()

            async for event in compatibility_layer.astream(
                input_data=input_data, config=config, stream_mode=stream_mode, subgraphs=subgraphs
            ):
                yield event

        except Exception as e:
            logger.error(f"LangGraph astream 相容性處理失敗: {e}")
            # 產生錯誤事件
            yield compatibility_layer._create_langgraph_error(str(e))

    def get_server_status(self) -> Dict[str, Any]:
        """獲取服務器狀態"""
        return {
            "status": "running",
            "system": "autogen",
            "available_models": list(self.model_clients.keys()),
            "adapters_count": len(self.api_adapters),
            "compatibility_layers_count": len(self.compatibility_layers),
            "features": {
                "chat_stream": True,
                "langgraph_compatibility": True,
                "interactive_workflow": True,
                "tool_integration": True,
                "human_feedback": True,
            },
        }


# 全域服務器實例
autogen_api_server = AutoGenAPIServer()


# 便利函數
async def get_autogen_chat_stream(request: ChatRequest) -> StreamingResponse:
    """獲取 AutoGen 聊天流"""
    return await autogen_api_server.handle_chat_stream(request)


async def invoke_autogen_workflow(
    input_data: Dict[str, Any], config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """調用 AutoGen 工作流"""
    return await autogen_api_server.handle_langgraph_compatibility(input_data, config)


async def stream_autogen_workflow(
    input_data: Dict[str, Any],
    config: Dict[str, Any] = None,
    stream_mode: List[str] = None,
    subgraphs: bool = True,
):
    """流式調用 AutoGen 工作流"""
    async for event in autogen_api_server.handle_langgraph_astream(
        input_data, config, stream_mode, subgraphs
    ):
        yield event
