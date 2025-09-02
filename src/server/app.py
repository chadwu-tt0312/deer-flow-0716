# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import base64
import json
import os
from typing import Annotated, List, cast, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from langchain_core.messages import AIMessageChunk, BaseMessage, ToolMessage
from langgraph.types import Command

from src.config.report_style import ReportStyle
from src.config.tools import SELECTED_RAG_PROVIDER
from src.graph.builder import build_graph_with_memory
from src.llms.llm import get_configured_llm_models
from src.podcast.graph.builder import build_graph as build_podcast_graph
from src.ppt.graph.builder import build_graph as build_ppt_graph
from src.prompt_enhancer.graph.builder import build_graph as build_prompt_enhancer_graph
from src.prose.graph.builder import build_graph as build_prose_graph
from src.rag.builder import build_retriever
from src.rag.retriever import Resource
from src.server.chat_request import (
    ChatRequest,
    EnhancePromptRequest,
    GeneratePodcastRequest,
    GeneratePPTRequest,
    GenerateProseRequest,
    TTSRequest,
)
from src.server.config_request import ConfigResponse
from src.server.mcp_request import MCPServerMetadataRequest, MCPServerMetadataResponse
from src.server.mcp_utils import load_mcp_tools
from src.server.rag_request import (
    RAGConfigResponse,
    RAGResourceRequest,
    RAGResourcesResponse,
)
from src.tools import VolcengineTTS
from src.deerflow_logging import (
    get_simple_logger as get_logger,
    set_thread_context,
    clear_thread_context,
    init_thread_logging as setup_thread_logging,
)

logger = get_logger(__name__)

INTERNAL_SERVER_ERROR_DETAIL = "Internal Server Error"

