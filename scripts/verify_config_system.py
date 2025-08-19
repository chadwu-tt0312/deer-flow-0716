#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
配置系統驗證腳本

直接驗證 conf_autogen.yaml 配置檔案的載入和使用。
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.autogen_system.config.config_loader import ConfigLoader
from src.autogen_system.config.agent_config import (
    AgentConfig,
    WorkflowConfig,
    LLMConfig,
    AgentRole,
    WorkflowType,
)


class ConfigSystemVerifier:
    """配置系統驗證器"""

    def __init__(self):
        self.project_root = project_root
        self.config_file = self.project_root / "conf_autogen.yaml"
        self.config_loader = ConfigLoader(str(self.project_root))

    def verify_config_file_exists(self) -> bool:
        """驗證配置檔案是否存在"""
        print("🔍 檢查配置檔案...")

        if not self.config_file.exists():
            print(f"❌ 配置檔案不存在: {self.config_file}")
            return False

        print(f"✅ 配置檔案存在: {self.config_file}")
        print(f"   檔案大小: {self.config_file.stat().st_size} bytes")
        return True

    def verify_yaml_syntax(self) -> bool:
        """驗證 YAML 語法"""
        print("\n🔍 檢查 YAML 語法...")

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                yaml.safe_load(f)
            print("✅ YAML 語法正確")
            return True
        except yaml.YAMLError as e:
            print(f"❌ YAML 語法錯誤: {e}")
            return False

    def verify_config_structure(self) -> bool:
        """驗證配置結構"""
        print("\n🔍 檢查配置結構...")

        config = self.config_loader.load_yaml_config("conf_autogen.yaml")

        # 檢查必要區段
        required_sections = ["autogen", "agents", "workflows", "tools"]
        missing_sections = []

        for section in required_sections:
            if section not in config:
                missing_sections.append(section)

        if missing_sections:
            print(f"❌ 缺少必要配置區段: {missing_sections}")
            return False

        print("✅ 配置結構完整")
        print(f"   主要區段: {list(config.keys())}")

        # 檢查 autogen 區段
        autogen_config = config["autogen"]
        if "default_llm_config" not in autogen_config:
            print("❌ 缺少 default_llm_config")
            return False

        print("✅ autogen 區段完整")
        return True

    def verify_llm_config(self) -> bool:
        """驗證 LLM 配置"""
        print("\n🔍 檢查 LLM 配置...")

        config = self.config_loader.load_yaml_config("conf_autogen.yaml")
        autogen_config = config.get("autogen", {})

        try:
            llm_config = self.config_loader.load_llm_config(
                autogen_config.get("default_llm_config", {})
            )

            print("✅ LLM 配置載入成功")
            print(f"   模型: {llm_config.model}")
            print(f"   溫度: {llm_config.temperature}")
            print(f"   最大 token: {llm_config.max_tokens}")
            print(f"   超時: {llm_config.timeout}")

            # 檢查環境變數
            if llm_config.api_key:
                print(f"   API Key: {'*' * 10}{llm_config.api_key[-4:]}")
            else:
                print("   API Key: 未設定 (將使用環境變數)")

            return True

        except Exception as e:
            print(f"❌ LLM 配置載入失敗: {e}")
            return False

    def verify_agents_config(self) -> bool:
        """驗證智能體配置"""
        print("\n🔍 檢查智能體配置...")

        config = self.config_loader.load_yaml_config("conf_autogen.yaml")
        agents_config = config.get("agents", {})

        if not agents_config:
            print("❌ 沒有智能體配置")
            return False

        print(f"✅ 找到 {len(agents_config)} 個智能體配置")

        # 檢查必要智能體
        required_agents = ["coordinator", "planner", "researcher", "coder", "reporter"]
        missing_agents = []

        for agent in required_agents:
            if agent not in agents_config:
                missing_agents.append(agent)

        if missing_agents:
            print(f"❌ 缺少必要智能體: {missing_agents}")
            return False

        print("✅ 所有必要智能體都已配置")

        # 驗證每個智能體配置
        for agent_name, agent_dict in agents_config.items():
            try:
                agent_config = self.config_loader.load_agent_config(agent_name, agent_dict)

                print(f"   ✅ {agent_name}: {agent_config.name} ({agent_config.role.value})")
                print(f"      系統訊息: {agent_config.system_message[:50]}...")
                print(f"      工具數量: {len(agent_config.tools)}")

            except Exception as e:
                print(f"   ❌ {agent_name} 配置載入失敗: {e}")
                return False

        return True

    def verify_workflows_config(self) -> bool:
        """驗證工作流配置"""
        print("\n🔍 檢查工作流配置...")

        try:
            # 載入研究工作流
            workflow_config = self.config_loader.load_workflow_config("research")

            print("✅ 研究工作流配置載入成功")
            print(f"   名稱: {workflow_config.name}")
            print(f"   類型: {workflow_config.workflow_type.value}")
            print(f"   智能體數量: {len(workflow_config.agents)}")

            # 顯示智能體列表
            for i, agent in enumerate(workflow_config.agents, 1):
                print(f"     {i}. {agent.name} ({agent.role.value})")

            return True

        except Exception as e:
            print(f"❌ 工作流配置載入失敗: {e}")
            return False

    def verify_tools_config(self) -> bool:
        """驗證工具配置"""
        print("\n🔍 檢查工具配置...")

        config = self.config_loader.load_yaml_config("conf_autogen.yaml")
        tools_config = config.get("tools", {})

        if not tools_config:
            print("❌ 沒有工具配置")
            return False

        print("✅ 工具配置完整")

        # 檢查主要工具
        main_tools = ["web_search", "code_execution", "mcp_servers"]
        for tool in main_tools:
            if tool in tools_config:
                print(f"   ✅ {tool}: 已配置")
            else:
                print(f"   ⚠️  {tool}: 未配置")

        # 檢查 web_search 配置
        if "web_search" in tools_config:
            web_search = tools_config["web_search"]
            print(f"   🔍 web_search 提供者: {web_search.get('provider', '未設定')}")
            print(f"   🔍 最大結果數: {web_search.get('max_results', '未設定')}")

        return True

    def verify_security_config(self) -> bool:
        """驗證安全配置"""
        print("\n🔍 檢查安全配置...")

        try:
            security_config = self.config_loader.get_security_config()

            print("✅ 安全配置載入成功")
            print(f"   程式碼執行: {security_config['enable_code_execution']}")
            print(f"   沙盒模式: {security_config['sandbox_mode']}")
            print(f"   允許的檔案類型: {security_config['allowed_file_extensions']}")
            print(f"   最大檔案大小: {security_config['max_file_size_mb']} MB")

            return True

        except Exception as e:
            print(f"❌ 安全配置載入失敗: {e}")
            return False

    def verify_environment_variables(self) -> bool:
        """驗證環境變數"""
        print("\n🔍 檢查環境變數...")

        env_vars = {"OPENAI_API_KEY": "OpenAI API 金鑰", "OPENAI_BASE_URL": "OpenAI 基礎 URL"}

        missing_vars = []
        for var, description in env_vars.items():
            if os.getenv(var):
                print(f"   ✅ {var}: 已設定 ({description})")
            else:
                print(f"   ⚠️  {var}: 未設定 ({description})")
                missing_vars.append(var)

        if missing_vars:
            print(f"⚠️  建議設定環境變數: {missing_vars}")
            print("   注意: 這些變數可以在 conf_autogen.yaml 中設定，或通過環境變數覆蓋")

        return True

    def verify_config_integration(self) -> bool:
        """驗證配置整合"""
        print("\n🔍 檢查配置整合...")

        try:
            # 載入完整配置
            config = self.config_loader.load_yaml_config("conf_autogen.yaml")

            # 載入研究工作流
            workflow_config = self.config_loader.load_workflow_config("research")

            # 檢查工作流中的智能體配置完整性
            for agent in workflow_config.agents:
                if not agent.llm_config:
                    print(f"❌ 智能體 {agent.name} 缺少 LLM 配置")
                    return False

                if not agent.system_message:
                    print(f"❌ 智能體 {agent.name} 缺少系統訊息")
                    return False

            print("✅ 配置整合檢查通過")
            print(f"   工作流智能體數量: {len(workflow_config.agents)}")

            return True

        except Exception as e:
            print(f"❌ 配置整合檢查失敗: {e}")
            return False

    def run_full_verification(self) -> bool:
        """執行完整驗證"""
        print("🚀 開始配置系統完整驗證")
        print("=" * 50)

        verification_steps = [
            ("配置檔案存在性", self.verify_config_file_exists),
            ("YAML 語法", self.verify_yaml_syntax),
            ("配置結構", self.verify_config_structure),
            ("LLM 配置", self.verify_llm_config),
            ("智能體配置", self.verify_agents_config),
            ("工作流配置", self.verify_workflows_config),
            ("工具配置", self.verify_tools_config),
            ("安全配置", self.verify_security_config),
            ("環境變數", self.verify_environment_variables),
            ("配置整合", self.verify_config_integration),
        ]

        results = []
        for step_name, verifier_func in verification_steps:
            try:
                result = verifier_func()
                results.append((step_name, result))
            except Exception as e:
                print(f"❌ {step_name} 驗證異常: {e}")
                results.append((step_name, False))

        # 顯示驗證結果
        print("\n" + "=" * 50)
        print("📊 驗證結果摘要")
        print("=" * 50)

        passed = 0
        total = len(results)

        for step_name, result in results:
            status = "✅ 通過" if result else "❌ 失敗"
            print(f"{step_name:15} : {status}")
            if result:
                passed += 1

        print("=" * 50)
        print(f"總計: {passed}/{total} 項驗證通過")

        if passed == total:
            print("🎉 所有驗證都通過！配置系統正常運作。")
        else:
            print("⚠️  部分驗證失敗，請檢查上述問題。")

        return passed == total


def main():
    """主函數"""
    verifier = ConfigSystemVerifier()

    try:
        success = verifier.run_full_verification()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  驗證被使用者中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 驗證過程發生錯誤: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
