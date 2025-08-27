# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
智能體配置模組

定義 AutoGen 智能體的配置結構和相關資料類別。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


class AgentRole(Enum):
    """智能體角色定義"""

    COORDINATOR = "coordinator"
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    REPORTER = "reporter"


@dataclass
class LLMConfig:
    """LLM 配置"""

    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: int = 30
    seed: Optional[int] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def to_autogen_config(self) -> Dict[str, Any]:
        """轉換為 AutoGen 標準的 LLM 配置格式"""
        config = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            **self.extra_params,
        }

        if self.api_key:
            config["api_key"] = self.api_key
        if self.base_url:
            config["base_url"] = self.base_url
        if self.seed:
            config["seed"] = self.seed

        return config


@dataclass
class AgentConfig:
    """智能體配置類別"""

    name: str
    role: AgentRole
    system_message: str = ""
    llm_config: Optional[LLMConfig] = None
    tools: List[str] = field(default_factory=list)
    max_consecutive_auto_reply: int = 10
    human_input_mode: str = "NEVER"  # NEVER, TERMINATE, ALWAYS
    description: str = ""
    max_round: int = 50

    def to_autogen_config(self) -> Dict[str, Any]:
        """轉換為 AutoGen 標準配置格式"""
        config = {
            "name": self.name,
            "system_message": self.system_message,
            "max_consecutive_auto_reply": self.max_consecutive_auto_reply,
            "human_input_mode": self.human_input_mode,
            "description": self.description,
        }

        if self.llm_config:
            config["llm_config"] = self.llm_config.to_autogen_config()

        return config


# 預設配置
DEFAULT_LLM_CONFIG = LLMConfig()

DEFAULT_AGENT_CONFIGS = {
    "coordinator": AgentConfig(
        name="CoordinatorAgent",
        role=AgentRole.COORDINATOR,
        system_message="你是協調者，負責管理整個研究工作流程。",
        llm_config=LLMConfig(temperature=0.3),
    ),
    "planner": AgentConfig(
        name="PlannerAgent",
        role=AgentRole.PLANNER,
        system_message="你是計劃者，負責分析需求並制定詳細的執行計劃。",
        llm_config=LLMConfig(temperature=0.5),
    ),
    "researcher": AgentConfig(
        name="ResearcherAgent",
        role=AgentRole.RESEARCHER,
        system_message="你是研究員，負責進行網路搜尋和資訊收集。",
        tools=["web_search", "crawl_tool"],
    ),
    "coder": AgentConfig(
        name="CoderAgent",
        role=AgentRole.CODER,
        system_message="你是程式設計師，負責程式碼分析和執行。",
        tools=["python_repl"],
    ),
    "reporter": AgentConfig(
        name="ReporterAgent",
        role=AgentRole.REPORTER,
        system_message="你是報告撰寫者，負責整理資訊並生成最終報告。",
        llm_config=LLMConfig(temperature=0),
    ),
}
