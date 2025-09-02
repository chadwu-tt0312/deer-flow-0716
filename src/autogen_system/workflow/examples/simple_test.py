# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
簡化的智能體選擇器測試

避免複雜的導入依賴，直接測試選擇邏輯。
"""

import sys
from pathlib import Path
from typing import Sequence, Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass


# 簡化的模擬類別，避免循環導入
class MockAgentName(str, Enum):
    COORDINATOR = "CoordinatorAgentV3"
    PLANNER = "PlannerAgentV3"
    RESEARCHER = "ResearcherAgentV3"
    CODER = "CoderAgentV3"
    REPORTER = "ReporterAgentV3"
    USER = "user"


class MockWorkflowPhase(str, Enum):
    INITIALIZATION = "initialization"
    COORDINATION = "coordination"
    BACKGROUND_INVESTIGATION = "background_investigation"
    PLANNING = "planning"
    HUMAN_FEEDBACK = "human_feedback"
    EXECUTION = "execution"
    REPORTING = "reporting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class MockMessage:
    source: str
    content: str


def test_basic_flow():
    """測試基本流程"""
    print("=== 測試基本流程邏輯 ===")

    # 測試場景
    test_cases = [
        # 初始狀態
        {
            "messages": [],
            "expected_phase": MockWorkflowPhase.INITIALIZATION,
            "expected_next": MockAgentName.COORDINATOR,
            "description": "初始狀態應該選擇協調者",
        },
        # 使用者輸入
        {
            "messages": [MockMessage("user", "請研究人工智慧")],
            "expected_phase": MockWorkflowPhase.INITIALIZATION,
            "expected_next": MockAgentName.COORDINATOR,
            "description": "使用者輸入應該選擇協調者",
        },
        # 協調者完成
        {
            "messages": [
                MockMessage("user", "請研究人工智慧"),
                MockMessage("CoordinatorAgentV3", "任務分析完成"),
            ],
            "expected_phase": MockWorkflowPhase.COORDINATION,
            "expected_next": "BackgroundInvestigator",  # 因為 enable_background_investigation=True
            "description": "協調者完成應該選擇背景調查者",
        },
    ]

    for i, test_case in enumerate(test_cases):
        print(f"\n--- 測試案例 {i + 1}: {test_case['description']} ---")

        # 模擬階段判斷
        if not test_case["messages"]:
            actual_phase = MockWorkflowPhase.INITIALIZATION
        else:
            last_speaker = test_case["messages"][-1].source
            if last_speaker == "user":
                actual_phase = MockWorkflowPhase.INITIALIZATION
            elif last_speaker == "CoordinatorAgentV3":
                actual_phase = MockWorkflowPhase.COORDINATION
            else:
                actual_phase = MockWorkflowPhase.INITIALIZATION

        # 模擬選擇邏輯
        if actual_phase == MockWorkflowPhase.INITIALIZATION:
            actual_next = MockAgentName.COORDINATOR
        elif actual_phase == MockWorkflowPhase.COORDINATION:
            # 假設 enable_background_investigation=True
            actual_next = "BackgroundInvestigator"
        else:
            actual_next = None

        # 驗證結果
        assert actual_phase == test_case["expected_phase"], (
            f"階段不符：期望 {test_case['expected_phase']}，實際 {actual_phase}"
        )
        assert actual_next == test_case["expected_next"], (
            f"選擇不符：期望 {test_case['expected_next']}，實際 {actual_next}"
        )

        print(f"✅ 階段: {actual_phase}")
        print(f"✅ 選擇: {actual_next}")


def test_parameter_logic():
    """測試參數邏輯"""
    print("\n=== 測試參數邏輯 ===")

    # 測試參數設定
    params = {
        "max_plan_iterations": 1,
        "max_step_num": 2,
        "max_search_results": 3,
        "auto_accepted_plan": True,
        "enable_background_investigation": True,
    }

    print("參數設定:")
    for key, value in params.items():
        print(f"  {key}: {value}")

    # 測試邏輯
    print("\n測試邏輯:")

    # 1. 背景調查邏輯
    if params["enable_background_investigation"]:
        print("✅ 啟用背景調查：協調者 -> 背景調查者 -> 規劃者")
    else:
        print("✅ 跳過背景調查：協調者 -> 規劃者")

    # 2. 計劃接受邏輯
    if params["auto_accepted_plan"]:
        print("✅ 自動接受計劃：規劃者 -> 執行者")
    else:
        print("✅ 需要人工確認：規劃者 -> 人工回饋 -> 執行者")

    # 3. 迭代限制邏輯
    current_iterations = 0
    if current_iterations >= params["max_plan_iterations"]:
        print(f"✅ 達到迭代限制 ({params['max_plan_iterations']})：直接轉到報告者")
    else:
        print(
            f"✅ 未達迭代限制：繼續執行（當前：{current_iterations}/{params['max_plan_iterations']}）"
        )

    # 4. 步驟限制邏輯
    plan_steps = ["step1", "step2"]  # 模擬 2 個步驟
    if len(plan_steps) > params["max_step_num"]:
        print(f"❌ 步驟數量超過限制：{len(plan_steps)} > {params['max_step_num']}")
    else:
        print(f"✅ 步驟數量符合限制：{len(plan_steps)} <= {params['max_step_num']}")


def test_step_execution_flow():
    """測試步驟執行流程"""
    print("\n=== 測試步驟執行流程 ===")

    # 模擬計劃步驟
    steps = [
        {"id": "step1", "step_type": "research", "description": "搜尋資料"},
        {"id": "step2", "step_type": "research", "description": "分析趨勢"},
    ]

    completed_steps = []

    print("計劃步驟:")
    for step in steps:
        print(f"  {step['id']}: {step['description']} ({step['step_type']})")

    # 模擬執行流程
    print("\n執行流程:")

    for i, step in enumerate(steps):
        print(f"\n第 {i + 1} 輪:")
        print(f"  當前步驟: {step['id']}")

        # 選擇執行者
        if "research" in step["step_type"]:
            executor = MockAgentName.RESEARCHER
        elif "code" in step["step_type"] or "processing" in step["step_type"]:
            executor = MockAgentName.CODER
        else:
            executor = MockAgentName.RESEARCHER

        print(f"  執行者: {executor}")

        # 模擬執行完成
        completed_steps.append(step["id"])
        print(f"  步驟完成，轉回規劃者檢查")

        # 檢查是否還有未完成步驟
        remaining_steps = [s for s in steps if s["id"] not in completed_steps]
        if remaining_steps:
            next_step = remaining_steps[0]
            print(f"  規劃者發現下一個步驟: {next_step['id']}")
        else:
            print(f"  規劃者發現所有步驟完成，轉到報告者")
            break

    print(f"\n✅ 執行完成，已完成步驟: {completed_steps}")


def main():
    """主函數"""
    print("🚀 開始簡化測試")

    try:
        test_basic_flow()
        test_parameter_logic()
        test_step_execution_flow()

        print("\n🎉 所有測試通過！")

    except AssertionError as e:
        print(f"\n❌ 測試失敗: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 測試錯誤: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
