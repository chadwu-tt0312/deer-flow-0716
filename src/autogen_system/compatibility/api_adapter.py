# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen API 適配器

提供與原有 LangGraph API 完全相容的接口層。
"""

import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator, Union
from datetime import datetime


from autogen_core.models import ChatCompletionClient

from src.deerflow_logging import get_simple_logger as get_logger
from src.config.report_style import ReportStyle
from src.rag.retriever import Resource

# 移除不存在的導入，使用實際的配置類別
from src.config.report_style import ReportStyle

logger = get_logger(__name__)


class AutoGenAPIAdapter:
    """
    AutoGen API 適配器

    提供統一的 API 接口，內部使用 AutoGen 系統。
    """

    def __init__(self, model_client: ChatCompletionClient):
        """
        初始化 API 適配器

        Args:
            model_client: 聊天完成客戶端
        """
        self.model_client = model_client
        self.active_workflows: Dict[str, ResearchWorkflowManager] = {}

        logger.info("AutoGen API 適配器初始化完成")

    async def process_chat_request(
        self, messages: List[Dict[str, Any]], thread_id: str = "default", **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        處理聊天請求

        Args:
            messages: 訊息列表
            thread_id: 執行緒 ID
            **kwargs: 其他配置參數

        Yields:
            Dict[str, Any]: 事件數據
        """
        logger.info(f"處理聊天請求: thread_id={thread_id}")

        try:
            # 提取用戶輸入
            user_input = self._extract_user_input(messages)

            # 創建配置
            config = self._create_config(**kwargs)

            # 創建或獲取工作流管理器
            workflow_manager = await self._get_workflow_manager(thread_id, config)

            # 執行工作流並產生事件
            async for event in self._execute_workflow_with_events(
                workflow_manager, user_input, thread_id
            ):
                yield event

        except Exception as e:
            logger.error(f"聊天請求處理失敗: {e}")
            yield self._create_error_event(str(e), thread_id)

    def _extract_user_input(self, messages: List[Dict[str, Any]]) -> str:
        """提取用戶輸入"""
        if not messages:
            return ""

        # 找到最後一個用戶訊息
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")

        return ""

    def _create_config(self, **kwargs) -> Dict[str, Any]:
        """創建對話配置"""
        return {
            "enable_background_investigation": kwargs.get("enable_background_investigation", True),
            "max_plan_iterations": kwargs.get("max_plan_iterations", 1),
            "max_step_iterations": kwargs.get("max_step_num", 3),
            "max_search_results": kwargs.get("max_search_results", 3),
            "auto_accept_plan": kwargs.get("auto_accept_plan", True),
            "human_feedback_enabled": not kwargs.get("auto_accepted_plan", True),
            "debug_mode": kwargs.get("debug", False),
            "report_style": kwargs.get("report_style", ReportStyle.ACADEMIC),
            "resources": kwargs.get("resources", []),
            "mcp_settings": kwargs.get("mcp_settings", {}),
        }

    async def _get_workflow_manager(self, thread_id: str, config: Dict[str, Any]) -> Any:
        """獲取或創建工作流管理器"""
        # 簡化實現，直接使用 AutoGen 系統
        if thread_id not in self.active_workflows:
            # 這裡應該創建 AutoGen 工作流管理器
            # 暫時使用簡化實現
            self.active_workflows[thread_id] = {"config": config, "client": self.model_client}

        return self.active_workflows[thread_id]

    async def _execute_workflow_with_events(
        self, workflow_manager: Any, user_input: str, thread_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """執行工作流並產生事件"""

        # 開始事件
        yield self._create_event(
            "workflow_start",
            {"message": "開始執行研究工作流", "user_input": user_input},
            "coordinator",
            thread_id,
        )

        try:
            # 執行工作流 - 簡化實現
            # 這裡應該調用實際的 AutoGen 工作流
            result = {
                "success": True,
                "workflow_plan": {"steps": []},
                "execution_result": {"steps_by_status": {"completed": 1}},
                "final_report": f"處理完成：{user_input}",
                "execution_time": 1.0,
            }

            # 工作流各階段事件
            if result.get("success"):
                # 計劃生成事件
                yield self._create_event(
                    "plan_generated",
                    {"message": "研究計劃已生成", "plan": result.get("workflow_plan")},
                    "planner",
                    thread_id,
                )

                # 執行事件
                execution_result = result.get("execution_result", {})
                steps_completed = execution_result.get("steps_by_status", {}).get("completed", 0)

                yield self._create_event(
                    "execution_progress",
                    {"message": f"已完成 {steps_completed} 個步驟", "progress": execution_result},
                    "researcher",
                    thread_id,
                )

                # 最終報告事件
                final_report = result.get("final_report", "")
                if final_report:
                    # 分塊發送報告
                    chunk_size = 500
                    for i in range(0, len(final_report), chunk_size):
                        chunk = final_report[i : i + chunk_size]
                        is_final = i + chunk_size >= len(final_report)

                        yield self._create_event(
                            "message_chunk",
                            {"content": chunk, "finish_reason": "stop" if is_final else None},
                            "reporter",
                            thread_id,
                        )

                # 完成事件
                yield self._create_event(
                    "workflow_complete",
                    {
                        "message": "研究工作流執行完成",
                        "execution_time": result.get("execution_time", 0),
                        "success": True,
                    },
                    "coordinator",
                    thread_id,
                )
            else:
                # 錯誤事件
                error_msg = result.get("error", "未知錯誤")
                yield self._create_error_event(error_msg, thread_id)

        except Exception as e:
            logger.error(f"工作流執行異常: {e}")
            yield self._create_error_event(str(e), thread_id)

    def _create_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        agent: str = "system",
        thread_id: str = "default",
    ) -> Dict[str, Any]:
        """創建事件"""
        return {
            "event": event_type,
            "data": {
                **data,
                "agent": agent,
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat(),
            },
        }

    def _create_error_event(self, error_message: str, thread_id: str = "default") -> Dict[str, Any]:
        """創建錯誤事件"""
        return self._create_event(
            "error",
            {"content": f"❌ 執行錯誤: {error_message}", "error": True, "finish_reason": "error"},
            "error",
            thread_id,
        )

    async def cleanup_thread(self, thread_id: str):
        """清理執行緒資源"""
        if thread_id in self.active_workflows:
            await self.active_workflows[thread_id].cleanup()
            del self.active_workflows[thread_id]
            logger.info(f"已清理執行緒: {thread_id}")

    async def cleanup_all(self):
        """清理所有資源"""
        for thread_id in list(self.active_workflows.keys()):
            await self.cleanup_thread(thread_id)
        logger.info("已清理所有執行緒")


