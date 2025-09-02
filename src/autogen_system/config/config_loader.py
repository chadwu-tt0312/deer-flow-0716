# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
配置載入器模組

負責從 YAML 檔案或環境變數載入 AutoGen 系統配置。
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

from .agent_config import (
    AgentConfig,
    LLMConfig,
    AgentRole,
    DEFAULT_AGENT_CONFIGS,
)
from src.deerflow_logging import get_thread_logger


def _get_logger():
    """獲取當前 thread 的 logger"""
    try:
        return get_thread_logger()
    except RuntimeError:
        # 如果沒有設定 thread context，使用簡單的 logger
        from src.deerflow_logging import get_simple_logger

        return get_simple_logger(__name__)


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
            _get_logger().info(f"已載入環境變數檔案: {env_file}")
        else:
            _get_logger().info("未找到 .env 檔案，使用系統環境變數")

    def load_yaml_config(self, config_file: str = "conf_autogen.yaml") -> Dict[str, Any]:
        """載入 YAML 配置檔案"""
        config_path = self.config_dir / config_file

        if not config_path.exists():
            _get_logger().warning(f"配置檔案不存在: {config_path}")
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            return config or {}
        except Exception as e:
            _get_logger().error(f"載入配置檔案失敗: {config_path}, 錯誤: {e}")
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

        return AgentConfig(
            name=agent_dict.get("name", agent_name),
            role=role,
            system_message=agent_dict.get("system_message", ""),
            llm_config=llm_config,
            tools=agent_dict.get("tools", []),
            max_consecutive_auto_reply=agent_dict.get("max_consecutive_auto_reply", 10),
            human_input_mode=agent_dict.get("human_input_mode", "NEVER"),
            description=agent_dict.get("description", ""),
        )

    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """取得工具配置"""
        config = self.load_yaml_config()
        tools_config = config.get("tools", {})
        return tools_config.get(tool_name, {})

    def get_environment_info(self) -> Dict[str, Any]:
        """獲取環境變數資訊"""
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
        """驗證配置完整性"""
        validation_result = {"valid": True, "errors": [], "warnings": [], "missing_env_vars": []}

        # 檢查必要的環境變數 - 至少需要一個可用的 API 金鑰
        has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
        has_azure_key = bool(os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("BASIC_MODEL__API_KEY"))

        if not has_openai_key and not has_azure_key:
            validation_result["valid"] = False
            validation_result["errors"].append(
                "缺少必要的 API 金鑰: 需要設定 OPENAI_API_KEY 或 AZURE_OPENAI_API_KEY/BASIC_MODEL__API_KEY"
            )
            validation_result["missing_env_vars"].extend(
                ["OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "BASIC_MODEL__API_KEY"]
            )

        # 檢查配置檔案
        config = self.load_yaml_config()
        if not config:
            validation_result["warnings"].append("無法載入配置檔案")

        return validation_result


# 全域配置載入器實例
config_loader = ConfigLoader()
