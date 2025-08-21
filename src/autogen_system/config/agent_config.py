# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
智能體配置模組

定義 AutoGen 智能體的配置結構和相關資料類別。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum


class AgentRole(Enum):
    """智能體角色定義"""

    COORDINATOR = "coordinator"
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    REPORTER = "reporter"
    HUMAN_PROXY = "human_proxy"


class WorkflowType(Enum):
    """工作流類型定義"""

    RESEARCH = "research"
    PODCAST = "podcast"
    PPT = "ppt"
    PROSE = "prose"
    PROMPT_ENHANCER = "prompt_enhancer"


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
class CodeExecutionConfig:
    """程式碼執行配置"""

    enabled: bool = False
    work_dir: str = "temp_code"
    use_docker: bool = False
    timeout: int = 60
    max_execution_time: int = 300
    allowed_modules: List[str] = field(
        default_factory=lambda: ["pandas", "numpy", "matplotlib", "requests", "json", "csv"]
    )


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
    code_execution_config: Optional[CodeExecutionConfig] = None
    description: str = ""
    is_termination_msg: Optional[callable] = None
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
            config["llm_config"] = {
                "model": self.llm_config.model,
                "temperature": self.llm_config.temperature,
                "max_tokens": self.llm_config.max_tokens,
                "timeout": self.llm_config.timeout,
                **self.llm_config.extra_params,
            }

            if self.llm_config.api_key:
                config["llm_config"]["api_key"] = self.llm_config.api_key
            if self.llm_config.base_url:
                config["llm_config"]["base_url"] = self.llm_config.base_url
            if self.llm_config.seed:
                config["llm_config"]["seed"] = self.llm_config.seed

        if self.code_execution_config:
            if self.code_execution_config.enabled:
                config["code_execution_config"] = {
                    "work_dir": self.code_execution_config.work_dir,
                    "use_docker": self.code_execution_config.use_docker,
                    "timeout": self.code_execution_config.timeout,
                }
            else:
                config["code_execution_config"] = False

        if self.is_termination_msg:
            config["is_termination_msg"] = self.is_termination_msg

        return config


@dataclass
class GroupChatConfig:
    """群組對話配置"""

    agents: List[str]  # 智能體名稱列表
    max_round: int = 50
    admin_name: str = "Admin"
    speaker_selection_method: str = "auto"  # auto, manual, round_robin, random
    allow_repeat_speaker: bool = True
    send_introductions: bool = False
    enable_clear_history: bool = False


@dataclass
class WorkflowConfig:
    """工作流配置類別"""

    name: str
    workflow_type: WorkflowType
    agents: List[AgentConfig] = field(default_factory=list)
    group_chat_config: Optional[GroupChatConfig] = None
    conversation_pattern: str = "sequential"  # sequential, parallel, custom
    max_iterations: int = 3
    human_feedback_steps: List[str] = field(default_factory=list)
    timeout: int = 3600  # 1小時超時

    # 特定工作流的額外配置
    extra_config: Dict[str, Any] = field(default_factory=dict)

    def get_agent_by_role(self, role: AgentRole) -> Optional[AgentConfig]:
        """根據角色取得智能體配置"""
        for agent in self.agents:
            if agent.role == role:
                return agent
        return None

    def get_agent_by_name(self, name: str) -> Optional[AgentConfig]:
        """根據名稱取得智能體配置"""
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None


# 預設配置
DEFAULT_LLM_CONFIG = LLMConfig()

DEFAULT_RESEARCH_WORKFLOW_CONFIG = WorkflowConfig(
    name="default_research",
    workflow_type=WorkflowType.RESEARCH,
    agents=[
        AgentConfig(
            name="CoordinatorAgent",
            role=AgentRole.COORDINATOR,
            system_message="你是協調者，負責管理整個研究工作流程。",
            llm_config=LLMConfig(temperature=0.3),
        ),
        AgentConfig(
            name="PlannerAgent",
            role=AgentRole.PLANNER,
            system_message="你是計劃者，負責分析需求並制定詳細的執行計劃。",
            llm_config=LLMConfig(temperature=0.5),
        ),
        AgentConfig(
            name="ResearcherAgent",
            role=AgentRole.RESEARCHER,
            system_message="你是研究員，負責進行網路搜尋和資訊收集。",
            tools=["web_search", "crawl_tool", "local_search"],
        ),
        AgentConfig(
            name="CoderAgent",
            role=AgentRole.CODER,
            system_message="你是程式設計師，負責程式碼分析和執行。",
            tools=["python_repl"],
            code_execution_config=CodeExecutionConfig(enabled=True),
        ),
        AgentConfig(
            name="ReporterAgent",
            role=AgentRole.REPORTER,
            system_message="你是報告撰寫者，負責整理資訊並生成最終報告。",
            llm_config=LLMConfig(temperature=0),
        ),
    ],
    group_chat_config=GroupChatConfig(
        agents=[
            "CoordinatorAgent",
            "PlannerAgent",
            "ResearcherAgent",
            "CoderAgent",
            "ReporterAgent",
        ],
        max_round=50,
        speaker_selection_method="auto",
    ),
    human_feedback_steps=["plan_review"],
    max_iterations=3,
)
