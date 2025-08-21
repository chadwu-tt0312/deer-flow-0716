# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
配置載入器模組

負責從 YAML 檔案或環境變數載入 AutoGen 系統配置。
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv

from .agent_config import (
    AgentConfig,
    WorkflowConfig,
    LLMConfig,
    CodeExecutionConfig,
    GroupChatConfig,
    AgentRole,
    WorkflowType,
    DEFAULT_RESEARCH_WORKFLOW_CONFIG,
)
from src.logging import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """配置載入器"""

    def __init__(self, config_dir: str = "."):
        self.config_dir = Path(config_dir)
        self._configs_cache: Dict[str, Any] = {}

        # 載入環境變數
        self._load_environment_variables()

    def _load_environment_variables(self):
        """載入環境變數"""
        # 嘗試載入 .env 檔案
        env_file = self.config_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(f"已載入環境變數檔案: {env_file}")
        else:
            logger.info("未找到 .env 檔案，使用系統環境變數")

    def load_yaml_config(self, config_file: str = "conf_autogen.yaml") -> Dict[str, Any]:
        """載入 YAML 配置檔案"""
        config_path = self.config_dir / config_file

        if not config_path.exists():
            logger.warning(f"配置檔案不存在: {config_path}")
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            # logger.info(f"成功載入配置檔案: {config_path}")
            return config or {}
        except Exception as e:
            logger.error(f"載入配置檔案失敗: {config_path}, 錯誤: {e}")
            return {}

    def load_llm_config(
        self, config_dict: Dict[str, Any] = None, model_type: str = "default"
    ) -> LLMConfig:
        """
        載入 LLM 配置

        Args:
            config_dict: 配置字典，如果為 None 則從檔案載入
            model_type: 模型類型 ("default", "azure", "openai")
        """
        if config_dict is None:
            config_dict = self.load_yaml_config().get("autogen", {}).get("default_llm_config", {})

        # 根據模型類型載入不同的配置
        if model_type == "azure":
            return self._load_azure_openai_config(config_dict)
        else:
            return self._load_openai_config(config_dict)

    def _load_azure_openai_config(self, config_dict: Dict[str, Any]) -> LLMConfig:
        """載入 Azure OpenAI 配置"""
        # 從環境變數獲取 Azure OpenAI 配置
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

        if not all([azure_endpoint, azure_api_key, azure_deployment]):
            logger.warning("Azure OpenAI 環境變數不完整，回退到 OpenAI 配置")
            return self._load_openai_config(config_dict)

        # 從配置檔案讀取基本參數
        max_tokens = config_dict.get("max_tokens", 100000)
        timeout = config_dict.get("timeout", 30)

        return LLMConfig(
            model=azure_deployment,
            api_key=azure_api_key,
            base_url=azure_endpoint,
            temperature=config_dict.get("temperature", 0.2),
            max_tokens=max_tokens,
            timeout=timeout,
            extra_params={
                "azure_deployment": azure_deployment,
                "api_version": azure_api_version,
                "verify_ssl": config_dict.get("verify_ssl", False),
            },
        )

    def _load_openai_config(self, config_dict: Dict[str, Any]) -> LLMConfig:
        """載入 OpenAI 配置"""
        # 從環境變數獲取 OpenAI 配置，支援多種 API 金鑰來源
        api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("BASIC_MODEL__API_KEY")
            or os.getenv("AZURE_OPENAI_API_KEY")
        )
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        if not api_key:
            logger.error("未設定任何可用的 API 金鑰")
            raise ValueError(
                "請設定 OPENAI_API_KEY、BASIC_MODEL__API_KEY 或 AZURE_OPENAI_API_KEY 環境變數"
            )

        return LLMConfig(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=config_dict.get("temperature", 0.2),
            max_tokens=config_dict.get("max_tokens", 1000),
            timeout=config_dict.get("timeout", 30),
            seed=config_dict.get("seed"),
            extra_params=config_dict.get("extra_params", {}),
        )

    def load_agent_config(self, agent_name: str, agent_dict: Dict[str, Any]) -> AgentConfig:
        """載入單一智能體配置"""
        try:
            role = AgentRole(agent_dict.get("role", agent_name.lower()))
        except ValueError:
            logger.warning(f"未知的智能體角色: {agent_dict.get('role')}, 使用預設值")
            role = AgentRole.COORDINATOR

        # LLM 配置
        llm_config = None
        if "llm_config_override" in agent_dict:
            # 檢查是否有 Azure OpenAI 覆蓋配置
            override_config = agent_dict["llm_config_override"]
            if override_config.get("use_azure", False):
                llm_config = self._load_azure_openai_config(override_config)
            else:
                base_llm_config = self.load_llm_config()
                llm_config = LLMConfig(
                    model=override_config.get("model", base_llm_config.model),
                    api_key=override_config.get("api_key", base_llm_config.api_key),
                    base_url=override_config.get("base_url", base_llm_config.base_url),
                    temperature=override_config.get("temperature", base_llm_config.temperature),
                    max_tokens=override_config.get("max_tokens", base_llm_config.max_tokens),
                    timeout=override_config.get("timeout", base_llm_config.timeout),
                    seed=override_config.get("seed", base_llm_config.seed),
                    extra_params=override_config.get("extra_params", base_llm_config.extra_params),
                )
        else:
            # 使用預設配置
            llm_config = self.load_llm_config()

        # 程式碼執行配置
        code_execution_config = None
        if "code_execution_config" in agent_dict:
            code_config = agent_dict["code_execution_config"]
            if isinstance(code_config, dict):
                code_execution_config = CodeExecutionConfig(
                    enabled=True,
                    work_dir=code_config.get("work_dir", "temp_code"),
                    use_docker=code_config.get("use_docker", False),
                    timeout=code_config.get("timeout", 60),
                    max_execution_time=code_config.get("max_execution_time", 300),
                    allowed_modules=code_config.get("allowed_modules", []),
                )

        return AgentConfig(
            name=agent_dict.get("name", agent_name),
            role=role,
            system_message=agent_dict.get("system_message", ""),
            llm_config=llm_config,
            tools=agent_dict.get("tools", []),
            max_consecutive_auto_reply=agent_dict.get("max_consecutive_auto_reply", 10),
            human_input_mode=agent_dict.get("human_input_mode", "NEVER"),
            code_execution_config=code_execution_config,
            description=agent_dict.get("description", ""),
        )

    def load_workflow_config(self, workflow_name: str = "research") -> WorkflowConfig:
        """載入工作流配置"""
        config = self.load_yaml_config()

        # 如果沒有配置檔案，返回預設配置
        if not config:
            logger.info("使用預設研究工作流配置")
            return DEFAULT_RESEARCH_WORKFLOW_CONFIG

        workflows = config.get("workflows", {})
        workflow_dict = workflows.get(workflow_name, {})

        if not workflow_dict:
            logger.warning(f"找不到工作流配置: {workflow_name}, 使用預設配置")
            return DEFAULT_RESEARCH_WORKFLOW_CONFIG

        # 載入智能體配置
        agents_config = config.get("agents", {})
        enabled_agents = workflow_dict.get("enabled_agents", [])

        agents = []
        for agent_name in enabled_agents:
            if agent_name in agents_config:
                agent_config = self.load_agent_config(agent_name, agents_config[agent_name])
                agents.append(agent_config)
            else:
                logger.warning(f"找不到智能體配置: {agent_name}")

        # 群組對話配置
        group_chat_config = None
        if "group_chat" in config.get("autogen", {}):
            gc_config = config["autogen"]["group_chat"]
            group_chat_config = GroupChatConfig(
                agents=enabled_agents,
                max_round=gc_config.get("max_round", 50),
                admin_name=gc_config.get("admin_name", "Admin"),
                speaker_selection_method=gc_config.get("speaker_selection_method", "auto"),
                allow_repeat_speaker=gc_config.get("allow_repeat_speaker", True),
                send_introductions=gc_config.get("send_introductions", False),
                enable_clear_history=gc_config.get("enable_clear_history", False),
            )

        try:
            workflow_type = WorkflowType(workflow_name)
        except ValueError:
            workflow_type = WorkflowType.RESEARCH

        return WorkflowConfig(
            name=workflow_name,
            workflow_type=workflow_type,
            agents=agents,
            group_chat_config=group_chat_config,
            conversation_pattern=workflow_dict.get("workflow_type", "sequential"),
            max_iterations=workflow_dict.get("max_iterations", 3),
            human_feedback_steps=workflow_dict.get("human_feedback_steps", []),
            timeout=workflow_dict.get("timeout", 3600),
            extra_config=workflow_dict.get("extra_config", {}),
        )

    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """取得工具配置"""
        config = self.load_yaml_config()
        tools_config = config.get("tools", {})
        return tools_config.get(tool_name, {})

    def load_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """載入工具配置（新增方法）"""
        config = self.load_yaml_config()
        tools_config = config.get("tools", {})
        tool_config = tools_config.get(tool_name, {})

        # 如果工具配置中有環境變數引用，進行替換
        if tool_config and isinstance(tool_config, dict):
            tool_config = self._resolve_environment_variables(tool_config)

        return tool_config

    def load_security_config(self) -> Dict[str, Any]:
        """載入安全配置（新增方法）"""
        config = self.load_yaml_config()
        security_config = config.get("security", {})

        # 如果安全配置中有環境變數引用，進行替換
        if security_config and isinstance(security_config, dict):
            security_config = self._resolve_environment_variables(security_config)

        return security_config

    def load_performance_config(self) -> Dict[str, Any]:
        """載入效能配置（新增方法）"""
        config = self.load_yaml_config()
        performance_config = config.get("performance", {})

        # 如果效能配置中有環境變數引用，進行替換
        if performance_config and isinstance(performance_config, dict):
            performance_config = self._resolve_environment_variables(performance_config)

        return performance_config

    def load_logging_config(self) -> Dict[str, Any]:
        """載入記錄配置（新增方法）"""
        config = self.load_yaml_config()
        logging_config = config.get("LOGGING", {})

        # 如果記錄配置中有環境變數引用，進行替換
        if logging_config and isinstance(logging_config, dict):
            logging_config = self._resolve_environment_variables(logging_config)

        return logging_config

    def _resolve_environment_variables(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """解析配置中的環境變數引用"""
        resolved_config = {}

        for key, value in config_dict.items():
            if isinstance(value, str) and value.startswith("$"):
                # 環境變數引用，例如 $AZURE_OPENAI_ENDPOINT
                env_var = value[1:]  # 移除 $ 符號
                resolved_value = os.getenv(env_var)
                if resolved_value is not None:
                    resolved_config[key] = resolved_value
                else:
                    logger.warning(f"環境變數 {env_var} 未設定")
                    resolved_config[key] = value  # 保留原始值
            elif isinstance(value, dict):
                # 遞歸處理嵌套字典
                resolved_config[key] = self._resolve_environment_variables(value)
            elif isinstance(value, list):
                # 處理列表中的環境變數引用
                resolved_list = []
                for item in value:
                    if isinstance(item, str) and item.startswith("$"):
                        env_var = item[1:]
                        resolved_item = os.getenv(env_var, item)
                        resolved_list.append(resolved_item)
                    else:
                        resolved_list.append(item)
                resolved_config[key] = resolved_list
            else:
                resolved_config[key] = value

        return resolved_config

    def get_environment_info(self) -> Dict[str, Any]:
        """獲取環境變數資訊（新增方法）"""
        # 檢查可用的 API 金鑰
        openai_api_key = os.getenv("OPENAI_API_KEY")
        basic_model_api_key = os.getenv("BASIC_MODEL__API_KEY")
        azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")

        # 判斷是否有可用的 API 金鑰
        has_any_api_key = bool(openai_api_key or basic_model_api_key or azure_openai_api_key)

        env_info = {
            "openai": {
                "api_key_set": bool(openai_api_key),
                "model": os.getenv("OPENAI_MODEL", "未設定"),
                "base_url": os.getenv("OPENAI_BASE_URL", "未設定"),
                "has_any_key": has_any_api_key,
            },
            "azure_openai": {
                "endpoint_set": bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
                "api_key_set": bool(azure_openai_api_key or basic_model_api_key),
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "未設定"),
                "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "未設定"),
                "basic_model_key_set": bool(basic_model_api_key),
            },
            "search": {
                "search_api": os.getenv("SEARCH_API", "未設定"),
                "tavily_key_set": bool(os.getenv("TAVILY_API_KEY")),
                "brave_key_set": bool(os.getenv("BRAVE_API_KEY")),
            },
            "system": {
                "use_autogen_system": os.getenv("USE_AUTOGEN_SYSTEM", "false"),
                "debug_mode": os.getenv("DEBUG", "false"),
                "log_level": os.getenv("LOG_LEVEL", "INFO"),
            },
        }

        return env_info

    def validate_configuration(self) -> Dict[str, Any]:
        """驗證配置完整性（新增方法）"""
        validation_result = {"valid": True, "errors": [], "warnings": [], "missing_env_vars": []}

        # 檢查必要的環境變數 - 至少需要一個可用的 API 金鑰
        required_env_vars = []
        optional_env_vars = [
            "OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_DEPLOYMENT_NAME",
            "BASIC_MODEL__API_KEY",
            "TAVILY_API_KEY",
        ]

        # 檢查是否有可用的 API 金鑰
        has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
        has_azure_key = bool(os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("BASIC_MODEL__API_KEY"))
        has_azure_endpoint = bool(os.getenv("AZURE_OPENAI_ENDPOINT"))

        if not has_openai_key and not has_azure_key:
            validation_result["valid"] = False
            validation_result["errors"].append(
                "缺少必要的 API 金鑰: 需要設定 OPENAI_API_KEY 或 AZURE_OPENAI_API_KEY/BASIC_MODEL__API_KEY"
            )
            validation_result["missing_env_vars"].extend(
                ["OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "BASIC_MODEL__API_KEY"]
            )

        # 如果使用 Azure OpenAI，檢查必要的配置
        if has_azure_key and not has_azure_endpoint:
            validation_result["warnings"].append(
                "使用 Azure OpenAI 時建議設定 AZURE_OPENAI_ENDPOINT"
            )

        for var in optional_env_vars:
            if not os.getenv(var):
                validation_result["warnings"].append(f"缺少可選的環境變數: {var}")

        # 檢查配置檔案
        config = self.load_yaml_config()
        if not config:
            validation_result["warnings"].append("無法載入配置檔案")

        return validation_result


# 全域配置載入器實例
config_loader = ConfigLoader()