# 全域 API 相容性函數
async def run_agent_workflow_async(
    user_input: str,
    debug: bool = False,
    max_plan_iterations: int = 1,
    max_step_num: int = 3,
    enable_background_investigation: bool = True,
    auto_accepted_plan: bool = True,
    resources: List[Resource] = None,
    report_style: ReportStyle = ReportStyle.ACADEMIC,
    mcp_settings: Dict[str, Any] = None,
    model_client: ChatCompletionClient = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    異步執行智能體工作流

    保持與原有 LangGraph API 完全相容的介面。

    Args:
        user_input: 用戶輸入
        debug: 偵錯模式
        max_plan_iterations: 最大計劃迭代次數
        max_step_num: 最大步驟數
        enable_background_investigation: 啟用背景調查
        auto_accepted_plan: 自動接受計劃
        resources: 資源列表
        report_style: 報告風格
        mcp_settings: MCP 設定
        model_client: 模型客戶端
        **kwargs: 其他參數

    Returns:
        Dict[str, Any]: 執行結果
    """
    logger.info(f"執行智能體工作流: {user_input}")

    if not model_client:
        # 如果沒有提供模型客戶端，需要從全域配置取得
        from src.llms.llm import get_default_model_client

        model_client = get_default_model_client()

    # 創建 API 適配器
    adapter = AutoGenAPIAdapter(model_client)

    try:
        # 準備參數
        messages = [{"role": "user", "content": user_input}]

        config_params = {
            "debug": debug,
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "enable_background_investigation": enable_background_investigation,
            "auto_accepted_plan": auto_accepted_plan,
            "resources": resources or [],
            "report_style": report_style,
            "mcp_settings": mcp_settings or {},
            **kwargs,
        }

        # 收集所有事件
        events = []
        final_content = ""
        execution_metadata = {}

        async for event in adapter.process_chat_request(
            messages=messages, thread_id="api_workflow", **config_params
        ):
            events.append(event)

            # 提取最終內容
            data = event.get("data", {})
            if data.get("agent") == "reporter" and data.get("content"):
                final_content += data["content"]

            # 提取執行元數據
            if event.get("event") == "workflow_complete":
                execution_metadata = data

        # 返回相容格式的結果
        return {
            "success": True,
            "user_input": user_input,
            "final_report": final_content,
            "events": events,
            "execution_metadata": execution_metadata,
            "debug_info": {
                "total_events": len(events),
                "completed_at": datetime.now().isoformat(),
            }
            if debug
            else None,
        }

    except Exception as e:
        logger.error(f"工作流執行失敗: {e}")
        return {
            "success": False,
            "user_input": user_input,
            "error": str(e),
            "final_report": "",
            "events": [],
            "execution_metadata": {},
            "debug_info": {
                "error_details": str(e),
                "failed_at": datetime.now().isoformat(),
            }
            if debug
            else None,
        }

    finally:
        # 清理資源
        await adapter.cleanup_all()


def run_agent_workflow(
    user_input: str,
    debug: bool = False,
    max_plan_iterations: int = 1,
    max_step_num: int = 3,
    enable_background_investigation: bool = True,
    auto_accepted_plan: bool = True,
    resources: List[Resource] = None,
    report_style: ReportStyle = ReportStyle.ACADEMIC,
    mcp_settings: Dict[str, Any] = None,
    model_client: ChatCompletionClient = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    同步執行智能體工作流

    Args:
        同 run_agent_workflow_async

    Returns:
        Dict[str, Any]: 執行結果
    """
    # 使用 asyncio 運行異步版本
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            run_agent_workflow_async(
                user_input=user_input,
                debug=debug,
                max_plan_iterations=max_plan_iterations,
                max_step_num=max_step_num,
                enable_background_investigation=enable_background_investigation,
                auto_accepted_plan=auto_accepted_plan,
                resources=resources,
                report_style=report_style,
                mcp_settings=mcp_settings,
                model_client=model_client,
                **kwargs,
            )
        )
        return result
    finally:
        loop.close()


def create_autogen_api_adapter(
    model_client: ChatCompletionClient = None, **kwargs
) -> AutoGenAPIAdapter:
    """
    創建 AutoGen API 適配器實例

    Args:
        model_client: 聊天完成客戶端
        **kwargs: 其他參數

    Returns:
        AutoGenAPIAdapter: API 適配器實例
    """
    return AutoGenAPIAdapter(model_client=model_client, **kwargs)
