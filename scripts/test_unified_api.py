#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
測試統一的 API 路由和系統切換功能

此腳本測試 autogen 與 LangGraph 是否使用相同的 API 路徑，
以及系統切換是否正常工作。
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.autogen_system.compatibility import (
    SystemSwitcher,
    SystemType,
    get_current_system,
    switch_to_autogen,
    switch_to_langgraph,
    system_health_check,
)


async def test_system_switching():
    """測試系統切換功能"""
    print("🧪 測試系統切換功能...")

    # 創建系統切換器實例
    switcher = SystemSwitcher()

    # 檢查初始系統
    initial_system = switcher.get_current_system()
    print(f"✅ 初始系統: {initial_system.value}")

    # 測試切換到 AutoGen
    print("\n🔄 切換到 AutoGen 系統...")
    switcher.switch_system(SystemType.AUTOGEN)
    current_system = switcher.get_current_system()
    print(f"✅ 當前系統: {current_system.value}")

    # 測試切換到 LangGraph
    print("\n🔄 切換到 LangGraph 系統...")
    switcher.switch_system(SystemType.LANGGRAPH)
    current_system = switcher.get_current_system()
    print(f"✅ 當前系統: {current_system.value}")

    # 測試環境變數檢測
    print("\n🔍 測試環境變數檢測...")
    env_system = switcher._detect_system()
    print(f"✅ 環境變數檢測結果: {env_system.value}")

    return True


async def test_global_functions():
    """測試全域函數"""
    print("\n🧪 測試全域函數...")

    # 測試獲取當前系統
    current_system = get_current_system()
    print(f"✅ 全域當前系統: {current_system}")

    # 測試切換函數
    print("\n🔄 測試全域切換函數...")
    switch_to_autogen()
    current_system = get_current_system()
    print(f"✅ 切換到 AutoGen 後: {current_system}")

    switch_to_langgraph()
    current_system = get_current_system()
    print(f"✅ 切換到 LangGraph 後: {current_system}")

    return True


async def test_health_check():
    """測試健康檢查"""
    print("\n🧪 測試系統健康檢查...")

    try:
        health_status = await system_health_check()
        print("✅ 健康檢查完成")
        print(f"   系統狀態: {health_status}")
    except Exception as e:
        print(f"❌ 健康檢查失敗: {e}")
        return False

    return True


async def test_api_compatibility():
    """測試 API 相容性"""
    print("\n🧪 測試 API 相容性...")

    try:
        # 檢查主要的 app.py 是否正確導入
        from src.server.app import app

        print("✅ 主要 app.py 成功導入")

        # 檢查是否有統一的 API 路由
        routes = [route.path for route in app.routes if hasattr(route, "path")]
        chat_routes = [route for route in routes if "chat" in route]
        print(f"✅ 找到聊天路由: {chat_routes}")

        # 檢查是否有 /api/chat/stream 路由
        if "/api/chat/stream" in chat_routes:
            print("✅ 統一的聊天 API 路由存在")
        else:
            print("❌ 統一的聊天 API 路由不存在")
            return False

        # 檢查是否有系統狀態端點
        system_routes = [route for route in routes if "system" in route]
        if "/api/system/status" in system_routes:
            print("✅ 系統狀態端點存在")
        else:
            print("❌ 系統狀態端點不存在")
            return False

        # 測試系統類型檢測函數
        from src.server.app import get_current_system_type

        current_system = get_current_system_type()
        print(f"✅ 系統類型檢測正常: {current_system}")

        return True

    except Exception as e:
        print(f"❌ API 相容性測試失敗: {e}")
        return False


async def main():
    """主測試函數"""
    print("🚀 開始測試統一的 API 路由和系統切換功能")
    print("=" * 60)

    test_results = []

    # 執行所有測試
    tests = [
        ("系統切換功能", test_system_switching),
        ("全域函數", test_global_functions),
        ("健康檢查", test_health_check),
        ("API 相容性", test_api_compatibility),
    ]

    for test_name, test_func in tests:
        try:
            result = await test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 測試異常: {e}")
            test_results.append((test_name, False))

    # 輸出測試結果摘要
    print("\n" + "=" * 60)
    print("📊 測試結果摘要")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n總計: {passed}/{total} 測試通過")

    if passed == total:
        print("🎉 所有測試通過！統一的 API 路由和系統切換功能正常")
        return True
    else:
        print("⚠️  部分測試失敗，請檢查相關配置")
        return False


if __name__ == "__main__":
    # 設定預設環境變數
    if "USE_AUTOGEN_SYSTEM" not in os.environ:
        os.environ["USE_AUTOGEN_SYSTEM"] = "true"
        print("ℹ️  設定預設環境變數: USE_AUTOGEN_SYSTEM=true")

    # 執行測試
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
