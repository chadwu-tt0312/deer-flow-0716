# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
響應映射器

負責將 AutoGen 系統的響應轉換為前端期望的格式。
"""

import json
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime

from src.deerflow_logging import get_logger

logger = get_logger(__name__)


class ResponseMapper:
    """
    響應映射器

    將 AutoGen 系統響應轉換為前端兼容格式。
    """

    @staticmethod
    def map_execution_result(autogen_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        映射執行結果

        Args:
            autogen_result: AutoGen 執行結果

        Returns:
            Dict[str, Any]: 映射後的結果
        """
        if not autogen_result:
            return ResponseMapper._create_empty_result()

        success = autogen_result.get("success", False)

        if success:
            return {
                "success": True,
                "research_topic": autogen_result.get("research_topic", ""),
                "final_report": autogen_result.get("final_report", ""),
                "execution_time": autogen_result.get("execution_time", 0),
                "plan": autogen_result.get("workflow_plan", {}),
                "execution_metadata": {
                    "session_id": autogen_result.get("session_id"),
                    "interaction_enabled": autogen_result.get("interaction_enabled", False),
                    "timestamp": autogen_result.get("timestamp"),
                    "execution_result": autogen_result.get("execution_result", {}),
                },
            }
        else:
            return {
                "success": False,
                "error": autogen_result.get("error", "未知錯誤"),
                "timestamp": autogen_result.get("timestamp"),
                "session_id": autogen_result.get("session_id"),
                "execution_metadata": {
                    "error_details": autogen_result.get("error", ""),
                    "failed_at": autogen_result.get("timestamp"),
                },
            }

    @staticmethod
    def map_plan_data(autogen_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        映射計劃數據

        Args:
            autogen_plan: AutoGen 計劃數據

        Returns:
            Dict[str, Any]: 映射後的計劃
        """
        if not autogen_plan:
            return {}

        return {
            "plan_id": autogen_plan.get("plan_id", autogen_plan.get("id", "")),
            "name": autogen_plan.get("name", "研究計劃"),
            "description": autogen_plan.get("description", ""),
            "steps": ResponseMapper._map_plan_steps(autogen_plan.get("steps", [])),
            "metadata": autogen_plan.get("metadata", {}),
            "estimated_time": ResponseMapper._calculate_estimated_time(
                autogen_plan.get("steps", [])
            ),
            "created_at": autogen_plan.get("created_at"),
            "status": autogen_plan.get("status", "pending"),
        }

    @staticmethod
    def _map_plan_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """映射計劃步驟"""
        mapped_steps = []

        for i, step in enumerate(steps):
            mapped_step = {
                "step_id": step.get("step_id", step.get("id", f"step_{i}")),
                "step_type": step.get("step_type", "research"),
                "description": step.get("description", f"步驟 {i + 1}"),
                "expected_output": step.get("expected_output", ""),
                "dependencies": step.get("dependencies", []),
                "status": step.get("status", "pending"),
                "agent_type": step.get("agent_type", "researcher"),
                "inputs": step.get("inputs", {}),
                "estimated_time": step.get("timeout_seconds", 60),
            }
            mapped_steps.append(mapped_step)

        return mapped_steps

    @staticmethod
    def _calculate_estimated_time(steps: List[Dict[str, Any]]) -> int:
        """計算預估執行時間（分鐘）"""
        total_seconds = sum(step.get("timeout_seconds", 60) for step in steps)
        return max(1, total_seconds // 60)  # 至少 1 分鐘

    @staticmethod
    def _create_empty_result() -> Dict[str, Any]:
        """創建空結果"""
        return {
            "success": False,
            "error": "無執行結果",
            "timestamp": datetime.now().isoformat(),
            "execution_metadata": {
                "error_details": "結果為空或無效",
                "failed_at": datetime.now().isoformat(),
            },
        }


class StreamResponseMapper:
    """
    流式響應映射器

    處理流式響應的格式轉換。
    """

    @staticmethod
    async def map_stream_events(
        autogen_stream: AsyncGenerator[Dict[str, Any], None],
    ) -> AsyncGenerator[str, None]:
        """
        映射流式事件為 SSE 格式

        Args:
            autogen_stream: AutoGen 流式事件

        Yields:
            str: SSE 格式的事件字符串
        """
        try:
            async for event in autogen_stream:
                sse_event = StreamResponseMapper._convert_to_sse(event)
                if sse_event:
                    yield sse_event

        except Exception as e:
            logger.error(f"流式響應映射失敗: {e}")
            # 發送錯誤事件
            error_event = StreamResponseMapper._create_error_sse(str(e))
            yield error_event

    @staticmethod
    def _convert_to_sse(event: Dict[str, Any]) -> str:
        """將事件轉換為 SSE 格式"""
        event_type = event.get("event", "message_chunk")
        data = event.get("data", {})

        # 清理空內容
        if data.get("content") == "":
            data.pop("content", None)

        # 構建 SSE 事件
        sse_lines = [f"event: {event_type}"]
        sse_lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
        sse_lines.append("")  # 空行表示事件結束

        return "\n".join(sse_lines) + "\n"

    @staticmethod
    def _create_error_sse(error_message: str) -> str:
        """創建錯誤 SSE 事件"""
        error_data = {
            "thread_id": "error",
            "agent": "system",
            "id": f"error_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "role": "assistant",
            "content": f"❌ 錯誤: {error_message}",
            "finish_reason": "error",
        }

        sse_lines = ["event: error"]
        sse_lines.append(f"data: {json.dumps(error_data, ensure_ascii=False)}")
        sse_lines.append("")

        return "\n".join(sse_lines) + "\n"

    @staticmethod
    def map_message_chunk(
        content: str,
        thread_id: str,
        agent: str = "assistant",
        finish_reason: str = None,
        additional_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        映射訊息塊

        Args:
            content: 訊息內容
            thread_id: 執行緒 ID
            agent: 智能體名稱
            finish_reason: 完成原因
            additional_data: 額外數據

        Returns:
            Dict[str, Any]: 映射後的事件數據
        """
        event_data = {
            "thread_id": thread_id,
            "agent": agent,
            "id": f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "role": "assistant",
            "content": content,
        }

        if finish_reason:
            event_data["finish_reason"] = finish_reason

        if additional_data:
            event_data.update(additional_data)

        return {"event": "message_chunk", "data": event_data}

    @staticmethod
    def map_tool_call(
        tool_call_data: Dict[str, Any], thread_id: str, agent: str = "assistant"
    ) -> Dict[str, Any]:
        """
        映射工具調用事件

        Args:
            tool_call_data: 工具調用數據
            thread_id: 執行緒 ID
            agent: 智能體名稱

        Returns:
            Dict[str, Any]: 映射後的工具調用事件
        """
        return {
            "event": "tool_calls",
            "data": {
                "thread_id": thread_id,
                "agent": agent,
                "id": f"tool_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                "role": "assistant",
                "content": "",
                "tool_calls": tool_call_data.get("tool_calls", []),
                "tool_call_chunks": tool_call_data.get("tool_call_chunks", []),
            },
        }

    @staticmethod
    def map_tool_result(
        tool_result: Dict[str, Any], thread_id: str, tool_call_id: str
    ) -> Dict[str, Any]:
        """
        映射工具執行結果

        Args:
            tool_result: 工具執行結果
            thread_id: 執行緒 ID
            tool_call_id: 工具調用 ID

        Returns:
            Dict[str, Any]: 映射後的工具結果事件
        """
        return {
            "event": "tool_call_result",
            "data": {
                "thread_id": thread_id,
                "agent": "tool",
                "id": f"result_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                "role": "assistant",
                "content": str(tool_result.get("result", "")),
                "tool_call_id": tool_call_id,
            },
        }


# 便利函數
def map_autogen_to_frontend(autogen_result: Dict[str, Any]) -> Dict[str, Any]:
    """將 AutoGen 結果映射為前端格式"""
    return ResponseMapper.map_execution_result(autogen_result)


async def stream_autogen_to_frontend(
    autogen_stream: AsyncGenerator[Dict[str, Any], None],
) -> AsyncGenerator[str, None]:
    """將 AutoGen 流式響應映射為前端 SSE 格式"""
    async for sse_event in StreamResponseMapper.map_stream_events(autogen_stream):
        yield sse_event
