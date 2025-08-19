#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
快速配置測試腳本

簡單直接地測試 conf_autogen.yaml 配置檔案的載入和使用。
"""

import os
import sys
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_config_loading():
    """測試配置載入"""
    print("🚀 開始快速配置測試")
    print("=" * 40)

    try:
        # 1. 測試配置檔案存在
        config_file = project_root / "conf_autogen.yaml"
        if not config_file.exists():
            print(f"❌ 配置檔案不存在: {config_file}")
            return False

        print(f"✅ 配置檔案存在: {config_file}")

        # 2. 測試配置載入器
        from src.autogen_system.config.config_loader import ConfigLoader

        config_loader = ConfigLoader(str(project_root))

        print("✅ 配置載入器創建成功")

        # 3. 載入 YAML 配置
        config = config_loader.load_yaml_config("conf_autogen.yaml")
        if not config:
            print("❌ 配置載入失敗")
            return False

        print("✅ YAML 配置載入成功")
        print(f"   配置區段: {list(config.keys())}")

        # 4. 測試 LLM 配置
        autogen_config = config.get("autogen", {})
        if "default_llm_config" not in autogen_config:
            print("❌ 缺少 default_llm_config")
            return False

        llm_config = config_loader.load_llm_config(autogen_config.get("default_llm_config", {}))

        print("✅ LLM 配置載入成功")
        print(f"   模型: {llm_config.model}")
        print(f"   溫度: {llm_config.temperature}")

        # 5. 測試智能體配置
        agents_config = config.get("agents", {})
        if not agents_config:
            print("❌ 沒有智能體配置")
            return False

        print(f"✅ 智能體配置載入成功 ({len(agents_config)} 個)")

        # 測試每個智能體
        for agent_name, agent_dict in agents_config.items():
            try:
                agent_config = config_loader.load_agent_config(agent_name, agent_dict)
                print(f"   ✅ {agent_name}: {agent_config.name}")
            except Exception as e:
                print(f"   ❌ {agent_name}: {e}")
                return False

        # 6. 測試工作流配置
        try:
            workflow_config = config_loader.load_workflow_config("research")
            print(f"✅ 工作流配置載入成功: {workflow_config.name}")
            print(f"   智能體數量: {len(workflow_config.agents)}")
        except Exception as e:
            print(f"❌ 工作流配置載入失敗: {e}")
            return False

        # 7. 測試工具配置
        tools_config = config.get("tools", {})
        if tools_config:
            print("✅ 工具配置載入成功")
            print(f"   工具類型: {list(tools_config.keys())}")

        # 8. 測試安全配置
        try:
            security_config = config_loader.get_security_config()
            print("✅ 安全配置載入成功")
            print(f"   程式碼執行: {security_config['enable_code_execution']}")
        except Exception as e:
            print(f"❌ 安全配置載入失敗: {e}")
            return False

        print("\n" + "=" * 40)
        print("🎉 所有配置測試都通過！")
        print("=" * 40)

        return True

    except Exception as e:
        print(f"❌ 配置測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_config_usage():
    """測試配置使用"""
    print("\n🔍 測試配置實際使用...")

    try:
        from src.autogen_system.config.config_loader import config_loader
        from src.autogen_system.config.agent_config import AgentConfig, WorkflowConfig

        # 載入配置
        config = config_loader.load_yaml_config("conf_autogen.yaml")

        # 創建智能體配置
        agents = {}
        agents_config = config.get("agents", {})

        for agent_name, agent_dict in agents_config.items():
            agent_config = config_loader.load_agent_config(agent_name, agent_dict)
            agents[agent_name] = agent_config

        print(f"✅ 成功創建 {len(agents)} 個智能體配置")

        # 創建工作流配置
        workflow_config = config_loader.load_workflow_config("research")
        print(f"✅ 成功創建工作流配置: {workflow_config.name}")

        # 驗證配置完整性
        for agent in workflow_config.agents:
            assert agent.llm_config is not None, f"智能體 {agent.name} 缺少 LLM 配置"
            assert agent.system_message, f"智能體 {agent.name} 缺少系統訊息"

        print("✅ 配置完整性驗證通過")

        return True

    except Exception as e:
        print(f"❌ 配置使用測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函數"""
    print("🚀 開始 PHASE1 配置系統驗證")
    print("=" * 50)

    # 測試 1: 配置載入
    if not test_config_loading():
        print("\n❌ 配置載入測試失敗")
        sys.exit(1)

    # 測試 2: 配置使用
    if not test_config_usage():
        print("\n❌ 配置使用測試失敗")
        sys.exit(1)

    print("\n🎉 PHASE1 配置系統驗證完成！")
    print("配置系統已準備就緒，可以進入下一階段。")


if __name__ == "__main__":
    main()