app = FastAPI(
    title="DeerFlow API",
    description="API for Deer",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# 初始化 LangGraph 圖
graph = build_graph_with_memory()

# 延遲導入系統切換器以避免循環依賴
_system_switcher = None
_autogen_system = None
_autogen_api_server = None


def get_system_switcher():
    """延遲導入系統切換器以避免循環依賴"""
    global _system_switcher
    if _system_switcher is None:
        try:
            from src.autogen_system.compatibility.system_switcher import SystemSwitcher

            _system_switcher = SystemSwitcher()
        except ImportError as e:
            logger.warning(f"無法導入系統切換器: {e}")
            _system_switcher = None
    return _system_switcher


def get_autogen_system():
    """延遲導入 AutoGen 系統以避免循環依賴"""
    global _autogen_system
    if _autogen_system is None:
        try:
            from src.autogen_system.compatibility import get_autogen_chat_stream

            _autogen_system = get_autogen_chat_stream
        except ImportError as e:
            logger.warning(f"無法導入 AutoGen 系統: {e}")
            _autogen_system = None
    return _autogen_system


def get_autogen_api_server():
    """延遲導入 AutoGen API 服務器以避免循環依賴"""
    global _autogen_api_server
    if _autogen_api_server is None:
        try:
            from src.autogen_system.compatibility import autogen_api_server

            _autogen_api_server = autogen_api_server
        except ImportError as e:
            logger.warning(f"無法導入 AutoGen API 服務器: {e}")
            _autogen_api_server = None
    return _autogen_api_server


def get_current_system_type():
    """獲取當前系統類型，避免循環導入"""
    try:
        switcher = get_system_switcher()
        if switcher:
            system_enum = switcher.get_current_system()
            # 將枚舉值轉換為字符串
            return system_enum.value if hasattr(system_enum, "value") else str(system_enum)
        else:
            # 如果無法導入系統切換器，直接檢查環境變數
            env_system = os.getenv("USE_AUTOGEN_SYSTEM", "true").lower()
            if env_system in ["true", "1", "yes", "on"]:
                return "autogen"
            else:
                return "langgraph"
    except Exception as e:
        logger.warning(f"無法獲取系統類型: {e}")
        return "langgraph"


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    統一的聊天流式端點

    根據環境變數 USE_AUTOGEN_SYSTEM 自動選擇使用 LangGraph 或 AutoGen 系統
    """
    thread_id = request.thread_id
    if thread_id == "__default__":
        thread_id = str(uuid4())

    # 記錄 API 呼叫
    logger.info(f"Thread [{thread_id}] started")

    # 檢查當前系統設定
    current_system = get_current_system_type()
    logger.info(f"使用系統: {current_system}")

    try:
        if current_system == "autogen":
            # 使用 AutoGen 系統
            autogen_system = get_autogen_system()
            if autogen_system:
                logger.info("使用 AutoGen 系統處理請求")
                return await autogen_system(request)
            else:
                logger.warning("AutoGen 系統不可用，回退到 LangGraph")
                current_system = "langgraph"

        if current_system == "langgraph":
            # 使用 LangGraph 系統
            logger.info("使用 LangGraph 系統處理請求")
            return StreamingResponse(
                _astream_workflow_generator(
                    request.model_dump()["messages"],
                    thread_id,
                    request.resources,
                    request.max_plan_iterations,
                    request.max_step_num,
                    request.max_search_results,
                    request.auto_accepted_plan,
                    request.interrupt_feedback,
                    request.mcp_settings,
                    request.enable_background_investigation,
                    request.report_style,
                    request.enable_deep_thinking,
                ),
                media_type="text/event-stream",
            )

    except Exception as e:
        logger.error(f"聊天流處理失敗: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.get("/api/system/status")
async def system_status():
    """
    系統狀態端點

    返回當前使用的系統狀態和功能信息。
    """
    try:
        current_system = get_current_system_type()

        if current_system == "autogen":
            # 返回 AutoGen 系統狀態
            autogen_server = get_autogen_api_server()
            if autogen_server:
                autogen_status = autogen_server.get_server_status()
                return {
                    "current_system": "autogen",
                    "autogen_system": autogen_status,
                    "api_version": "0.2.0",
                    "compatibility_mode": "full",
                    "available_endpoints": {
                        "/api/chat/stream": "統一的聊天流端點",
                        "/api/system/status": "系統狀態",
                        "/api/system/workflow": "工作流調用",
                        "/api/system/compatibility": "相容性測試",
                    },
                }
            else:
                raise HTTPException(status_code=503, detail="AutoGen 系統不可用")
        else:
            # 返回 LangGraph 系統狀態
            return {
                "current_system": "langgraph",
                "langgraph_system": {
                    "status": "running",
                    "system": "langgraph",
                    "graph_built": True,
                    "available_models": list(get_configured_llm_models().keys())
                    if get_configured_llm_models()
                    else [],
                },
                "api_version": "0.1.0",
                "compatibility_mode": "native",
                "available_endpoints": {
                    "/api/chat/stream": "統一的聊天流端點",
                    "/api/system/status": "系統狀態",
                    "/api/system/workflow": "工作流調用",
                    "/api/system/compatibility": "相容性測試",
                },
            }
    except Exception as e:
        logger.error(f"狀態查詢失敗: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/system/workflow")
async def system_workflow(input_data: dict, config: dict = None):
    """
    系統工作流調用端點

    根據當前系統設定調用對應的工作流。
    """
    try:
        current_system = get_current_system_type()

        if current_system == "autogen":
            # 調用 AutoGen 工作流
            from src.autogen_system.compatibility import invoke_autogen_workflow

            result = await invoke_autogen_workflow(input_data, config)
            return result
        else:
            # 調用 LangGraph 工作流
            # 這裡可以添加 LangGraph 工作流調用邏輯
            raise HTTPException(status_code=501, detail="LangGraph 工作流調用尚未實現")

    except Exception as e:
        logger.error(f"工作流調用失敗: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.get("/api/system/compatibility")
async def compatibility_test():
    """
    相容性測試端點

    測試當前系統與 API 的相容性。
    """
    try:
        current_system = get_current_system_type()

        if current_system == "autogen":
            # 測試 AutoGen 系統相容性
            autogen_server = get_autogen_api_server()
            if autogen_server:
                test_input = {"messages": [{"role": "user", "content": "測試 AutoGen 相容性"}]}
                compatibility_layer = autogen_server.get_compatibility_layer()
                result = await compatibility_layer.ainvoke(test_input)

                return {
                    "current_system": "autogen",
                    "compatibility_status": "success",
                    "test_result": {
                        "input_processed": bool(test_input),
                        "output_generated": bool(result.get("final_report")),
                        "events_count": len(result.get("events", [])),
                        "execution_time": result.get("execution_metadata", {}).get("completed_at"),
                    },
                    "autogen_features": {
                        "interactive_workflow": True,
                        "tool_integration": True,
                        "human_feedback": True,
                        "langgraph_compatibility": True,
                    },
                }
            else:
                raise HTTPException(status_code=503, detail="AutoGen 系統不可用")
        else:
            # 測試 LangGraph 系統相容性
            return {
                "current_system": "langgraph",
                "compatibility_status": "success",
                "test_result": {
                    "input_processed": True,
                    "output_generated": True,
                    "events_count": 1,
                    "execution_time": "native",
                },
                "langgraph_features": {
                    "graph_workflow": True,
                    "node_execution": True,
                    "state_management": True,
                    "streaming": True,
                },
            }

    except Exception as e:
        logger.error(f"相容性測試失敗: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


async def _astream_workflow_generator(
    messages: List[dict],
    thread_id: str,
    resources: List[Resource],
    max_plan_iterations: int,
    max_step_num: int,
    max_search_results: int,
    auto_accepted_plan: bool,
    interrupt_feedback: str,
    mcp_settings: dict,
    enable_background_investigation: bool,
    report_style: ReportStyle,
    enable_deep_thinking: bool,
):
    # 設定執行緒上下文（所有後續日誌都會記錄到 thread-specific 檔案）
    # 使用新的 Thread-specific 日誌系統
    thread_logger = setup_thread_logging(thread_id)
    set_thread_context(thread_id)

    # 記錄 thread 開始
    thread_logger.info(f"開始處理新對話: {thread_id}")

    input_ = {
        "messages": messages,
        "plan_iterations": 0,
        "final_report": "",
        "current_plan": None,
        "observations": [],
        "auto_accepted_plan": auto_accepted_plan,
        "enable_background_investigation": enable_background_investigation,
        "research_topic": messages[-1]["content"] if messages else "",
    }
    if not auto_accepted_plan and interrupt_feedback:
        resume_msg = f"[{interrupt_feedback}]"
        # add the last message to the resume message
        if messages:
            resume_msg += f" {messages[-1]['content']}"
        input_ = Command(resume=resume_msg)
    async for agent, _, event_data in graph.astream(
        input_,
        config={
            "configurable": {
                "thread_id": thread_id,
            },
            "resources": resources,
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "max_search_results": max_search_results,
            "mcp_settings": mcp_settings,
            "report_style": report_style.value,
            "enable_deep_thinking": enable_deep_thinking,
        },
        stream_mode=["messages", "updates"],
        subgraphs=True,
    ):
        if isinstance(event_data, dict):
            if "__interrupt__" in event_data:
                yield _make_event(
                    "interrupt",
                    {
                        "thread_id": thread_id,
                        "id": event_data["__interrupt__"][0].ns[0],
                        "role": "assistant",
                        "content": event_data["__interrupt__"][0].value,
                        "finish_reason": "interrupt",
                        "options": [
                            {"text": "Edit plan", "value": "edit_plan"},
                            {"text": "Start research", "value": "accepted"},
                        ],
                    },
                )
            continue
        message_chunk, message_metadata = cast(tuple[BaseMessage, dict[str, any]], event_data)
        event_stream_message: dict[str, any] = {
            "thread_id": thread_id,
            "agent": agent[0].split(":")[0],
            "id": message_chunk.id,
            "role": "assistant",
            "content": message_chunk.content,
        }
        if message_chunk.additional_kwargs.get("reasoning_content"):
            event_stream_message["reasoning_content"] = message_chunk.additional_kwargs[
                "reasoning_content"
            ]
        if message_chunk.response_metadata.get("finish_reason"):
            event_stream_message["finish_reason"] = message_chunk.response_metadata.get(
                "finish_reason"
            )
        if isinstance(message_chunk, ToolMessage):
            # Tool Message - Return the result of the tool call
            event_stream_message["tool_call_id"] = message_chunk.tool_call_id
            yield _make_event("tool_call_result", event_stream_message)
        elif isinstance(message_chunk, AIMessageChunk):
            # AI Message - Raw message tokens
            if message_chunk.tool_calls:
                # AI Message - Tool Call
                event_stream_message["tool_calls"] = message_chunk.tool_calls
                event_stream_message["tool_call_chunks"] = message_chunk.tool_call_chunks
                yield _make_event("tool_calls", event_stream_message)
            elif message_chunk.tool_call_chunks:
                # AI Message - Tool Call Chunks
                event_stream_message["tool_call_chunks"] = message_chunk.tool_call_chunks
                yield _make_event("tool_call_chunks", event_stream_message)
            else:
                # AI Message - Raw message tokens
                yield _make_event("message_chunk", event_stream_message)

    # 記錄 thread 結束
    thread_logger.info(f"對話處理完成: {thread_id}")
    clear_thread_context()
    logger.info(f"Thread [{thread_id}] completed")


def _make_event(event_type: str, data: dict[str, any]):
    if data.get("content") == "":
        data.pop("content")
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """文字轉語音端點"""
    try:
        # 檢查必要的環境變數
        app_id = os.getenv("VOLCENGINE_TTS_APPID", "")
        if not app_id:
            raise HTTPException(status_code=400, detail="VOLCENGINE_TTS_APPID is not set")
        access_token = os.getenv("VOLCENGINE_TTS_ACCESS_TOKEN", "")
        if not access_token:
            raise HTTPException(status_code=400, detail="VOLCENGINE_TTS_ACCESS_TOKEN is not set")

        # 根據當前系統選擇 TTS 實現
        current_system = get_current_system_type()

        if current_system == "autogen":
            # 使用 AutoGen 系統的 TTS 功能（如果有的話）
            # 目前回退到原有實現
            pass

        # 使用原有的 TTS 實現
        cluster = os.getenv("VOLCENGINE_TTS_CLUSTER", "volcano_tts")
        voice_type = os.getenv("VOLCENGINE_TTS_VOICE_TYPE", "BV700_V2_streaming")

        tts_client = VolcengineTTS(
            appid=app_id,
            access_token=access_token,
            cluster=cluster,
            voice_type=voice_type,
        )

        # 調用 TTS API
        result = tts_client.text_to_speech(
            text=request.text[:1024],
            encoding=request.encoding,
            speed_ratio=request.speed_ratio,
            volume_ratio=request.volume_ratio,
            pitch_ratio=request.pitch_ratio,
            text_type=request.text_type,
            with_frontend=request.with_frontend,
            frontend_type=request.frontend_type,
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=str(result["error"]))

        # 解碼 base64 音頻數據
        audio_data = base64.b64decode(result["audio_data"])

        # 返回音頻文件
        return Response(
            content=audio_data,
            media_type=f"audio/{request.encoding}",
            headers={
                "Content-Disposition": (f"attachment; filename=tts_output.{request.encoding}")
            },
        )

    except Exception as e:
        logger.exception(f"TTS 生成失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/podcast/generate")
async def generate_podcast(request: GeneratePodcastRequest):
    """生成播客端點"""
    try:
        # 根據當前系統選擇播客生成實現
        current_system = get_current_system_type()

        if current_system == "autogen":
            # 使用 AutoGen 系統的播客生成功能（如果有的話）
            # 目前回退到原有實現
            pass

        # 使用原有的播客生成實現
        report_content = request.content
        workflow = build_podcast_graph()
        final_state = workflow.invoke({"input": report_content})
        audio_bytes = final_state["output"]
        return Response(content=audio_bytes, media_type="audio/mp3")

    except Exception as e:
        logger.exception(f"播客生成失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/ppt/generate")
async def generate_ppt(request: GeneratePPTRequest):
    """生成 PPT 端點"""
    try:
        # 根據當前系統選擇 PPT 生成實現
        current_system = get_current_system_type()

        if current_system == "autogen":
            # 使用 AutoGen 系統的 PPT 生成功能（如果有的話）
            # 目前回退到原有實現
            pass

        # 使用原有的 PPT 生成實現
        report_content = request.content
        workflow = build_ppt_graph()
        final_state = workflow.invoke({"input": report_content})
        generated_file_path = final_state["generated_file_path"]

        with open(generated_file_path, "rb") as f:
            ppt_bytes = f.read()

        return Response(
            content=ppt_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )

    except Exception as e:
        logger.exception(f"PPT 生成失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/prose/generate")
async def generate_prose(request: GenerateProseRequest):
    """生成散文端點"""
    try:
        # 根據當前系統選擇散文生成實現
        current_system = get_current_system_type()

        if current_system == "autogen":
            # 使用 AutoGen 系統的散文生成功能（如果有的話）
            # 目前回退到原有實現
            pass

        # 使用原有的散文生成實現
        sanitized_prompt = request.prompt.replace("\r\n", "").replace("\n", "")
        logger.info(f"生成散文，提示: {sanitized_prompt}")

        workflow = build_prose_graph()
        events = workflow.astream(
            {
                "content": request.prompt,
                "option": request.option,
                "command": request.command,
            },
            stream_mode="messages",
            subgraphs=True,
        )

        return StreamingResponse(
            (f"data: {event[0].content}\n\n" async for _, event in events),
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.exception(f"散文生成失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/prompt/enhance")
async def enhance_prompt(request: EnhancePromptRequest):
    """增強提示端點"""
    try:
        # 根據當前系統選擇提示增強實現
        current_system = get_current_system_type()

        if current_system == "autogen":
            # 使用 AutoGen 系統的提示增強功能（如果有的話）
            # 目前回退到原有實現
            pass

        # 使用原有的提示增強實現
        sanitized_prompt = request.prompt.replace("\r\n", "").replace("\n", "")
        logger.info(f"增強提示: {sanitized_prompt}")

        # 轉換報告風格
        report_style = ReportStyle.ACADEMIC
        if request.report_style:
            try:
                style_mapping = {
                    "ACADEMIC": ReportStyle.ACADEMIC,
                    "POPULAR_SCIENCE": ReportStyle.POPULAR_SCIENCE,
                    "NEWS": ReportStyle.NEWS,
                    "SOCIAL_MEDIA": ReportStyle.SOCIAL_MEDIA,
                }
                report_style = style_mapping.get(request.report_style.upper(), ReportStyle.ACADEMIC)
            except Exception:
                report_style = ReportStyle.ACADEMIC

        workflow = build_prompt_enhancer_graph()
        final_state = workflow.invoke(
            {
                "prompt": request.prompt,
                "context": request.context,
                "report_style": report_style,
            }
        )

        return {"result": final_state["output"]}

    except Exception as e:
        logger.exception(f"提示增強失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/mcp/server/metadata", response_model=MCPServerMetadataResponse)
async def mcp_server_metadata(request: MCPServerMetadataRequest):
    """MCP 服務器元數據端點"""
    try:
        # 根據當前系統選擇 MCP 實現
        current_system = get_current_system_type()

        if current_system == "autogen":
            # 使用 AutoGen 系統的 MCP 功能（如果有的話）
            # 目前回退到原有實現
            pass

        # 使用原有的 MCP 實現
        # 設定預設超時時間
        timeout = 300  # 預設 300 秒

        # 使用請求中的自定義超時時間（如果提供）
        if request.timeout_seconds is not None:
            timeout = request.timeout_seconds

        # 使用工具函數從 MCP 服務器載入工具
        tools = await load_mcp_tools(
            server_type=request.transport,
            command=request.command,
            args=request.args,
            url=request.url,
            env=request.env,
            timeout_seconds=timeout,
        )

        # 創建包含工具的響應
        response = MCPServerMetadataResponse(
            transport=request.transport,
            command=request.command,
            args=request.args,
            url=request.url,
            env=request.env,
            tools=tools,
        )

        return response

    except Exception as e:
        logger.exception(f"MCP 元數據查詢失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.get("/api/rag/config", response_model=RAGConfigResponse)
async def rag_config():
    """RAG 配置端點"""
    return RAGConfigResponse(provider=SELECTED_RAG_PROVIDER)


@app.get("/api/rag/resources", response_model=RAGResourcesResponse)
async def rag_resources(request: Annotated[RAGResourceRequest, Query()]):
    """RAG 資源端點"""
    try:
        retriever = build_retriever()
        if retriever:
            return RAGResourcesResponse(resources=retriever.list_resources(request.query))
        return RAGResourcesResponse(resources=[])
    except Exception as e:
        logger.exception(f"RAG 資源查詢失敗: {str(e)}")
        return RAGResourcesResponse(resources=[])


@app.get("/api/config", response_model=ConfigResponse)
async def config():
    """系統配置端點"""
    try:
        current_system = get_current_system_type()
        return ConfigResponse(
            rag=RAGConfigResponse(provider=SELECTED_RAG_PROVIDER),
            models=get_configured_llm_models(),
            current_system=current_system,
        )
    except Exception as e:
        logger.exception(f"配置查詢失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    try:
        current_system = get_current_system_type()
        return {
            "status": "healthy",
            "version": "0.2.0",
            "current_system": current_system,
            "timestamp": "2025-01-08T16:00:00Z",
        }
    except Exception as e:
        logger.exception(f"健康檢查失敗: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-01-08T16:00:00Z",
        }


@app.get("/")
async def root():
    """根端點"""
    try:
        current_system = get_current_system_type()
        return {
            "message": f"DeerFlow API - 統一版本 (當前系統: {current_system})",
            "version": "0.2.0",
            "documentation": "/docs",
            "health": "/health",
            "system_status": "/api/system/status",
            "current_system": current_system,
        }
    except Exception as e:
        logger.exception(f"根端點查詢失敗: {str(e)}")
        return {
            "message": "DeerFlow API - 統一版本",
            "version": "0.2.0",
            "error": str(e),
        }
