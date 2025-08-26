#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
整合功能測試

簡單測試 ConversationManager 和 WorkflowController 的整合功能。
"""

import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


def test_imports():
    """測試導入功能"""
    print("🧪 測試導入功能...")

    try:
        from src.autogen_system.controllers.ledger_orchestrator import LedgerOrchestrator

        print("✅ LedgerOrchestrator 導入成功")
    except Exception as e:
        print(f"❌ LedgerOrchestrator 導入失敗: {e}")
        return False

    try:
        from src.autogen_system.controllers.conversation_manager import AutoGenConversationManager

        print("✅ ConversationManager 導入成功")
    except Exception as e:
        print(f"❌ ConversationManager 導入失敗: {e}")
        return False

    try:
        from src.autogen_system.controllers.workflow_controller import (
            WorkflowController,
            create_workflow_controller_with_ledger,
        )

        print("✅ WorkflowController 導入成功")
    except Exception as e:
        print(f"❌ WorkflowController 導入失敗: {e}")
        return False

    return True


def test_ledger_orchestrator():
    """測試 LedgerOrchestrator 基本功能"""
    print("\n🧪 測試 LedgerOrchestrator 基本功能...")

    try:
        from src.autogen_system.controllers.ledger_orchestrator import LedgerOrchestrator
        from src.autogen_system.config.agent_config import WorkflowConfig

        # 創建基本配置
        config = WorkflowConfig(
            name="test_workflow", workflow_type="research", max_iterations=5, agents=["test_agent"]
        )

        # 創建空的智能體字典
        agents = {}

        # 創建 LedgerOrchestrator
        orchestrator = LedgerOrchestrator(config=config, agents=agents, max_rounds=5)

        print("✅ LedgerOrchestrator 創建成功")
        print(f"   - 配置名稱: {orchestrator.config.name}")
        print(f"   - 智能體數量: {len(orchestrator.agents)}")
        print(f"   - 使用 AutoGen: {orchestrator._is_autogen_system}")

        return True

    except Exception as e:
        print(f"❌ LedgerOrchestrator 測試失敗: {e}")
        return False


def test_workflow_controller():
    """測試 WorkflowController 基本功能"""
    print("\n🧪 測試 WorkflowController 基本功能...")

    try:
        from src.autogen_system.controllers.workflow_controller import WorkflowController

        # 創建 WorkflowController
        controller = WorkflowController()

        print("✅ WorkflowController 創建成功")
        print(f"   - 使用 Ledger: {controller.is_using_ledger()}")
        print(f"   - 步驟處理器數量: {len(controller.step_handlers)}")
        print(f"   - 條件評估器數量: {len(controller.condition_evaluators)}")

        return True

    except Exception as e:
        print(f"❌ WorkflowController 測試失敗: {e}")
        return False


def test_conversation_manager():
    """測試 ConversationManager 基本功能"""
    print("\n🧪 測試 ConversationManager 基本功能...")

    try:
        from src.autogen_system.controllers.conversation_manager import AutoGenConversationManager

        # 創建模擬的 ChatCompletionClient
        class MockChatCompletionClient:
            def __init__(self):
                self.name = "mock_client"

        # 創建 ConversationManager
        manager = AutoGenConversationManager(model_client=MockChatCompletionClient())

        print("✅ ConversationManager 創建成功")
        print(f"   - 模型客戶端: {manager.model_client.name}")
        print(f"   - 配置: {manager.config.max_conversation_turns} 輪對話")
        print(f"   - LedgerOrchestrator: {manager.ledger_orchestrator is not None}")

        return True

    except Exception as e:
        print(f"❌ ConversationManager 測試失敗: {e}")
        return False


def test_integration():
    """測試整合功能"""
    print("\n🧪 測試整合功能...")

    try:
        from src.autogen_system.controllers.ledger_orchestrator import LedgerOrchestrator
        from src.autogen_system.controllers.workflow_controller import (
            create_workflow_controller_with_ledger,
        )
        from src.autogen_system.controllers.conversation_manager import AutoGenConversationManager
        from src.autogen_system.config.agent_config import WorkflowConfig

        # 創建基本配置
        config = WorkflowConfig(
            name="integration_test",
            workflow_type="research",
            max_iterations=5,
            agents=["test_agent"],
        )

        # 創建空的智能體字典
        agents = {}

        # 1. 創建 LedgerOrchestrator
        ledger_orchestrator = LedgerOrchestrator(config=config, agents=agents, max_rounds=5)
        print("✅ 1. LedgerOrchestrator 創建成功")

        # 2. 創建整合的 WorkflowController
        workflow_controller = create_workflow_controller_with_ledger(ledger_orchestrator)
        print("✅ 2. 整合的 WorkflowController 創建成功")
        print(f"   - 使用 Ledger: {workflow_controller.is_using_ledger()}")

        # 3. 創建 ConversationManager 並設置 LedgerOrchestrator
        class MockChatCompletionClient:
            def __init__(self):
                self.name = "mock_client"

        conversation_manager = AutoGenConversationManager(model_client=MockChatCompletionClient())
        conversation_manager.ledger_orchestrator = ledger_orchestrator
        print("✅ 3. ConversationManager 整合成功")
        print(
            f"   - LedgerOrchestrator 已設置: {conversation_manager.ledger_orchestrator is not None}"
        )

        # 4. 測試狀態同步
        workflow_controller.sync_with_ledger()
        print("✅ 4. 狀態同步成功")

        # 5. 測試獲取狀態
        ledger_status = workflow_controller.get_ledger_status()
        conversation_summary = conversation_manager.get_conversation_summary()

        print("✅ 5. 狀態獲取成功")
        print(f"   - Ledger 狀態: {ledger_status is not None}")
        print(f"   - 對話摘要使用 Ledger: {conversation_summary.get('using_ledger', False)}")

        return True

    except Exception as e:
        print(f"❌ 整合功能測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函數"""
    print("🚀 開始整合功能測試\n")

    # 測試導入
    if not test_imports():
        print("\n❌ 導入測試失敗，無法繼續")
        return

    # 測試各個組件
    tests = [
        test_ledger_orchestrator,
        test_workflow_controller,
        test_conversation_manager,
        test_integration,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    # 顯示結果
    print(f"\n📊 測試結果: {passed}/{total} 通過")

    if passed == total:
        print("🎉 所有測試通過！整合功能正常")
    else:
        print("⚠️ 部分測試失敗，請檢查相關功能")

    print("\n✅ 整合功能測試完成")


if __name__ == "__main__":
    main()
