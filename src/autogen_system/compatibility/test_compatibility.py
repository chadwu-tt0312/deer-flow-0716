# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
API 相容性測試

驗證 AutoGen 系統與現有 API 的相容性。
"""

import asyncio
import json
from typing import Dict, Any, List
from datetime import datetime


# Mock AutoGen classes for compatibility
class MockOpenAIChatCompletionClient:
    """Mock OpenAIChatCompletionClient for compatibility"""

    def __init__(self, *args, **kwargs):
        self.config = kwargs.get("config", {})
        self.api_key = kwargs.get("api_key", "mock_key")
        self.base_url = kwargs.get("base_url", "https://api.openai.com/v1")

    def get(self, key, default=None):
        """Mock get method for config access"""
        if hasattr(self, key):
            return getattr(self, key)
        return self.config.get(key, default)

    def __getattr__(self, name):
        """Handle any other attribute access"""
        return lambda *args, **kwargs: None


OpenAIChatCompletionClient = MockOpenAIChatCompletionClient

from src.logging import get_logger
from src.config.report_style import ReportStyle
from ..controllers.conversation_manager import ConversationConfig
from .api_adapter import AutoGenAPIAdapter
from .langgraph_compatibility import LangGraphCompatibilityLayer
from .response_mapper import ResponseMapper, StreamResponseMapper

logger = get_logger(__name__)


class CompatibilityTester:
    """
    相容性測試器

    測試 AutoGen 系統與現有 API 的相容性。
    """

    def __init__(self):
        """初始化測試器"""
        # 創建模擬的模型客戶端
        self.model_client = OpenAIChatCompletionClient(model="gpt-4", api_key="test-key")

        self.api_adapter = AutoGenAPIAdapter(self.model_client)
        self.compatibility_layer = LangGraphCompatibilityLayer(self.model_client)

        self.test_results = []

        logger.info("相容性測試器初始化完成")

    async def run_all_tests(self) -> Dict[str, Any]:
        """運行所有相容性測試"""
        logger.info("開始運行相容性測試")

        test_suite = [
            ("API 適配器測試", self.test_api_adapter),
            ("LangGraph 相容性測試", self.test_langgraph_compatibility),
            ("響應映射測試", self.test_response_mapping),
            ("流式響應測試", self.test_stream_response),
            ("請求格式相容性測試", self.test_request_format_compatibility),
            ("錯誤處理測試", self.test_error_handling),
        ]

        results = {}
        passed = 0
        total = len(test_suite)

        for test_name, test_func in test_suite:
            try:
                logger.info(f"運行測試: {test_name}")
                result = await test_func()
                results[test_name] = result

                if result.get("passed", False):
                    passed += 1
                    logger.info(f"✅ {test_name} - 通過")
                else:
                    logger.warning(f"❌ {test_name} - 失敗: {result.get('error', '未知錯誤')}")

            except Exception as e:
                logger.error(f"❌ {test_name} - 異常: {e}")
                results[test_name] = {"passed": False, "error": str(e), "exception": True}

        summary = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": (passed / total) * 100 if total > 0 else 0,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"相容性測試完成 - 通過率: {summary['success_rate']:.1f}%")
        return summary

    async def test_api_adapter(self) -> Dict[str, Any]:
        """測試 API 適配器"""
        try:
            # 模擬聊天請求
            messages = [{"role": "user", "content": "測試 AutoGen API 適配器"}]

            # 收集事件
            events = []
            async for event in self.api_adapter.process_chat_request(
                messages=messages,
                thread_id="test_thread",
                max_plan_iterations=1,
                max_step_num=2,
                auto_accepted_plan=True,
                enable_background_investigation=False,
            ):
                events.append(event)
                # 限制事件數量以避免無限循環
                if len(events) >= 10:
                    break

            # 驗證結果
            has_status_event = any(
                "工作流開始" in str(event.get("data", {}).get("content", "")) for event in events
            )

            return {
                "passed": len(events) > 0 and has_status_event,
                "events_count": len(events),
                "has_status_event": has_status_event,
                "sample_event": events[0] if events else None,
            }

        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def test_langgraph_compatibility(self) -> Dict[str, Any]:
        """測試 LangGraph 相容性"""
        try:
            # 測試 ainvoke
            input_data = {"messages": [{"role": "user", "content": "測試 LangGraph 相容性"}]}

            result = await self.compatibility_layer.ainvoke(input_data)

            # 驗證結果格式
            has_messages = "messages" in result
            has_final_report = "final_report" in result
            has_metadata = "execution_metadata" in result

            # 測試 astream
            events = []
            async for event in self.compatibility_layer.astream(input_data):
                events.append(event)
                if len(events) >= 5:  # 限制事件數量
                    break

            return {
                "passed": has_messages and has_metadata and len(events) > 0,
                "ainvoke_result": {
                    "has_messages": has_messages,
                    "has_final_report": has_final_report,
                    "has_metadata": has_metadata,
                },
                "astream_events": len(events),
                "sample_event_format": type(events[0]).__name__ if events else None,
            }

        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def test_response_mapping(self) -> Dict[str, Any]:
        """測試響應映射"""
        try:
            # 測試成功結果映射
            autogen_result = {
                "success": True,
                "research_topic": "測試主題",
                "final_report": "測試報告",
                "execution_time": 10.5,
                "workflow_plan": {
                    "id": "test_plan",
                    "name": "測試計劃",
                    "steps": [
                        {"step_id": "step_1", "description": "測試步驟", "step_type": "research"}
                    ],
                },
                "session_id": "test_session",
                "timestamp": datetime.now().isoformat(),
            }

            mapped_result = ResponseMapper.map_execution_result(autogen_result)

            # 驗證映射結果
            has_success = mapped_result.get("success") == True
            has_topic = "research_topic" in mapped_result
            has_report = "final_report" in mapped_result
            has_metadata = "execution_metadata" in mapped_result

            # 測試失敗結果映射
            error_result = {
                "success": False,
                "error": "測試錯誤",
                "timestamp": datetime.now().isoformat(),
            }

            mapped_error = ResponseMapper.map_execution_result(error_result)
            has_error = mapped_error.get("success") == False and "error" in mapped_error

            return {
                "passed": has_success and has_topic and has_report and has_metadata and has_error,
                "success_mapping": {
                    "has_success": has_success,
                    "has_topic": has_topic,
                    "has_report": has_report,
                    "has_metadata": has_metadata,
                },
                "error_mapping": has_error,
            }

        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def test_stream_response(self) -> Dict[str, Any]:
        """測試流式響應"""
        try:
            # 創建模擬的 AutoGen 流
            async def mock_autogen_stream():
                events = [
                    {
                        "event": "message_chunk",
                        "data": {
                            "thread_id": "test",
                            "agent": "system",
                            "content": "測試內容",
                            "id": "test_1",
                        },
                    },
                    {
                        "event": "message_chunk",
                        "data": {
                            "thread_id": "test",
                            "agent": "assistant",
                            "content": "完成",
                            "finish_reason": "stop",
                            "id": "test_2",
                        },
                    },
                ]

                for event in events:
                    yield event

            # 測試流式映射
            sse_events = []
            async for sse_event in StreamResponseMapper.map_stream_events(mock_autogen_stream()):
                sse_events.append(sse_event)

            # 驗證 SSE 格式
            valid_sse = all(event.startswith("event:") and "data:" in event for event in sse_events)

            return {
                "passed": len(sse_events) == 2 and valid_sse,
                "sse_events_count": len(sse_events),
                "valid_sse_format": valid_sse,
                "sample_sse": sse_events[0] if sse_events else None,
            }

        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def test_request_format_compatibility(self) -> Dict[str, Any]:
        """測試請求格式相容性"""
        try:
            # 測試不同的請求格式
            test_cases = [
                # 標準格式
                {
                    "messages": [{"role": "user", "content": "標準格式測試"}],
                    "thread_id": "test1",
                    "max_plan_iterations": 1,
                },
                # 空訊息
                {"messages": [], "thread_id": "test2"},
                # 多模態內容
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "多模態測試"},
                                {"type": "text", "text": "第二部分"},
                            ],
                        }
                    ],
                    "thread_id": "test3",
                },
            ]

            results = []
            for i, test_case in enumerate(test_cases):
                try:
                    # 測試參數解析
                    messages = test_case.get("messages", [])
                    user_input = self.api_adapter._extract_user_input(messages)

                    config = self.api_adapter._create_autogen_config(
                        max_plan_iterations=test_case.get("max_plan_iterations", 1),
                        max_step_num=3,
                        max_search_results=3,
                        auto_accepted_plan=True,
                        enable_background_investigation=False,
                        enable_deep_thinking=False,
                    )

                    results.append(
                        {
                            "test_case": i + 1,
                            "success": True,
                            "user_input_extracted": bool(user_input) or len(messages) == 0,
                            "config_created": isinstance(config, ConversationConfig),
                        }
                    )

                except Exception as e:
                    results.append({"test_case": i + 1, "success": False, "error": str(e)})

            all_passed = all(result.get("success", False) for result in results)

            return {
                "passed": all_passed,
                "test_cases": len(test_cases),
                "passed_cases": sum(1 for r in results if r.get("success", False)),
                "results": results,
            }

        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def test_error_handling(self) -> Dict[str, Any]:
        """測試錯誤處理"""
        try:
            # 測試無效輸入
            error_cases = []

            # 測試空訊息的錯誤處理
            events = []
            async for event in self.api_adapter.process_chat_request(
                messages=[], thread_id="error_test", auto_accepted_plan=True
            ):
                events.append(event)
                if len(events) >= 3:  # 限制事件數量
                    break

            has_error_event = any(
                event.get("event") == "error"
                or "錯誤" in str(event.get("data", {}).get("content", ""))
                for event in events
            )

            error_cases.append(
                {
                    "case": "empty_messages",
                    "has_error_event": has_error_event,
                    "events_count": len(events),
                }
            )

            # 測試 LangGraph 相容性錯誤處理
            try:
                invalid_result = await self.compatibility_layer.ainvoke(None)
                langgraph_error_handled = "error" in str(invalid_result).lower()
            except:
                langgraph_error_handled = True  # 異常被正確拋出

            error_cases.append(
                {"case": "langgraph_invalid_input", "error_handled": langgraph_error_handled}
            )

            return {
                "passed": all(
                    case.get("has_error_event", case.get("error_handled", False))
                    for case in error_cases
                ),
                "error_cases": error_cases,
            }

        except Exception as e:
            return {"passed": False, "error": str(e)}


# 便利函數
async def run_compatibility_tests() -> Dict[str, Any]:
    """運行相容性測試"""
    tester = CompatibilityTester()
    return await tester.run_all_tests()


async def quick_compatibility_check() -> bool:
    """快速相容性檢查"""
    try:
        tester = CompatibilityTester()

        # 簡單的 API 適配器測試
        result = await tester.test_api_adapter()
        return result.get("passed", False)

    except Exception:
        return False


if __name__ == "__main__":
    # 運行測試
    async def main():
        print("開始 AutoGen API 相容性測試...")
        results = await run_compatibility_tests()

        print(f"\n測試結果摘要:")
        print(f"總測試數: {results['total_tests']}")
        print(f"通過: {results['passed']}")
        print(f"失敗: {results['failed']}")
        print(f"成功率: {results['success_rate']:.1f}%")

        if results["success_rate"] >= 80:
            print("\n✅ 相容性測試大部分通過，系統可以使用")
        else:
            print("\n❌ 相容性測試失敗較多，建議檢查系統配置")

    asyncio.run(main())
