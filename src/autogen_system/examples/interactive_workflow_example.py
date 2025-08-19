# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 互動式工作流範例

展示如何使用互動式功能進行研究工作流。
"""

import asyncio
import json
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
from ..interaction import (
    InteractiveWorkflowManager,
    run_interactive_research,
    run_non_interactive_research,
    display_welcome_message,
)
from ..controllers.conversation_manager import ConversationConfig

logger = get_logger(__name__)


async def example_interactive_research():
    """互動式研究工作流範例"""
    print("\n=== 互動式研究工作流範例 ===\n")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4",
        api_key="your-api-key",  # 請替換為實際的 API 密鑰
    )

    # 互動式配置
    config = ConversationConfig(
        enable_background_investigation=True,
        max_plan_iterations=3,
        max_step_iterations=5,
        enable_human_feedback=True,  # 啟用人工反饋
        auto_accept_plan=False,  # 不自動接受計劃
        debug_mode=True,
    )

    # 用戶查詢
    user_input = "研究人工智慧在教育領域的應用前景和挑戰"

    try:
        print("🚀 啟動互動式研究工作流...")
        print(f"研究主題: {user_input}\n")

        # 執行互動式研究
        result = await run_interactive_research(
            user_input, model_client, enable_interaction=True, config=config
        )

        # 顯示執行結果
        print("\n" + "📊" * 30)
        print("執行結果摘要")
        print("📊" * 30)

        print(f"✅ 執行狀態: {'成功' if result.get('success') else '失敗'}")
        print(f"🔍 研究主題: {result.get('research_topic', '未知')}")
        print(f"⏱️  執行時間: {result.get('execution_time', 0):.2f} 秒")
        print(f"🔗 會話ID: {result.get('session_id', '未知')}")
        print(f"🤝 互動模式: {'啟用' if result.get('interaction_enabled') else '停用'}")

        if result.get("success"):
            execution_result = result.get("execution_result", {})
            print(f"\n📈 執行詳情:")
            print(f"  - 計劃狀態: {execution_result.get('plan_status', '未知')}")
            print(f"  - 總步驟數: {execution_result.get('total_steps', 0)}")
            print(
                f"  - 完成步驟: {execution_result.get('steps_by_status', {}).get('completed', 0)}"
            )
            print(f"  - 失敗步驟: {execution_result.get('steps_by_status', {}).get('failed', 0)}")

            # 顯示部分報告
            final_report = result.get("final_report", "")
            if final_report:
                print(f"\n📄 報告預覽:")
                report_preview = (
                    final_report[:300] + "..." if len(final_report) > 300 else final_report
                )
                print(report_preview)
        else:
            print(f"\n❌ 錯誤: {result.get('error', '未知錯誤')}")

    except Exception as e:
        logger.error(f"互動式研究範例執行失敗: {e}")
        print(f"執行失敗: {e}")


async def example_non_interactive_research():
    """非互動式研究工作流範例"""
    print("\n=== 非互動式研究工作流範例 ===\n")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4",
        api_key="your-api-key",  # 請替換為實際的 API 密鑰
    )

    # 非互動式配置
    config = ConversationConfig(
        enable_background_investigation=True,
        max_plan_iterations=2,
        max_step_iterations=3,
        enable_human_feedback=False,  # 停用人工反饋
        auto_accept_plan=True,  # 自動接受計劃
        debug_mode=False,
    )

    # 用戶查詢
    user_input = "分析區塊鏈技術在供應鏈管理中的優勢和局限性"

    try:
        print("🤖 啟動自動化研究工作流...")
        print(f"研究主題: {user_input}\n")

        # 執行非互動式研究
        result = await run_non_interactive_research(user_input, model_client, config)

        # 顯示簡化的結果
        print(f"執行狀態: {'✅ 成功' if result.get('success') else '❌ 失敗'}")
        print(f"執行時間: {result.get('execution_time', 0):.2f} 秒")

        if result.get("success"):
            print("\n自動化工作流執行完成！")
        else:
            print(f"執行失敗: {result.get('error')}")

    except Exception as e:
        logger.error(f"非互動式研究範例執行失敗: {e}")
        print(f"執行失敗: {e}")


async def example_custom_interactive_workflow():
    """自定義互動式工作流範例"""
    print("\n=== 自定義互動式工作流範例 ===\n")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4",
        api_key="your-api-key",  # 請替換為實際的 API 密鑰
    )

    # 自定義配置
    config = ConversationConfig(
        enable_background_investigation=True,
        max_plan_iterations=3,
        max_step_iterations=7,
        enable_human_feedback=True,
        auto_accept_plan=False,
        timeout_seconds=600,
        debug_mode=True,
    )

    # 創建互動式工作流管理器
    interactive_manager = InteractiveWorkflowManager(model_client, config, enable_interaction=True)

    try:
        # 用戶查詢
        user_input = "評估虛擬實境技術在醫療訓練中的應用效果"

        print("🎮 啟動自定義互動式工作流...")
        print(f"查詢: {user_input}\n")

        # 執行工作流
        result = await interactive_manager.run_interactive_research_workflow(user_input)

        # 顯示詳細狀態
        execution_status = interactive_manager.get_execution_status()
        print(f"\n📊 詳細執行狀態:")
        print(f"  - 工作流狀態: {execution_status.get('status')}")
        print(f"  - 當前步驟: {execution_status.get('current_step')}")
        print(f"  - 總步驟數: {execution_status.get('total_steps')}")
        print(f"  - 暫停狀態: {execution_status.get('paused')}")
        print(f"  - 會話ID: {execution_status.get('session_id')}")

        # 反饋統計
        feedback_stats = execution_status.get("feedback_stats", {})
        if feedback_stats.get("total_requests", 0) > 0:
            print(f"\n💬 互動統計:")
            print(f"  - 總反饋請求: {feedback_stats.get('total_requests', 0)}")
            print(f"  - 批准率: {feedback_stats.get('approval_rate', 0):.1f}%")
            print(f"  - 平均回應時間: {feedback_stats.get('average_response_time', 0):.1f}秒")

        # 最終結果
        if result.get("success"):
            print(f"\n🎉 工作流執行成功！")
            print(f"總執行時間: {result.get('execution_time', 0):.2f} 秒")
        else:
            print(f"\n❌ 工作流執行失敗: {result.get('error')}")

    except Exception as e:
        logger.error(f"自定義互動式工作流執行失敗: {e}")
        print(f"執行失敗: {e}")

    finally:
        await interactive_manager.cleanup()


async def example_workflow_control():
    """工作流控制範例"""
    print("\n=== 工作流控制範例 ===\n")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4",
        api_key="your-api-key",  # 請替換為實際的 API 密鑰
    )

    # 配置
    config = ConversationConfig(
        enable_background_investigation=True,
        max_plan_iterations=2,
        max_step_iterations=5,
        enable_human_feedback=True,
        auto_accept_plan=False,
    )

    # 創建互動式管理器
    interactive_manager = InteractiveWorkflowManager(model_client, config, enable_interaction=True)

    try:
        print("🎛️  工作流控制示範...")

        # 模擬工作流控制操作
        print("\n📋 可用控制操作:")
        print("1. ⏸️  暫停工作流")
        print("2. ▶️  恢復工作流")
        print("3. ⏹️  停止工作流")
        print("4. 📊 查看狀態")

        # 展示狀態查詢
        status = interactive_manager.get_execution_status()
        print(f"\n當前狀態: {status.get('status')}")

        # 模擬暫停操作
        print("\n⏸️  執行暫停操作...")
        paused = await interactive_manager.pause_workflow()
        print(f"暫停結果: {'成功' if paused else '失敗'}")

        # 模擬恢復操作
        print("\n▶️  執行恢復操作...")
        resumed = await interactive_manager.resume_workflow()
        print(f"恢復結果: {'成功' if resumed else '失敗'}")

        # 模擬停止操作
        print("\n⏹️  執行停止操作...")
        stopped = await interactive_manager.stop_workflow()
        print(f"停止結果: {'成功' if stopped else '失敗'}")

        print("\n✅ 工作流控制示範完成")

    except Exception as e:
        logger.error(f"工作流控制範例失敗: {e}")
        print(f"控制示範失敗: {e}")

    finally:
        await interactive_manager.cleanup()


async def main():
    """主函數 - 執行所有互動式範例"""
    # 顯示歡迎訊息
    await display_welcome_message()

    print("\nAutoGen 互動式工作流範例")
    print("=" * 60)

    try:
        # 執行各種範例
        await example_interactive_research()
        await example_non_interactive_research()
        await example_custom_interactive_workflow()
        await example_workflow_control()

        print("\n" + "=" * 60)
        print("🎉 所有互動式範例執行完成！")
        print("=" * 60)
        print("\n💡 互動式功能特色:")
        print("✅ 計劃審查和修改")
        print("⏸️  工作流暫停和恢復")
        print("🛠️  智能錯誤處理")
        print("📊 即時進度監控")
        print("🤝 人機協作決策")

    except KeyboardInterrupt:
        print("\n範例執行被中斷")
    except Exception as e:
        logger.error(f"範例執行異常: {e}")
        print(f"範例執行異常: {e}")


if __name__ == "__main__":
    # 執行範例
    asyncio.run(main())
