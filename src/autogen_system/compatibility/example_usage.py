# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
API 相容性層使用範例

展示如何使用 AutoGen API 相容性層。
"""

import asyncio
from typing import Dict, Any


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
from . import (
    AutoGenAPIAdapter,
    LangGraphCompatibilityLayer,
    ResponseMapper,
    StreamResponseMapper,
    run_compatibility_tests,
)

logger = get_logger(__name__)


async def example_api_adapter_usage():
    """API 適配器使用範例"""
    print("=== API 適配器使用範例 ===")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4",
        api_key="your-api-key",  # 請替換為實際的 API 密鑰
    )

    # 創建 API 適配器
    adapter = AutoGenAPIAdapter(model_client)

    # 模擬聊天請求
    messages = [{"role": "user", "content": "請分析人工智慧在醫療領域的應用"}]

    print("開始處理聊天請求...")

    try:
        # 處理請求並收集事件
        events = []
        async for event in adapter.process_chat_request(
            messages=messages,
            thread_id="example_thread",
            max_plan_iterations=1,
            max_step_num=2,
            auto_accepted_plan=True,
            enable_background_investigation=False,
            report_style=ReportStyle.ACADEMIC,
        ):
            events.append(event)
            print(
                f"事件: {event.get('event')} - {event.get('data', {}).get('content', '')[:50]}..."
            )

            # 限制事件數量
            if len(events) >= 5:
                break

        print(f"✅ 成功處理 {len(events)} 個事件")

    except Exception as e:
        print(f"❌ 處理失敗: {e}")


async def example_langgraph_compatibility():
    """LangGraph 相容性範例"""
    print("\n=== LangGraph 相容性範例 ===")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4",
        api_key="your-api-key",  # 請替換為實際的 API 密鑰
    )

    # 創建相容性層
    compatibility_layer = LangGraphCompatibilityLayer(model_client)

    # 模擬 LangGraph 輸入格式
    input_data = {"messages": [{"role": "user", "content": "測試 LangGraph 相容性"}]}

    config = {"thread_id": "langgraph_test", "max_plan_iterations": 1, "auto_accepted_plan": True}

    try:
        print("測試 ainvoke 方法...")
        result = await compatibility_layer.ainvoke(input_data, config)

        print(f"✅ ainvoke 成功")
        print(f"   - 訊息數量: {len(result.get('messages', []))}")
        print(f"   - 有最終報告: {'final_report' in result}")
        print(f"   - 執行狀態: {result.get('execution_metadata', {}).get('success', 'unknown')}")

        print("\n測試 astream 方法...")
        events = []
        async for event in compatibility_layer.astream(input_data, config):
            events.append(event)
            print(f"   事件: {type(event).__name__}")

            # 限制事件數量
            if len(events) >= 3:
                break

        print(f"✅ astream 成功，收到 {len(events)} 個事件")

    except Exception as e:
        print(f"❌ LangGraph 相容性測試失敗: {e}")


async def example_response_mapping():
    """響應映射範例"""
    print("\n=== 響應映射範例 ===")

    # 模擬 AutoGen 執行結果
    autogen_result = {
        "success": True,
        "research_topic": "AI 在醫療領域的應用",
        "final_report": "人工智慧在醫療領域展現出巨大潛力...",
        "execution_time": 15.7,
        "workflow_plan": {
            "id": "plan_123",
            "name": "醫療 AI 研究計劃",
            "description": "深入分析 AI 醫療應用",
            "steps": [
                {
                    "step_id": "research_step",
                    "step_type": "research",
                    "description": "收集 AI 醫療相關資料",
                    "timeout_seconds": 120,
                },
                {
                    "step_id": "analysis_step",
                    "step_type": "analysis",
                    "description": "分析收集到的資料",
                    "timeout_seconds": 180,
                },
            ],
        },
        "session_id": "session_456",
        "timestamp": "2025-01-08T16:00:00Z",
    }

    try:
        # 映射執行結果
        mapped_result = ResponseMapper.map_execution_result(autogen_result)

        print("✅ 執行結果映射成功")
        print(f"   - 成功狀態: {mapped_result.get('success')}")
        print(f"   - 研究主題: {mapped_result.get('research_topic')}")
        print(f"   - 執行時間: {mapped_result.get('execution_time')} 秒")
        print(f"   - 有元數據: {'execution_metadata' in mapped_result}")

        # 映射計劃數據
        mapped_plan = ResponseMapper.map_plan_data(autogen_result["workflow_plan"])

        print(f"\n✅ 計劃映射成功")
        print(f"   - 計劃名稱: {mapped_plan.get('name')}")
        print(f"   - 步驟數量: {len(mapped_plan.get('steps', []))}")
        print(f"   - 預估時間: {mapped_plan.get('estimated_time')} 分鐘")

        # 測試流式響應映射
        print(f"\n測試流式響應映射...")

        async def mock_stream():
            """模擬 AutoGen 流式事件"""
            events = [
                {
                    "event": "message_chunk",
                    "data": {
                        "thread_id": "test",
                        "agent": "researcher",
                        "content": "開始研究...",
                        "id": "msg_1",
                    },
                },
                {
                    "event": "message_chunk",
                    "data": {
                        "thread_id": "test",
                        "agent": "reporter",
                        "content": "研究完成",
                        "finish_reason": "stop",
                        "id": "msg_2",
                    },
                },
            ]

            for event in events:
                yield event

        sse_events = []
        async for sse_event in StreamResponseMapper.map_stream_events(mock_stream()):
            sse_events.append(sse_event)

        print(f"✅ 流式映射成功，生成 {len(sse_events)} 個 SSE 事件")

    except Exception as e:
        print(f"❌ 響應映射測試失敗: {e}")


async def example_compatibility_testing():
    """相容性測試範例"""
    print("\n=== 相容性測試範例 ===")

    try:
        print("運行完整相容性測試...")
        results = await run_compatibility_tests()

        print(f"\n測試結果:")
        print(f"   - 總測試: {results['total_tests']}")
        print(f"   - 通過: {results['passed']}")
        print(f"   - 失敗: {results['failed']}")
        print(f"   - 成功率: {results['success_rate']:.1f}%")

        if results["success_rate"] >= 80:
            print("✅ 相容性測試大部分通過")
        else:
            print("❌ 相容性測試存在問題")

        # 顯示詳細結果
        print(f"\n詳細測試結果:")
        for test_name, result in results["results"].items():
            status = "✅" if result.get("passed", False) else "❌"
            print(f"   {status} {test_name}")
            if not result.get("passed", False) and "error" in result:
                print(f"      錯誤: {result['error']}")

    except Exception as e:
        print(f"❌ 相容性測試失敗: {e}")


async def main():
    """主函數 - 運行所有範例"""
    print("AutoGen API 相容性層使用範例")
    print("=" * 50)

    try:
        await example_api_adapter_usage()
        await example_langgraph_compatibility()
        await example_response_mapping()
        await example_compatibility_testing()

        print("\n" + "=" * 50)
        print("✅ 所有範例執行完成")
        print("\n📚 使用指南:")
        print("1. API 適配器: 處理標準的聊天請求")
        print("2. LangGraph 相容性: 與現有 LangGraph 代碼無縫整合")
        print("3. 響應映射: 確保前端接收正確格式的數據")
        print("4. 相容性測試: 驗證系統集成狀態")

    except Exception as e:
        print(f"\n❌ 範例執行失敗: {e}")


if __name__ == "__main__":
    # 運行範例
    asyncio.run(main())
