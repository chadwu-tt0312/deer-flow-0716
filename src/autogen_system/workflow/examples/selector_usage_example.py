# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
智能體選擇器使用範例

展示如何使用重構後的智能體選擇器系統。
"""

import sys
from pathlib import Path
from typing import List

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.autogen_system.workflow import (
    AgentSelector,
    AdvancedAgentSelector,
    create_selector_function,
    AgentName,
    WorkflowPhase,
)
from src.logging import init_logging, get_logger

# 初始化日誌
init_logging()
logger = get_logger(__name__)


class MockMessage:
    """模擬訊息類別"""

    def __init__(self, source: str, content: str):
        self.source = source
        self.content = content


def demo_basic_selector():
    """基本選擇器演示"""
    logger.info("=== 基本選擇器演示 ===")

    # 創建基本選擇器，包含流程控制參數
    selector = AgentSelector(
        enable_debug=True,
        max_plan_iterations=1,
        max_step_num=2,
        max_search_results=3,
        auto_accepted_plan=True,
        enable_background_investigation=True,
    )

    # 模擬對話流程
    test_cases = [
        # 初始狀態
        [],
        # 使用者發言
        [MockMessage("user", "請研究人工智慧在教育領域的最新應用")],
        # 協調者回應
        [
            MockMessage("user", "請研究人工智慧在教育領域的最新應用"),
            MockMessage("CoordinatorAgentV3", "任務分析完成，需要進行詳細規劃"),
        ],
        # 規劃者回應（包含計劃）
        [
            MockMessage("user", "請研究人工智慧在教育領域的最新應用"),
            MockMessage("CoordinatorAgentV3", "任務分析完成，需要進行詳細規劃"),
            MockMessage(
                "PlannerAgentV3",
                """```json
{
    "message_type": "plan",
    "agent_name": "PlannerAgentV3",
    "timestamp": "2025-01-01T00:00:00",
    "data": {
        "steps": [
            {"id": "step1", "step_type": "research", "description": "搜尋相關資料"},
            {"id": "step2", "step_type": "processing", "description": "分析數據"}
        ],
        "completed_steps": [],
        "original_task": "研究人工智慧在教育領域的最新應用"
    }
}
```""",
            ),
        ],
    ]

    for i, messages in enumerate(test_cases):
        logger.info(f"\n--- 測試案例 {i + 1} ---")
        result = selector.select_next_agent(messages)
        logger.info(f"選擇結果: {result}")

    # 顯示使用統計
    logger.info(f"選擇器輪次: {selector.turn_count}")


def demo_advanced_selector():
    """進階選擇器演示"""
    logger.info("\n=== 進階選擇器演示 ===")

    # 創建進階選擇器，包含流程控制參數
    selector = AdvancedAgentSelector(
        enable_debug=True,
        max_plan_iterations=2,
        max_step_num=3,
        max_search_results=5,
        auto_accepted_plan=False,
        enable_background_investigation=True,
    )

    # 模擬多輪對話
    messages = []
    for i in range(10):
        messages.append(MockMessage("ResearcherAgentV3", f"研究結果 {i}"))
        result = selector.select_next_agent(messages)
        logger.info(f"輪次 {i + 1}: 選擇 {result}")

    # 顯示使用統計
    logger.info(f"使用統計: {selector.get_usage_statistics()}")


def demo_factory_function():
    """工廠函數演示"""
    logger.info("\n=== 工廠函數演示 ===")

    # 創建基本選擇器函數，包含流程控制參數
    basic_func = create_selector_function(
        "basic", max_turns=20, max_plan_iterations=1, max_step_num=2, auto_accepted_plan=True
    )
    logger.info("基本選擇器函數已創建")

    # 創建進階選擇器函數，包含流程控制參數
    advanced_func = create_selector_function(
        "advanced",
        max_turns=30,
        max_plan_iterations=2,
        max_step_num=4,
        auto_accepted_plan=False,
        enable_background_investigation=True,
    )
    logger.info("進階選擇器函數已創建")

    # 測試使用
    test_messages = [MockMessage("user", "測試訊息")]

    basic_result = basic_func(test_messages)
    logger.info(f"基本選擇器結果: {basic_result}")

    advanced_result = advanced_func(test_messages)
    logger.info(f"進階選擇器結果: {advanced_result}")

    # 訪問選擇器實例
    logger.info(f"基本選擇器輪次: {basic_func.selector.turn_count}")
    logger.info(f"進階選擇器統計: {advanced_func.selector.get_usage_statistics()}")


def demo_enum_usage():
    """枚舉使用演示"""
    logger.info("\n=== 枚舉使用演示 ===")

    # 智能體名稱枚舉
    logger.info("智能體名稱:")
    for agent in AgentName:
        logger.info(f"  - {agent.value}")

    # 工作流程階段枚舉
    logger.info("工作流程階段:")
    for phase in WorkflowPhase:
        logger.info(f"  - {phase.value}")


def main():
    """主函數"""
    logger.info("🚀 智能體選擇器使用範例開始")

    try:
        demo_basic_selector()
        demo_advanced_selector()
        demo_factory_function()
        demo_enum_usage()

        logger.info("✅ 所有演示完成")

    except Exception as e:
        logger.error(f"❌ 演示過程中發生錯誤: {e}")
        raise


if __name__ == "__main__":
    main()
