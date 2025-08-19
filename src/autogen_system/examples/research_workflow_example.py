# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 研究工作流範例

展示如何使用 AutoGen 系統執行研究工作流。
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


# Mock code executor for compatibility
class MockDockerCommandLineCodeExecutor:
    """Mock DockerCommandLineCodeExecutor for compatibility"""

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        """Handle any attribute access"""
        return lambda *args, **kwargs: None


DockerCommandLineCodeExecutor = MockDockerCommandLineCodeExecutor

from src.logging import get_logger
from ..workflows.research_workflow import (
    ResearchWorkflowManager,
    run_simple_research,
    run_advanced_research,
)
from ..controllers.conversation_manager import ConversationConfig

logger = get_logger(__name__)


async def example_simple_research():
    """簡單研究工作流範例"""
    print("=== 簡單研究工作流範例 ===\n")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4",
        api_key="your-api-key",  # 請替換為實際的 API 密鑰
    )

    # 用戶查詢
    user_input = "請研究人工智慧在醫療領域的最新應用"

    try:
        # 執行簡單研究
        result = await run_simple_research(user_input, model_client)

        print(f"研究主題: {result.get('research_topic')}")
        print(f"執行狀態: {'成功' if result.get('success') else '失敗'}")
        print(f"執行時間: {result.get('execution_time', 0):.2f} 秒")

        if result.get("success"):
            print(f"\n最終報告:\n{result.get('final_report', '報告生成失敗')}")
        else:
            print(f"\n錯誤訊息: {result.get('error')}")

    except Exception as e:
        logger.error(f"範例執行失敗: {e}")
        print(f"執行失敗: {e}")


async def example_advanced_research():
    """高級研究工作流範例"""
    print("\n=== 高級研究工作流範例 ===\n")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4",
        api_key="your-api-key",  # 請替換為實際的 API 密鑰
    )

    # 高級配置
    config = ConversationConfig(
        enable_background_investigation=True,
        max_plan_iterations=3,
        max_step_iterations=5,
        enable_human_feedback=False,
        auto_accept_plan=True,
        debug_mode=True,
    )

    # 用戶查詢
    user_input = "分析比特幣價格變化趨勢，並預測未來走向"

    try:
        # 執行高級研究
        result = await run_advanced_research(
            user_input, model_client, workflow_type="comprehensive", config=config
        )

        print(f"研究主題: {result.get('research_topic')}")
        print(f"執行狀態: {'成功' if result.get('success') else '失敗'}")
        print(f"執行時間: {result.get('execution_time', 0):.2f} 秒")

        # 顯示執行摘要
        execution_result = result.get("execution_result", {})
        print(f"\n執行摘要:")
        print(f"- 計劃狀態: {execution_result.get('plan_status')}")
        print(f"- 總步驟數: {execution_result.get('total_steps')}")
        print(f"- 步驟狀態分佈: {execution_result.get('steps_by_status')}")

        if result.get("success"):
            print(f"\n最終報告:\n{result.get('final_report', '報告生成失敗')}")
        else:
            print(f"\n錯誤訊息: {result.get('error')}")

    except Exception as e:
        logger.error(f"範例執行失敗: {e}")
        print(f"執行失敗: {e}")


async def example_custom_workflow():
    """自定義工作流範例"""
    print("\n=== 自定義工作流範例 ===\n")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4",
        api_key="your-api-key",  # 請替換為實際的 API 密鑰
    )

    # 自定義配置
    config = ConversationConfig(
        enable_background_investigation=True,
        max_plan_iterations=2,
        max_step_iterations=3,
        enable_human_feedback=False,
        auto_accept_plan=True,
        timeout_seconds=600,
    )

    # 創建工作流管理器
    workflow_manager = ResearchWorkflowManager(model_client, config)

    try:
        await workflow_manager.initialize()

        # 用戶查詢
        user_input = "研究台灣半導體產業的發展現狀和競爭優勢"

        print(f"開始執行自定義工作流...")
        print(f"查詢: {user_input}\n")

        # 執行工作流
        result = await workflow_manager.run_research_workflow(user_input)

        print(f"研究主題: {result.get('research_topic')}")
        print(f"執行狀態: {'成功' if result.get('success') else '失敗'}")

        # 顯示工作流狀態
        workflow_status = workflow_manager.get_workflow_status()
        print(f"\n工作流狀態:")
        print(f"- 工作流 ID: {workflow_status.get('workflow_id')}")
        print(f"- 工作流名稱: {workflow_status.get('workflow_name')}")
        print(f"- 狀態: {workflow_status.get('status')}")

        # 顯示步驟摘要
        steps_summary = workflow_status.get("steps_summary", [])
        print(f"\n步驟執行摘要:")
        for step in steps_summary:
            status_icon = (
                "✅"
                if step["status"] == "completed"
                else "❌"
                if step["status"] == "failed"
                else "⏳"
            )
            print(f"  {status_icon} {step['id']} ({step['type']}) - {step['status']}")
            if step.get("execution_time"):
                print(f"      執行時間: {step['execution_time']:.2f} 秒")

        if result.get("success"):
            print(f"\n最終報告:\n{result.get('final_report', '報告生成失敗')}")
        else:
            print(f"\n錯誤訊息: {result.get('error')}")

    except Exception as e:
        logger.error(f"自定義工作流執行失敗: {e}")
        print(f"執行失敗: {e}")

    finally:
        await workflow_manager.cleanup()


async def example_workflow_with_code():
    """包含程式碼執行的工作流範例"""
    print("\n=== 包含程式碼執行的工作流範例 ===\n")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4",
        api_key="your-api-key",  # 請替換為實際的 API 密鑰
    )

    # 配置
    config = ConversationConfig(
        enable_background_investigation=True,
        max_plan_iterations=3,
        max_step_iterations=7,
        enable_human_feedback=False,
        auto_accept_plan=True,
    )

    # 用戶查詢 - 包含資料分析需求
    user_input = "分析一個 CSV 數據集，包括數據清理、統計分析和視覺化"

    try:
        # 執行工作流
        result = await run_advanced_research(user_input, model_client, "data_analysis", config)

        print(f"研究主題: {result.get('research_topic')}")
        print(f"執行狀態: {'成功' if result.get('success') else '失敗'}")
        print(f"執行時間: {result.get('execution_time', 0):.2f} 秒")

        # 檢查是否有程式碼執行結果
        execution_result = result.get("execution_result", {})
        if execution_result.get("steps_by_status", {}).get("completed", 0) > 0:
            print(
                f"\n成功完成 {execution_result.get('steps_by_status', {}).get('completed', 0)} 個步驟"
            )

        if result.get("success"):
            print(f"\n最終報告:\n{result.get('final_report', '報告生成失敗')}")
        else:
            print(f"\n錯誤訊息: {result.get('error')}")

    except Exception as e:
        logger.error(f"程式碼執行工作流失敗: {e}")
        print(f"執行失敗: {e}")


async def main():
    """主函數 - 執行所有範例"""
    print("AutoGen 研究工作流範例\n")
    print("=" * 50)

    try:
        # 執行各種範例
        await example_simple_research()
        await example_advanced_research()
        await example_custom_workflow()
        await example_workflow_with_code()

        print("\n" + "=" * 50)
        print("所有範例執行完成！")

    except KeyboardInterrupt:
        print("\n範例執行被中斷")
    except Exception as e:
        logger.error(f"範例執行異常: {e}")
        print(f"範例執行異常: {e}")


if __name__ == "__main__":
    # 執行範例
    asyncio.run(main())
