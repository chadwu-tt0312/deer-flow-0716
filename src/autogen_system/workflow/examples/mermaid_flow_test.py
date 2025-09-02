# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
基於 Mermaid 流程圖的智能體選擇器測試

測試重構後的選擇器是否正確實現了 mermaid 流程圖中的邏輯。
"""

import sys
from pathlib import Path
from typing import List

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.autogen_system.workflow import (
    AgentSelector,
    AgentName,
    WorkflowPhase,
)
from src.deerflow_logging import (
    init_simple_logging as init_logging,
    get_simple_logger as get_logger,
)

# 初始化日誌
init_logging()
logger = get_logger(__name__)


class MockMessage:
    """模擬訊息類別"""

    def __init__(self, source: str, content: str):
        self.source = source
        self.content = content


def test_mermaid_flow_scenario():
    """測試 Mermaid 流程圖場景"""
    logger.info("=== 測試 Mermaid 流程圖場景 ===")

    # 創建選擇器，使用與 mermaid 圖相同的參數
    selector = AgentSelector(
        enable_debug=True,
        max_plan_iterations=1,  # 對應 mermaid 圖中的 Max plan iterations=1
        max_step_num=2,  # 對應 mermaid 圖中的 Max steps of a research plan=2
        max_search_results=3,  # 對應 mermaid 圖中的 Max search results=3
        auto_accepted_plan=True,
        enable_background_investigation=True,
    )

    # 場景 1: 初始狀態 -> 協調者
    logger.info("\n--- 場景 1: 初始狀態 ---")
    messages = []
    result = selector.select_next_agent(messages)
    assert result == AgentName.COORDINATOR, f"期望 {AgentName.COORDINATOR}，實際 {result}"
    logger.info(f"✅ 初始狀態正確選擇: {result}")

    # 場景 2: 使用者輸入 -> 協調者
    logger.info("\n--- 場景 2: 使用者輸入 ---")
    messages = [MockMessage("user", "請研究人工智慧在醫療領域的最新應用趨勢")]
    result = selector.select_next_agent(messages)
    assert result == AgentName.COORDINATOR, f"期望 {AgentName.COORDINATOR}，實際 {result}"
    logger.info(f"✅ 使用者輸入正確選擇: {result}")

    # 場景 3: 協調者 -> 背景調查者（因為 enable_background_investigation=True）
    logger.info("\n--- 場景 3: 協調者完成 ---")
    messages.append(MockMessage("CoordinatorAgentV3", "任務分析完成，確定研究主題"))
    result = selector.select_next_agent(messages)
    expected = "BackgroundInvestigatorAgentV3"  # 根據流程圖
    assert result == expected, f"期望 {expected}，實際 {result}"
    logger.info(f"✅ 協調者正確選擇: {result}")

    # 場景 4: 背景調查 -> 規劃者
    logger.info("\n--- 場景 4: 背景調查完成 ---")
    messages.append(MockMessage("BackgroundInvestigatorAgentV3", "背景調查完成，收集到相關資料"))
    result = selector.select_next_agent(messages)
    assert result == AgentName.PLANNER, f"期望 {AgentName.PLANNER}，實際 {result}"
    logger.info(f"✅ 背景調查正確選擇: {result}")

    # 場景 5: 規劃者生成計劃 -> 研究者（第一個步驟）
    logger.info("\n--- 場景 5: 規劃者生成計劃 ---")
    plan_message = """```json
{
    "message_type": "plan",
    "agent_name": "PlannerAgentV3",
    "timestamp": "2025-01-01T00:00:00",
    "data": {
        "steps": [
            {"id": "step1", "step_type": "research", "description": "收集人工智慧在医疗领域的最新技术发展及应用案例"},
            {"id": "step2", "step_type": "research", "description": "分析人工智慧医疗应用的未来发展趋势、利益相关方及潜在风险"}
        ],
        "completed_steps": [],
        "original_task": "研究人工智慧在医疗领域的最新应用趋势",
        "has_enough_context": false
    }
}
```"""
    messages.append(MockMessage("PlannerAgentV3", plan_message))
    result = selector.select_next_agent(messages)
    assert result == AgentName.RESEARCHER, f"期望 {AgentName.RESEARCHER}，實際 {result}"
    logger.info(f"✅ 規劃者正確選擇: {result}")

    # 場景 6: 研究者完成第一步 -> 規劃者（檢查下一步）
    logger.info("\n--- 場景 6: 研究者完成第一步 ---")
    messages.append(MockMessage("ResearcherAgentV3", "第一個研究步驟完成，收集了相關技術發展資料"))
    result = selector.select_next_agent(messages)
    assert result == AgentName.PLANNER, f"期望 {AgentName.PLANNER}，實際 {result}"
    logger.info(f"✅ 研究者完成正確選擇: {result}")

    # 場景 7: 規劃者檢查 -> 研究者（第二個步驟）
    logger.info("\n--- 場景 7: 規劃者檢查下一步 ---")
    updated_plan_message = """```json
{
    "message_type": "plan",
    "agent_name": "PlannerAgentV3",
    "timestamp": "2025-01-01T00:01:00",
    "data": {
        "steps": [
            {"id": "step1", "step_type": "research", "description": "收集人工智慧在医疗领域的最新技术发展及应用案例"},
            {"id": "step2", "step_type": "research", "description": "分析人工智慧医疗应用的未来发展趋势、利益相关方及潜在风险"}
        ],
        "completed_steps": ["step1"],
        "original_task": "研究人工智慧在医疗领域的最新应用趋势",
        "has_enough_context": false
    }
}
```"""
    messages.append(MockMessage("PlannerAgentV3", updated_plan_message))
    result = selector.select_next_agent(messages)
    assert result == AgentName.RESEARCHER, f"期望 {AgentName.RESEARCHER}，實際 {result}"
    logger.info(f"✅ 規劃者檢查正確選擇: {result}")

    # 場景 8: 研究者完成第二步 -> 規劃者 -> 報告者
    logger.info("\n--- 場景 8: 研究者完成第二步 ---")
    messages.append(MockMessage("ResearcherAgentV3", "第二個研究步驟完成，分析了未來趨勢"))
    result = selector.select_next_agent(messages)
    assert result == AgentName.PLANNER, f"期望 {AgentName.PLANNER}，實際 {result}"
    logger.info(f"✅ 研究者第二步完成正確選擇: {result}")

    # 場景 9: 規劃者檢查所有步驟完成 -> 報告者
    logger.info("\n--- 場景 9: 規劃者檢查所有步驟完成 ---")
    final_plan_message = """```json
{
    "message_type": "plan",
    "agent_name": "PlannerAgentV3",
    "timestamp": "2025-01-01T00:02:00",
    "data": {
        "steps": [
            {"id": "step1", "step_type": "research", "description": "收集人工智慧在医疗领域的最新技术发展及应用案例"},
            {"id": "step2", "step_type": "research", "description": "分析人工智慧医疗应用的未来发展趋势、利益相关方及潜在风险"}
        ],
        "completed_steps": ["step1", "step2"],
        "original_task": "研究人工智慧在医疗领域的最新应用趋势",
        "has_enough_context": false
    }
}
```"""
    messages.append(MockMessage("PlannerAgentV3", final_plan_message))
    result = selector.select_next_agent(messages)
    assert result == AgentName.REPORTER, f"期望 {AgentName.REPORTER}，實際 {result}"
    logger.info(f"✅ 所有步驟完成正確選擇: {result}")

    # 場景 10: 報告者完成 -> 結束
    logger.info("\n--- 場景 10: 報告者完成 ---")
    messages.append(MockMessage("ReporterAgentV3", "最終報告已完成\n\nWORKFLOW_COMPLETE"))
    result = selector.select_next_agent(messages)
    assert result is None, f"期望 None，實際 {result}"
    logger.info(f"✅ 報告者完成正確選擇: {result}")

    logger.info("\n🎉 所有 Mermaid 流程圖場景測試通過！")


def test_parameter_limits():
    """測試參數限制"""
    logger.info("\n=== 測試參數限制 ===")

    # 測試計劃迭代次數限制
    selector = AgentSelector(
        enable_debug=True,
        max_plan_iterations=1,
        max_step_num=2,
        auto_accepted_plan=True,
        enable_background_investigation=False,
    )

    # 模擬達到迭代限制的情況
    selector.current_plan_iterations = 1  # 已達上限

    messages = [
        MockMessage("user", "測試任務"),
        MockMessage("CoordinatorAgentV3", "協調完成"),
        MockMessage(
            "PlannerAgentV3",
            """```json
{
    "message_type": "plan",
    "agent_name": "PlannerAgentV3",
    "timestamp": "2025-01-01T00:00:00",
    "data": {
        "steps": [{"id": "step1", "step_type": "research", "description": "測試步驟"}],
        "completed_steps": [],
        "original_task": "測試任務",
        "has_enough_context": false
    }
}
```""",
        ),
    ]

    result = selector.select_next_agent(messages)
    assert result == AgentName.REPORTER, f"期望 {AgentName.REPORTER}（達到迭代限制），實際 {result}"
    logger.info(f"✅ 計劃迭代限制測試通過: {result}")


def main():
    """主函數"""
    logger.info("🚀 開始 Mermaid 流程圖測試")

    try:
        test_mermaid_flow_scenario()
        test_parameter_limits()

        logger.info("✅ 所有測試通過")

    except AssertionError as e:
        logger.error(f"❌ 測試失敗: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ 測試過程中發生錯誤: {e}")
        raise


if __name__ == "__main__":
    main()
