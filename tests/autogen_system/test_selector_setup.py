#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
測試 AutoGen SelectorGroupChat 設置

快速驗證環境設置和依賴是否正確。
"""

import sys
import os
from pathlib import Path

# 確保專案根目錄在路徑中
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """測試導入"""
    print("🧪 測試導入...")

    try:
        # 測試基礎導入
        from src.deerflow_logging import get_simple_logger as get_logger

        print("✅ 基礎日誌模組導入成功")

        from src.config import load_yaml_config

        print("✅ 配置模組導入成功")

        from src.config.agents import AGENT_LLM_MAP

        print("✅ Agent 配置導入成功")

        # 測試 AutoGen 導入
        from autogen_agentchat.teams import SelectorGroupChat
        from autogen_agentchat.agents import AssistantAgent

        print("✅ AutoGen 模組導入成功")

        # 測試範例模組導入
        from src.autogen_system.agents.message_framework import MessageType

        print("✅ 訊息框架導入成功")

        from src.autogen_system.tools.tools_integration import initialize_all_tools

        print("✅ 工具整合模組導入成功")

        from src.autogen_system.agents.agents_v3 import CoordinatorAgentV3

        print("✅ V3 智能體模組導入成功")

        return True

    except ImportError as e:
        print(f"❌ 導入失敗: {e}")
        return False


def test_environment():
    """測試環境變數"""
    print("\n🔧 測試環境變數...")

    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "BASIC_MODEL__API_KEY",
        "REASONING_MODEL__API_KEY",
    ]

    missing = []
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var}: {'*' * 20}")  # 隱藏實際值
        else:
            print(f"❌ {var}: 未設定")
            missing.append(var)

    optional_vars = [
        "AZURE_DEPLOYMENT_NAME_4_1_MINI",
        "AZURE_DEPLOYMENT_NAME_4_1",
        "BASIC_MODEL__API_VERSION",
    ]

    print("\n📋 可選環境變數:")
    for var in optional_vars:
        value = os.getenv(var, "未設定")
        if value != "未設定":
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️ {var}: 未設定（將使用預設值）")

    return len(missing) == 0


def test_config_file():
    """測試配置檔案"""
    print("\n📄 測試配置檔案...")

    config_path = project_root / "conf_autogen.yaml"
    if not config_path.exists():
        print(f"❌ 配置檔案不存在: {config_path}")
        return False

    print(f"✅ 配置檔案存在: {config_path}")

    try:
        from src.config import load_yaml_config

        config = load_yaml_config("conf_autogen.yaml")

        # 檢查 V3 智能體配置
        agents = config.get("agents", {})
        v3_agents = ["coordinator_v3", "planner_v3", "researcher_v3", "coder_v3", "reporter_v3"]

        for agent in v3_agents:
            if agent in agents:
                print(f"✅ {agent} 配置存在")
            else:
                print(f"❌ {agent} 配置缺失")
                return False

        # 檢查工作流程配置
        workflows = config.get("workflows", {})
        if "research_v3" in workflows:
            print("✅ research_v3 工作流程配置存在")
        else:
            print("❌ research_v3 工作流程配置缺失")
            return False

        return True

    except Exception as e:
        print(f"❌ 配置檔案讀取失敗: {e}")
        return False


def test_llm_mapping():
    """測試 LLM 映射"""
    print("\n🧠 測試 LLM 映射...")

    try:
        from src.config.agents import AGENT_LLM_MAP

        v3_agents = [
            "CoordinatorAgentV3",
            "PlannerAgentV3",
            "ResearcherAgentV3",
            "CoderAgentV3",
            "ReporterAgentV3",
        ]

        for agent in v3_agents:
            if agent in AGENT_LLM_MAP:
                llm_type = AGENT_LLM_MAP[agent]
                print(f"✅ {agent}: {llm_type}")
            else:
                print(f"❌ {agent}: 映射缺失")
                return False

        return True

    except Exception as e:
        print(f"❌ LLM 映射測試失敗: {e}")
        return False


async def test_tools():
    """測試工具初始化"""
    print("\n🛠️ 測試工具初始化...")

    try:
        from src.autogen_system.tools.tools_integration import initialize_all_tools

        tools = await initialize_all_tools()
        print(f"✅ 工具初始化成功，共 {len(tools)} 個工具")

        # 檢查重要工具
        important_tools = ["web_search", "python_repl", "crawl_website"]
        for tool_name in important_tools:
            if tool_name in tools:
                print(f"✅ {tool_name} 工具可用")
            else:
                print(f"⚠️ {tool_name} 工具不可用")

        return True

    except Exception as e:
        print(f"❌ 工具初始化失敗: {e}")
        return False


async def main():
    """主測試函數"""
    print("🚀 AutoGen SelectorGroupChat 設置測試")
    print("=" * 50)

    tests = [
        ("導入測試", test_imports),
        ("環境變數測試", test_environment),
        ("配置檔案測試", test_config_file),
        ("LLM 映射測試", test_llm_mapping),
    ]

    results = []

    # 執行同步測試
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} 執行失敗: {e}")
            results.append((name, False))

    # 執行異步測試
    try:
        print("\n")
        tools_result = await test_tools()
        results.append(("工具初始化測試", tools_result))
    except Exception as e:
        print(f"❌ 工具初始化測試執行失敗: {e}")
        results.append(("工具初始化測試", False))

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
        print("🎉 所有測試通過！可以執行 SelectorGroupChat 範例。")
        print("\n執行指令:")
        print("python -m src.autogen_system.examples.basic.selector_group_chat_example")
    else:
        print("⚠️ 部分測試失敗，請檢查上述問題後重試。")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
