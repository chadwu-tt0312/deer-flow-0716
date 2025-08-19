# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
配置系統測試模組

真正驗證 conf_autogen.yaml 配置檔案的載入和使用。
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.autogen_system.config.config_loader import ConfigLoader
from src.autogen_system.config.agent_config import (
    AgentConfig,
    WorkflowConfig,
    LLMConfig,
    AgentRole,
    WorkflowType,
    CodeExecutionConfig,
    GroupChatConfig,
)


class TestConfigSystem:
    """配置系統測試類別"""

    def setup_method(self):
        """測試前設置"""
        # 獲取專案根目錄
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.config_file = self.project_root / "conf_autogen.yaml"

        # 創建配置載入器
        self.config_loader = ConfigLoader(str(self.project_root))

    def test_config_file_exists(self):
        """測試配置檔案是否存在"""
        assert self.config_file.exists(), f"配置檔案不存在: {self.config_file}"
        print(f"✅ 配置檔案存在: {self.config_file}")

    def test_load_real_config_file(self):
        """測試載入真實的配置檔案"""
        config = self.config_loader.load_yaml_config("conf_autogen.yaml")

        # 驗證基本結構
        assert "autogen" in config, "缺少 autogen 配置區段"
        assert "agents" in config, "缺少 agents 配置區段"
        assert "workflows" in config, "缺少 workflows 配置區段"
        assert "tools" in config, "缺少 tools 配置區段"

        print("✅ 真實配置檔案載入成功")
        print(f"   - autogen 區段: {list(config['autogen'].keys())}")
        print(f"   - agents 區段: {list(config['agents'].keys())}")
        print(f"   - workflows 區段: {list(config['workflows'].keys())}")

    def test_llm_config_loading(self):
        """測試 LLM 配置載入"""
        config = self.config_loader.load_yaml_config("conf_autogen.yaml")
        autogen_config = config.get("autogen", {})

        # 載入 LLM 配置
        llm_config = self.config_loader.load_llm_config(
            autogen_config.get("default_llm_config", {})
        )

        # 驗證配置值
        assert llm_config.model == "gpt-4o-mini"
        assert llm_config.temperature == 0.2
        assert llm_config.max_tokens == 1000
        assert llm_config.timeout == 30

        print("✅ LLM 配置載入成功")
        print(f"   - 模型: {llm_config.model}")
        print(f"   - 溫度: {llm_config.temperature}")
        print(f"   - 最大 token: {llm_config.max_tokens}")

    def test_agent_configs_loading(self):
        """測試智能體配置載入"""
        config = self.config_loader.load_yaml_config("conf_autogen.yaml")
        agents_config = config.get("agents", {})

        # 測試每個智能體配置
        for agent_name, agent_dict in agents_config.items():
            agent_config = self.config_loader.load_agent_config(agent_name, agent_dict)

            # 驗證基本屬性
            assert isinstance(agent_config, AgentConfig)
            assert agent_config.name == agent_dict.get("name", agent_name)
            assert agent_config.system_message == agent_dict.get("system_message", "")

            # 驗證角色
            expected_role = AgentRole(agent_dict.get("role", agent_name))
            assert agent_config.role == expected_role

            print(f"✅ 智能體 {agent_name} 配置載入成功")
            print(f"   - 名稱: {agent_config.name}")
            print(f"   - 角色: {agent_config.role.value}")
            print(f"   - 工具數量: {len(agent_config.tools)}")

    def test_workflow_config_loading(self):
        """測試工作流配置載入"""
        # 載入研究工作流配置
        workflow_config = self.config_loader.load_workflow_config("research")

        # 驗證基本屬性
        assert isinstance(workflow_config, WorkflowConfig)
        assert workflow_config.name == "research"
        assert workflow_config.workflow_type == WorkflowType.RESEARCH
        assert len(workflow_config.agents) > 0

        print("✅ 研究工作流配置載入成功")
        print(f"   - 名稱: {workflow_config.name}")
        print(f"   - 類型: {workflow_config.workflow_type.value}")
        print(f"   - 智能體數量: {len(workflow_config.agents)}")

        # 驗證智能體
        for agent in workflow_config.agents:
            print(f"     - {agent.name} ({agent.role.value})")

    def test_tools_config_loading(self):
        """測試工具配置載入"""
        config = self.config_loader.load_yaml_config("conf_autogen.yaml")
        tools_config = config.get("tools", {})

        # 驗證工具配置
        assert "web_search" in tools_config
        assert "code_execution" in tools_config
        assert "mcp_servers" in tools_config

        # 測試特定工具配置
        web_search_config = self.config_loader.get_tool_config("web_search")
        assert web_search_config["provider"] == "tavily"
        assert web_search_config["max_results"] == 5

        print("✅ 工具配置載入成功")
        print(f"   - web_search: {web_search_config}")

    def test_security_config_loading(self):
        """測試安全配置載入"""
        security_config = self.config_loader.get_security_config()

        # 驗證安全配置
        assert security_config["enable_code_execution"] is True
        assert security_config["sandbox_mode"] is True
        assert ".py" in security_config["allowed_file_extensions"]
        assert security_config["max_file_size_mb"] == 10

        print("✅ 安全配置載入成功")
        print(f"   - 程式碼執行: {security_config['enable_code_execution']}")
        print(f"   - 沙盒模式: {security_config['sandbox_mode']}")

    def test_environment_variable_override(self):
        """測試環境變數覆蓋"""
        # 設置測試環境變數
        test_api_key = "test_key_12345"
        test_base_url = "https://test.openai.com/v1"

        with patch.dict(
            os.environ, {"OPENAI_API_KEY": test_api_key, "OPENAI_BASE_URL": test_base_url}
        ):
            # 載入配置
            config = self.config_loader.load_yaml_config("conf_autogen.yaml")
            autogen_config = config.get("autogen", {})

            # 載入 LLM 配置
            llm_config = self.config_loader.load_llm_config(
                autogen_config.get("default_llm_config", {})
            )

            # 驗證環境變數覆蓋
            assert llm_config.api_key == test_api_key
            assert llm_config.base_url == test_base_url

            print("✅ 環境變數覆蓋成功")
            print(f"   - API Key: {llm_config.api_key}")
            print(f"   - Base URL: {llm_config.base_url}")

    def test_config_validation(self):
        """測試配置驗證"""
        config = self.config_loader.load_yaml_config("conf_autogen.yaml")

        # 驗證必要配置項目
        required_sections = ["autogen", "agents", "workflows"]
        for section in required_sections:
            assert section in config, f"缺少必要配置區段: {section}"

        # 驗證 autogen 區段
        autogen_config = config["autogen"]
        assert "default_llm_config" in autogen_config
        assert "agent_defaults" in autogen_config

        # 驗證 agents 區段
        agents_config = config["agents"]
        required_agents = ["coordinator", "planner", "researcher", "coder", "reporter"]
        for agent in required_agents:
            assert agent in agents_config, f"缺少必要智能體: {agent}"

        # 驗證 workflows 區段
        workflows_config = config["workflows"]
        assert "research" in workflows_config

        print("✅ 配置驗證通過")
        print(f"   - 必要區段: {required_sections}")
        print(f"   - 必要智能體: {required_agents}")

    def test_config_integration(self):
        """測試配置整合"""
        # 載入完整配置
        config = self.config_loader.load_yaml_config("conf_autogen.yaml")

        # 載入研究工作流
        workflow_config = self.config_loader.load_workflow_config("research")

        # 驗證工作流中的智能體都有對應的配置
        for agent in workflow_config.agents:
            # 檢查智能體是否有 LLM 配置
            assert agent.llm_config is not None, f"智能體 {agent.name} 缺少 LLM 配置"

            # 檢查智能體是否有系統訊息
            assert agent.system_message, f"智能體 {agent.name} 缺少系統訊息"

            print(f"✅ 智能體 {agent.name} 配置完整")
            print(f"   - LLM: {agent.llm_config.model}")
            print(f"   - 工具: {agent.tools}")

    def test_error_handling(self):
        """測試錯誤處理"""
        # 測試載入不存在的配置檔案
        config = self.config_loader.load_yaml_config("non_existent.yaml")
        assert config == {}

        # 測試載入無效的 YAML 檔案
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write("invalid: yaml: content: [")
            tmp_path = tmp.name

        try:
            config = self.config_loader.load_yaml_config(tmp_path)
            # 應該返回空字典或處理錯誤
            assert isinstance(config, dict)
        finally:
            os.unlink(tmp_path)

        print("✅ 錯誤處理測試通過")

    def test_config_cache(self):
        """測試配置快取"""
        # 第一次載入
        config1 = self.config_loader.load_yaml_config("conf_autogen.yaml")

        # 第二次載入（應該使用快取）
        config2 = self.config_loader.load_yaml_config("conf_autogen.yaml")

        # 驗證快取機制
        assert config1 is config2, "配置快取未生效"

        print("✅ 配置快取測試通過")


def test_config_system_end_to_end():
    """端到端配置系統測試"""
    print("\n🚀 開始端到端配置系統測試")

    # 創建測試實例
    test_instance = TestConfigSystem()
    test_instance.setup_method()

    # 執行所有測試
    test_methods = [
        "test_config_file_exists",
        "test_load_real_config_file",
        "test_llm_config_loading",
        "test_agent_configs_loading",
        "test_workflow_config_loading",
        "test_tools_config_loading",
        "test_security_config_loading",
        "test_config_validation",
        "test_config_integration",
        "test_error_handling",
        "test_config_cache",
    ]

    for method_name in test_methods:
        method = getattr(test_instance, method_name)
        try:
            method()
            print(f"✅ {method_name} 通過")
        except Exception as e:
            print(f"❌ {method_name} 失敗: {e}")
            raise

    print("\n🎉 端到端配置系統測試完成!")


if __name__ == "__main__":
    # 直接運行測試
    test_config_system_end_to_end()
