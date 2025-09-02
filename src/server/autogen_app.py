# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 兼容的 FastAPI 應用程序

提供與現有 API 完全相容的 AutoGen 接口。
"""

import base64
import json
import os
from typing import Annotated, List, cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from src.config.report_style import ReportStyle
from src.llms.llm import get_configured_llm_models
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
from src.deerflow_logging import get_simple_logger as get_logger
from src.config.tools import SELECTED_RAG_PROVIDER

# 導入 AutoGen 相容性組件
from src.autogen_system.compatibility import (
    autogen_api_server,
    get_autogen_chat_stream,
)

logger = get_logger(__name__)

INTERNAL_SERVER_ERROR_DETAIL = "Internal Server Error"

# 創建 FastAPI 應用
app = FastAPI(
    title="DeerFlow API (AutoGen Compatible)",
    description="API for Deer - AutoGen Compatible Version",
    version="0.2.0",
)

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    聊天流式端點 - AutoGen 版本

    使用 AutoGen 系統處理聊天請求，但保持與原有 API 的相容性。
    """
    logger.info("AutoGen Chat stream started")

    try:
        # 使用 AutoGen API 服務器處理請求
        return await get_autogen_chat_stream(request)

    except Exception as e:
        logger.error(f"AutoGen 聊天流處理失敗: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/chat/stream/legacy")
async def chat_stream_legacy(request: ChatRequest):
    """
    聊天流式端點 - 舊版 LangGraph

    保留原有的 LangGraph 實現作為備用。
    """
    # 導入原有的實現
    from src.server.app import _astream_workflow_generator
    from src.graph.builder import build_graph_with_memory

    thread_id = request.thread_id
    if thread_id == "__default__":
        thread_id = str(uuid4())

    logger.info("Legacy Chat stream started")

    # 使用原有的 LangGraph 實現
    graph = build_graph_with_memory()

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


@app.get("/api/autogen/status")
async def autogen_status():
    """
    AutoGen 系統狀態端點

    返回 AutoGen 系統的運行狀態和功能信息。
    """
    try:
        status = autogen_api_server.get_server_status()
        return {
            "autogen_system": status,
            "api_version": "0.2.0",
            "compatibility_mode": "full",
            "available_endpoints": {
                "/api/chat/stream": "AutoGen 聊天流（預設）",
                "/api/chat/stream/legacy": "LangGraph 聊天流（舊版）",
                "/api/autogen/status": "系統狀態",
                "/api/autogen/workflow": "工作流調用",
                "/api/autogen/compatibility": "相容性測試",
            },
        }
    except Exception as e:
        logger.error(f"狀態查詢失敗: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/autogen/workflow")
async def autogen_workflow(input_data: dict, config: dict = None):
    """
    AutoGen 工作流調用端點

    直接調用 AutoGen 工作流，支援 LangGraph 相容格式。
    """
    try:
        from src.autogen_system.compatibility import invoke_autogen_workflow

        result = await invoke_autogen_workflow(input_data, config)
        return result

    except Exception as e:
        logger.error(f"AutoGen 工作流調用失敗: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.get("/api/autogen/compatibility")
async def compatibility_test():
    """
    相容性測試端點

    測試 AutoGen 系統與現有 API 的相容性。
    """
    try:
        # 執行簡單的相容性測試
        test_input = {"messages": [{"role": "user", "content": "測試 AutoGen 相容性"}]}

        compatibility_layer = autogen_api_server.get_compatibility_layer()
        result = await compatibility_layer.ainvoke(test_input)

        return {
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

    except Exception as e:
        logger.error(f"相容性測試失敗: {e}")
        return {
            "compatibility_status": "error",
            "error": str(e),
            "autogen_features": {
                "interactive_workflow": False,
                "tool_integration": False,
                "human_feedback": False,
                "langgraph_compatibility": False,
            },
        }


# 保留所有原有的端點
@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """文字轉語音端點"""
    # 導入原有的實現
    from src.server.app import text_to_speech as original_tts

    return await original_tts(request)


@app.post("/api/podcast/generate")
async def generate_podcast(request: GeneratePodcastRequest):
    """生成播客端點"""
    try:
        # 可以選擇使用 AutoGen 或原有實現
        # 這裡保留原有實現
        from src.podcast.graph.builder import build_graph as build_podcast_graph

        report_content = request.content
        workflow = build_podcast_graph()
        final_state = workflow.invoke({"input": report_content})
        audio_bytes = final_state["output"]
        return Response(content=audio_bytes, media_type="audio/mp3")

    except Exception as e:
        logger.exception(f"Error occurred during podcast generation: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/ppt/generate")
async def generate_ppt(request: GeneratePPTRequest):
    """生成 PPT 端點"""
    try:
        # 可以選擇使用 AutoGen 或原有實現
        # 這裡保留原有實現
        from src.ppt.graph.builder import build_graph as build_ppt_graph

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
        logger.exception(f"Error occurred during ppt generation: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/prose/generate")
async def generate_prose(request: GenerateProseRequest):
    """生成散文端點"""
    try:
        # 可以選擇使用 AutoGen 或原有實現
        # 這裡保留原有實現
        from src.prose.graph.builder import build_graph as build_prose_graph

        sanitized_prompt = request.prompt.replace("\r\n", "").replace("\n", "")
        logger.info(f"Generating prose for prompt: {sanitized_prompt}")

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
        logger.exception(f"Error occurred during prose generation: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/prompt/enhance")
async def enhance_prompt(request: EnhancePromptRequest):
    """增強提示端點"""
    try:
        # 可以選擇使用 AutoGen 或原有實現
        # 這裡保留原有實現
        from src.prompt_enhancer.graph.builder import build_graph as build_prompt_enhancer_graph

        sanitized_prompt = request.prompt.replace("\r\n", "").replace("\n", "")
        logger.info(f"Enhancing prompt: {sanitized_prompt}")

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
        logger.exception(f"Error occurred during prompt enhancement: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/mcp/server/metadata", response_model=MCPServerMetadataResponse)
async def mcp_server_metadata(request: MCPServerMetadataRequest):
    """MCP 服務器元數據端點"""
    # 導入原有的實現
    from src.server.app import mcp_server_metadata as original_mcp

    return await original_mcp(request)


@app.get("/api/rag/config", response_model=RAGConfigResponse)
async def rag_config():
    """RAG 配置端點"""
    return RAGConfigResponse(provider=SELECTED_RAG_PROVIDER)


@app.get("/api/rag/resources", response_model=RAGResourcesResponse)
async def rag_resources(request: Annotated[RAGResourceRequest, Query()]):
    """RAG 資源端點"""
    retriever = build_retriever()
    if retriever:
        return RAGResourcesResponse(resources=retriever.list_resources(request.query))
    return RAGResourcesResponse(resources=[])


@app.get("/api/config", response_model=ConfigResponse)
async def config():
    """系統配置端點"""
    return ConfigResponse(
        rag=RAGConfigResponse(provider=SELECTED_RAG_PROVIDER),
        models=get_configured_llm_models(),
    )


# 添加健康檢查端點
@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "version": "0.2.0",
        "system": "autogen",
        "timestamp": "2025-01-08T16:00:00Z",
    }


@app.get("/")
async def root():
    """根端點"""
    return {
        "message": "DeerFlow API - AutoGen Compatible Version",
        "version": "0.2.0",
        "documentation": "/docs",
        "health": "/health",
        "autogen_status": "/api/autogen/status",
    }
