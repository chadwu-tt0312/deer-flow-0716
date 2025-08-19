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

    def load_yaml_config(self, config_file: str = "conf_autogen.yaml") -> Dict[str, Any]:
        """載入 YAML 配置檔案"""
        config_path = self.config_dir / config_file

        if not config_path.exists():
            logger.warning(f"配置檔案不存在: {config_path}")
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"成功載入配置檔案: {config_path}")
            return config or {}
        except Exception as e:
            logger.error(f"載入配置檔案失敗: {config_path}, 錯誤: {e}")
            return {}

    def load_llm_config(self, config_dict: Dict[str, Any] = None) -> LLMConfig:
        """載入 LLM 配置"""
        if config_dict is None:
            config_dict = self.load_yaml_config().get("autogen", {}).get("default_llm_config", {})

        # 從環境變數覆蓋配置
        api_key = config_dict.get("api_key") or os.getenv("OPENAI_API_KEY")
        base_url = config_dict.get("base_url") or os.getenv("OPENAI_BASE_URL")

        return LLMConfig(
            model=config_dict.get("model", "gpt-4o-mini"),
            api_key=api_key,
            base_url=base_url,
            temperature=config_dict.get("temperature", 0.7),
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
            base_llm_config = self.load_llm_config()
            override_config = agent_dict["llm_config_override"]

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

    def get_security_config(self) -> Dict[str, Any]:
        """取得安全配置"""
        config = self.load_yaml_config()
        return config.get(
            "security",
            {
                "enable_code_execution": True,
                "sandbox_mode": True,
                "allowed_file_extensions": [".py", ".txt", ".md", ".json", ".csv"],
                "max_file_size_mb": 10,
            },
        )


# 全域配置載入器實例
config_loader = ConfigLoader()
