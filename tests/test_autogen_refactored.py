#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
測試重構後的 AutoGen 系統

驗證重構後的模組是否正常工作。
"""

import sys
import os
from pathlib import Path

# 確保專案根目錄在路徑中
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_basic_imports():
    """測試基本導入"""
    print("🧪 測試基本導入...")

    try:
        # 測試核心模組
        from src.autogen_system.adapters.llm_adapter import LLMChatCompletionAdapter

        print("✅ LLM 適配器導入成功")

        from src.autogen_system.agents.agents_v3 import CoordinatorAgentV3

        print("✅ V3 智能體導入成功")

        from src.autogen_system.agents.message_framework import MessageType

        print("✅ 訊息框架導入成功")

        from src.autogen_system.tools.tools_integration import initialize_all_tools

        print("✅ 工具整合導入成功")

        # 測試重構後的 compatibility 層
        from src.autogen_system.compatibility import (
            AutoGenAPIAdapter,
            LangGraphCompatibilityLayer,
            ResponseMapper,
            StreamResponseMapper,
        )

        print("✅ 相容性層導入成功")

        return True

    except ImportError as e:
        print(f"❌ 導入失敗: {e}")
        return False


def test_adapter_creation():
    """測試適配器創建"""
    print("\n🔧 測試適配器創建...")

    try:
        from src.autogen_system.adapters.llm_adapter import LLMChatCompletionAdapter

        adapter = LLMChatCompletionAdapter("basic")
        print("✅ LLM 適配器創建成功")

        # 測試模型資訊
        model_info = adapter.model_info
        print(f"✅ 模型資訊: {model_info.get('model', 'unknown')}")

        return True

    except Exception as e:
        print(f"❌ 適配器創建失敗: {e}")
        return False


def test_compatibility_layer():
    """測試相容性層"""
    print("\n🔄 測試相容性層...")

    try:
        from src.autogen_system.compatibility import AutoGenAPIAdapter
        from src.autogen_system.adapters.llm_adapter import create_chat_client

        # 創建模型客戶端
        model_client = create_chat_client("coordinator")

        # 創建 API 適配器
        api_adapter = AutoGenAPIAdapter(model_client)
        print("✅ API 適配器創建成功")

        return True

    except Exception as e:
        print(f"❌ 相容性層測試失敗: {e}")
        return False


def test_moved_files():
    """測試移動的檔案"""
    print("\n📁 測試移動的檔案...")

    moved_files = [
        "src/autogen_system/examples/basic/selector_group_chat_example.py",
        "src/autogen_system/examples/compatibility/example_usage.py",
        "tests/autogen_system/test_selector_setup.py",
        "tests/autogen_system/test_compatibility.py",
    ]

    all_exist = True
    for file_path in moved_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} 存在")
        else:
            print(f"❌ {file_path} 不存在")
            all_exist = False

    return all_exist


def main():
    """主測試函數"""
    print("🚀 測試重構後的 AutoGen 系統")
    print("=" * 50)

    tests = [
        ("基本導入測試", test_basic_imports),
        ("適配器創建測試", test_adapter_creation),
        ("相容性層測試", test_compatibility_layer),
        ("檔案移動測試", test_moved_files),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} 執行失敗: {e}")
            results.append((name, False))

    # 總結結果
    print("\n" + "=" * 50)
    print("📊 測試結果總結:")

    passed = 0
    total = len(results)

    for name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{name}: {status}")
        if result:
            passed += 1

    print(f"\n總計: {passed}/{total} 測試通過")

    if passed == total:
        print("🎉 所有測試通過！重構成功。")
        print("\n📝 重構摘要:")
        print("1. ✅ 移除了重複的測試檔案")
        print("2. ✅ 移動了範例和測試檔案到正確位置")
        print("3. ✅ 重構了 compatibility 層，移除 Mock 類別")
        print("4. ✅ 統一了導入路徑")
        print("5. ✅ 清理了檔案結構")
    else:
        print("⚠️ 部分測試失敗，請檢查上述問題。")


if __name__ == "__main__":
    main()
