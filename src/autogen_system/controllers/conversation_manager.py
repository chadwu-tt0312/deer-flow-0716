# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 對話管理器

負責管理 AutoGen 智能體之間的對話流程和協作。
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# TODO: Fix AutoGen imports - current version has different API structure
try:
    from autogen_core import (
        SingleThreadedAgentRuntime,
        AgentId,
        MessageContext,
        DefaultSubscription,
        AgentConfig,
        AgentRole,
    )
except ImportError:
    # Fallback imports or mock classes
    SingleThreadedAgentRuntime = None
    AgentId = None
    MessageContext = None
    DefaultSubscription = None
    AgentConfig = None
    AgentRole = None


# Mock classes for missing dependencies
class MockSingleThreadedAgentRuntime:
    """Mock SingleThreadedAgentRuntime for compatibility"""

    def __init__(self, *args, **kwargs):
        self.agents = {}

    async def register_and_start_agent(self, agent):
        """Mock register_and_start_agent method"""
        self.agents[agent.name] = agent
        return True

    def __getattr__(self, name):
        """Handle any other attribute access"""
        return lambda *args, **kwargs: None


class MockChatCompletionClient:
    """Mock ChatCompletionClient for compatibility"""

    def __init__(self, *args, **kwargs):
        self.config = kwargs.get("config", {})
        self.api_key = kwargs.get("api_key", "mock_key")
        self.base_url = kwargs.get("base_url", "https://api.openai.com/v1")

    def get(self, key, default=None):
        """Mock get method for config access"""
        if hasattr(self, key):
            return getattr(self, key)
        return self.config.get(key, default)

    def __getattr__(self, name):
        """Handle any other attribute access"""
        return lambda *args, **kwargs: None


ChatCompletionClient = MockChatCompletionClient
OpenAIChatCompletionClient = MockChatCompletionClient
UserMessage = type("UserMessage", (), {})
SystemMessage = type("SystemMessage", (), {})

# 如果無法導入真實的類別，使用 mock 版本
if SingleThreadedAgentRuntime is None:
    SingleThreadedAgentRuntime = MockSingleThreadedAgentRuntime

# 如果無法導入 AgentRole，創建 mock 版本
if AgentRole is None:
    from enum import Enum

    class MockAgentRole(Enum):
        COORDINATOR = "coordinator"
        PLANNER = "planner"
        RESEARCHER = "researcher"
        CODER = "coder"
        REPORTER = "reporter"
        HUMAN_PROXY = "human_proxy"

    AgentRole = MockAgentRole

# 如果無法導入 AgentConfig，創建 mock 版本
if AgentConfig is None:
    from dataclasses import dataclass

    @dataclass
    class MockAgentConfig:
        name: str
        role: str
        system_message: str = ""
        max_consecutive_auto_reply: int = 10
        human_input_mode: str = "NEVER"
        code_execution_config: Any = None

        def to_autogen_config(self) -> Dict[str, Any]:
            """轉換為 AutoGen 標準配置格式"""
            return {
                "name": self.name,
                "system_message": self.system_message,
                "max_consecutive_auto_reply": self.max_consecutive_auto_reply,
                "human_input_mode": self.human_input_mode,
            }

    AgentConfig = MockAgentConfig

from src.logging import get_logger
from ..agents import CoordinatorAgent, PlannerAgent, ResearcherAgent, CoderAgent, ReporterAgent

logger = get_logger(__name__)


class WorkflowState(Enum):
    """工作流程狀態"""

    INITIALIZING = "initializing"
    COORDINATOR_ANALYSIS = "coordinator_analysis"
    BACKGROUND_INVESTIGATION = "background_investigation"
    PLANNING = "planning"
    PLAN_REVIEW = "plan_review"
    EXECUTION = "execution"
    RESEARCH = "research"
    CODING = "coding"
    REPORTING = "reporting"
    HUMAN_FEEDBACK = "human_feedback"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ConversationConfig:
    """對話配置"""

    max_plan_iterations: int = 3
    max_step_iterations: int = 5
    max_conversation_turns: int = 50
    enable_background_investigation: bool = True
    enable_human_feedback: bool = False
    auto_accept_plan: bool = True
    timeout_seconds: int = 300
    debug_mode: bool = False
    # 添加缺失的參數
    max_search_results: int = 3
    report_style: str = "academic"
    resources: List[Any] = None
    mcp_settings: Dict[str, Any] = None
    # 添加 human_feedback_enabled 參數
    human_feedback_enabled: bool = False

    def __post_init__(self):
        if self.resources is None:
            self.resources = []
        if self.mcp_settings is None:
            self.mcp_settings = {}


@dataclass
class ConversationState:
    """對話狀態"""

    workflow_state: WorkflowState = WorkflowState.INITIALIZING
    user_input: str = ""
    research_topic: str = ""
    locale: str = "zh-TW"
    current_plan: Optional[Dict[str, Any]] = None
    plan_iterations: int = 0
    execution_step: int = 0
    messages: List[Dict[str, Any]] = field(default_factory=list)
    background_investigation_results: str = ""
    final_report: str = ""
    error_message: str = ""
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class AutoGenConversationManager:
    """
    AutoGen 對話管理器

    管理多智能體對話流程，協調各智能體完成研究任務。
    """

    def __init__(self, model_client: ChatCompletionClient, config: ConversationConfig = None):
        """
        初始化對話管理器

        Args:
            model_client: 聊天完成客戶端
            config: 對話配置
        """
        self.model_client = model_client
        self.config = config or ConversationConfig()
        self.runtime: Optional[SingleThreadedAgentRuntime] = None
        self.agents: Dict[str, Any] = {}
        self.conversation_state = ConversationState()
        self.workflow_handlers: Dict[WorkflowState, Callable] = {}

        logger.info("AutoGen 對話管理器初始化")

    async def initialize_runtime(self):
        """初始化 AutoGen 運行時環境"""
        try:
            logger.info("初始化 AutoGen 運行時環境")

            # 創建運行時
            self.runtime = SingleThreadedAgentRuntime()

            # 創建智能體
            await self._create_agents()

            # 設置工作流處理器
            self._setup_workflow_handlers()

            logger.info("AutoGen 運行時環境初始化完成")

        except Exception as e:
            logger.error(f"初始化 AutoGen 運行時環境失敗: {e}")
            raise

    async def _create_agents(self):
        """創建所有智能體"""
        try:
            logger.info("創建 AutoGen 智能體")

            # 創建協調者智能體
            coordinator_config = AgentConfig(
                name="coordinator",
                role=AgentRole.COORDINATOR,
                system_message="你是 DeerFlow，一個友善的AI助手。",
                max_consecutive_auto_reply=1,
            )
            self.agents["coordinator"] = CoordinatorAgent(coordinator_config)
            await self.runtime.register_and_start_agent(self.agents["coordinator"])

            # 創建計劃者智能體
            planner_config = AgentConfig(
                name="planner",
                role=AgentRole.PLANNER,
                system_message="你是計劃者智能體，負責制定研究計劃。",
                max_consecutive_auto_reply=3,
            )
            self.agents["planner"] = PlannerAgent(planner_config)
            await self.runtime.register_and_start_agent(self.agents["planner"])

            # 創建研究者智能體
            researcher_config = AgentConfig(
                name="researcher",
                role=AgentRole.RESEARCHER,
                system_message="你是研究者智能體，負責執行研究任務。",
                max_consecutive_auto_reply=3,
            )
            self.agents["researcher"] = ResearcherAgent(researcher_config)
            await self.runtime.register_and_start_agent(self.agents["researcher"])

            # 創建程式設計師智能體
            coder_config = AgentConfig(
                name="coder",
                role=AgentRole.CODER,
                system_message="你是程式設計師智能體，負責編寫和測試代碼。",
                max_consecutive_auto_reply=3,
            )
            self.agents["coder"] = CoderAgent(coder_config)
            await self.runtime.register_and_start_agent(self.agents["coder"])

            # 創建報告者智能體
            reporter_config = AgentConfig(
                name="reporter",
                role=AgentRole.REPORTER,
                system_message="你是報告者智能體，負責生成最終報告。",
                max_consecutive_auto_reply=3,
            )
            self.agents["reporter"] = ReporterAgent(reporter_config)
            await self.runtime.register_and_start_agent(self.agents["reporter"])

            logger.info(f"成功創建 {len(self.agents)} 個智能體")

        except Exception as e:
            logger.error(f"創建智能體失敗: {e}")
            raise

    def _setup_workflow_handlers(self):
        """設置工作流處理器"""
        self.workflow_handlers = {
            WorkflowState.COORDINATOR_ANALYSIS: self._handle_coordinator_analysis,
            WorkflowState.BACKGROUND_INVESTIGATION: self._handle_background_investigation,
            WorkflowState.PLANNING: self._handle_planning,
            WorkflowState.PLAN_REVIEW: self._handle_plan_review,
            WorkflowState.EXECUTION: self._handle_execution,
            WorkflowState.RESEARCH: self._handle_research,
            WorkflowState.CODING: self._handle_coding,
            WorkflowState.REPORTING: self._handle_reporting,
            WorkflowState.HUMAN_FEEDBACK: self._handle_human_feedback,
        }

    async def start_conversation(self, user_input: str) -> ConversationState:
        """
        開始新的對話

        Args:
            user_input: 用戶輸入

        Returns:
            ConversationState: 對話狀態
        """
        logger.info(f"開始新對話: {user_input}")

        try:
            # 重置對話狀態
            self.conversation_state = ConversationState(
                user_input=user_input, workflow_state=WorkflowState.COORDINATOR_ANALYSIS
            )

            # 初始化運行時（如果尚未初始化）
            if not self.runtime:
                await self.initialize_runtime()

            # 開始工作流
            await self._execute_workflow()

            return self.conversation_state

        except Exception as e:
            logger.error(f"對話執行失敗: {e}")
            self.conversation_state.workflow_state = WorkflowState.ERROR
            self.conversation_state.error_message = str(e)
            return self.conversation_state

    async def _execute_workflow(self):
        """執行工作流"""
        max_iterations = self.config.max_conversation_turns
        iteration = 0

        while iteration < max_iterations and self.conversation_state.workflow_state not in [
            WorkflowState.COMPLETED,
            WorkflowState.ERROR,
        ]:
            logger.info(
                f"工作流第 {iteration + 1} 輪，狀態: {self.conversation_state.workflow_state.value}"
            )

            # 更新時間戳
            self.conversation_state.updated_at = datetime.now()

            # 執行當前狀態的處理器
            handler = self.workflow_handlers.get(self.conversation_state.workflow_state)
            if handler:
                try:
                    await handler()
                except Exception as e:
                    logger.error(f"工作流處理器執行失敗: {e}")
                    self.conversation_state.workflow_state = WorkflowState.ERROR
                    self.conversation_state.error_message = str(e)
                    break
            else:
                logger.error(f"未找到狀態處理器: {self.conversation_state.workflow_state}")
                self.conversation_state.workflow_state = WorkflowState.ERROR
                self.conversation_state.error_message = (
                    f"未知工作流狀態: {self.conversation_state.workflow_state}"
                )
                break

            iteration += 1

            # 防止無限循環
            if iteration >= max_iterations:
                logger.warning("達到最大對話輪數限制")
                self.conversation_state.workflow_state = WorkflowState.ERROR
                self.conversation_state.error_message = "對話超時"

    async def _handle_coordinator_analysis(self):
        """處理協調者分析階段"""
        logger.info("執行協調者分析")

        try:
            coordinator = self.agents["coordinator"]

            # 協調者分析用戶輸入
            analysis_result = await coordinator.analyze_user_input(
                self.conversation_state.user_input
            )

            # 更新對話狀態
            self.conversation_state.research_topic = analysis_result.get(
                "research_topic", self.conversation_state.user_input
            )
            self.conversation_state.locale = analysis_result.get("locale", "zh-TW")

            # 記錄分析結果
            self.conversation_state.execution_history.append(
                {
                    "step": "coordinator_analysis",
                    "result": analysis_result,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # 決定下一步
            next_action = analysis_result.get("next_action", "planner")
            if next_action == "direct":
                self.conversation_state.workflow_state = WorkflowState.REPORTING
            elif self.config.enable_background_investigation:
                self.conversation_state.workflow_state = WorkflowState.BACKGROUND_INVESTIGATION
            else:
                self.conversation_state.workflow_state = WorkflowState.PLANNING

        except Exception as e:
            logger.error(f"協調者分析失敗: {e}")
            raise

    async def _handle_background_investigation(self):
        """處理背景調查階段"""
        logger.info("執行背景調查")

        try:
            researcher = self.agents["researcher"]

            # 執行背景調查
            investigation_result = await researcher.investigate_topic(
                self.conversation_state.research_topic
            )

            # 更新對話狀態
            self.conversation_state.background_investigation_results = investigation_result

            # 記錄調查結果
            self.conversation_state.execution_history.append(
                {
                    "step": "background_investigation",
                    "result": investigation_result,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # 進入計劃階段
            self.conversation_state.workflow_state = WorkflowState.PLANNING

        except Exception as e:
            logger.error(f"背景調查失敗: {e}")
            raise

    async def _handle_planning(self):
        """處理計劃階段"""
        logger.info("執行計劃生成")

        try:
            planner = self.agents["planner"]

            # 生成計劃
            plan_context = {
                "user_input": self.conversation_state.user_input,
                "research_topic": self.conversation_state.research_topic,
                "background_investigation": self.conversation_state.background_investigation_results,
                "locale": self.conversation_state.locale,
            }

            plan_result = await planner.create_plan(plan_context)

            # 更新對話狀態
            self.conversation_state.current_plan = plan_result
            self.conversation_state.plan_iterations += 1

            # 記錄計劃結果
            self.conversation_state.execution_history.append(
                {
                    "step": "planning",
                    "plan_iteration": self.conversation_state.plan_iterations,
                    "result": plan_result,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # 決定下一步
            if self.config.enable_human_feedback and not self.config.auto_accept_plan:
                self.conversation_state.workflow_state = WorkflowState.HUMAN_FEEDBACK
            else:
                self.conversation_state.workflow_state = WorkflowState.EXECUTION

        except Exception as e:
            logger.error(f"計劃生成失敗: {e}")
            raise

    async def _handle_plan_review(self):
        """處理計劃審查階段"""
        logger.info("執行計劃審查")

        # TODO: 實現計劃審查邏輯
        self.conversation_state.workflow_state = WorkflowState.EXECUTION

    async def _handle_execution(self):
        """處理執行階段"""
        logger.info("執行計劃步驟")

        try:
            if not self.conversation_state.current_plan:
                logger.error("沒有可執行的計劃")
                self.conversation_state.workflow_state = WorkflowState.PLANNING
                return

            plan_steps = self.conversation_state.current_plan.get("steps", [])

            if self.conversation_state.execution_step >= len(plan_steps):
                # 所有步驟已完成，進入報告階段
                self.conversation_state.workflow_state = WorkflowState.REPORTING
                return

            current_step = plan_steps[self.conversation_state.execution_step]
            step_type = current_step.get("step_type", "research")

            # 根據步驟類型決定下一個狀態
            if step_type.lower() == "research":
                self.conversation_state.workflow_state = WorkflowState.RESEARCH
            elif step_type.lower() in ["processing", "code", "analysis"]:
                self.conversation_state.workflow_state = WorkflowState.CODING
            else:
                # 預設為研究
                self.conversation_state.workflow_state = WorkflowState.RESEARCH

        except Exception as e:
            logger.error(f"執行階段處理失敗: {e}")
            raise

    async def _handle_research(self):
        """處理研究階段"""
        logger.info("執行研究步驟")

        try:
            researcher = self.agents["researcher"]

            # 獲取當前步驟
            plan_steps = self.conversation_state.current_plan.get("steps", [])
            current_step = plan_steps[self.conversation_state.execution_step]

            # 執行研究
            research_result = await researcher.execute_research_step(current_step)

            # 更新步驟結果
            current_step["execution_result"] = research_result
            current_step["completed"] = True

            # 記錄執行結果
            self.conversation_state.execution_history.append(
                {
                    "step": "research",
                    "step_index": self.conversation_state.execution_step,
                    "result": research_result,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # 進入下一步驟
            self.conversation_state.execution_step += 1
            self.conversation_state.workflow_state = WorkflowState.EXECUTION

        except Exception as e:
            logger.error(f"研究步驟執行失敗: {e}")
            raise

    async def _handle_coding(self):
        """處理編程階段"""
        logger.info("執行編程步驟")

        try:
            coder = self.agents["coder"]

            # 獲取當前步驟
            plan_steps = self.conversation_state.current_plan.get("steps", [])
            current_step = plan_steps[self.conversation_state.execution_step]

            # 執行編程
            coding_result = await coder.execute_coding_step(current_step)

            # 更新步驟結果
            current_step["execution_result"] = coding_result
            current_step["completed"] = True

            # 記錄執行結果
            self.conversation_state.execution_history.append(
                {
                    "step": "coding",
                    "step_index": self.conversation_state.execution_step,
                    "result": coding_result,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # 進入下一步驟
            self.conversation_state.execution_step += 1
            self.conversation_state.workflow_state = WorkflowState.EXECUTION

        except Exception as e:
            logger.error(f"編程步驟執行失敗: {e}")
            raise

    async def _handle_reporting(self):
        """處理報告階段"""
        logger.info("生成最終報告")

        try:
            reporter = self.agents["reporter"]

            # 生成報告
            report_context = {
                "user_input": self.conversation_state.user_input,
                "research_topic": self.conversation_state.research_topic,
                "plan": self.conversation_state.current_plan,
                "execution_history": self.conversation_state.execution_history,
                "locale": self.conversation_state.locale,
            }

            final_report = await reporter.generate_final_report(report_context)

            # 更新對話狀態
            self.conversation_state.final_report = final_report
            self.conversation_state.workflow_state = WorkflowState.COMPLETED

            # 記錄報告結果
            self.conversation_state.execution_history.append(
                {
                    "step": "reporting",
                    "result": final_report,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            logger.info("對話流程完成")

        except Exception as e:
            logger.error(f"報告生成失敗: {e}")
            raise

    async def _handle_human_feedback(self):
        """處理人工反饋階段"""
        logger.info("等待人工反饋")

        try:
            # 如果沒有啟用人工反饋，自動繼續
            if not self.config.enable_human_feedback:
                self.conversation_state.workflow_state = WorkflowState.EXECUTION
                return

            # 導入人機互動組件
            from ..interaction import HumanFeedbackManager, FeedbackType

            # 創建反饋管理器（如果尚未創建）
            if not hasattr(self, "_feedback_manager"):
                self._feedback_manager = HumanFeedbackManager()

            # 請求計劃審查
            plan_data = self.conversation_state.current_plan or {}

            response = await self._feedback_manager.request_feedback(
                FeedbackType.PLAN_REVIEW,
                "計劃審查",
                "請審查此研究計劃",
                {
                    "plan": plan_data,
                    "research_topic": self.conversation_state.research_topic,
                    "user_input": self.conversation_state.user_input,
                },
                timeout_seconds=300,
            )

            # 記錄反饋結果
            self.conversation_state.execution_history.append(
                {
                    "step": "human_feedback",
                    "feedback_type": "plan_review",
                    "response_type": response.response_type,
                    "response_data": response.data,
                    "comment": response.comment,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # 根據反饋結果決定下一步
            if response.response_type == "approve":
                logger.info("用戶批准計劃，繼續執行")
                self.conversation_state.workflow_state = WorkflowState.EXECUTION
            elif response.response_type == "modify":
                logger.info("用戶要求修改計劃")

                # 處理計劃修改
                modifications = response.data.get("modifications", {})
                if modifications:
                    # 應用修改到計劃
                    self._apply_plan_modifications(modifications)

                # 返回計劃階段重新生成
                self.conversation_state.workflow_state = WorkflowState.PLANNING
            else:
                logger.info("用戶拒絕計劃，結束工作流")
                self.conversation_state.workflow_state = WorkflowState.ERROR
                self.conversation_state.error_message = "用戶拒絕了執行計劃"

        except Exception as e:
            logger.error(f"人工反饋處理失敗: {e}")
            # 發生錯誤時自動繼續執行
            self.conversation_state.workflow_state = WorkflowState.EXECUTION

    def _apply_plan_modifications(self, modifications: Dict[str, Any]):
        """應用計劃修改"""
        if not self.conversation_state.current_plan:
            return

        plan = self.conversation_state.current_plan

        # 添加新步驟
        if modifications.get("add_steps"):
            new_steps = modifications["add_steps"]
            for step_desc in new_steps:
                new_step = {
                    "step_id": f"added_step_{len(plan.get('steps', []))}",
                    "step_type": "research",
                    "description": step_desc,
                    "expected_output": "新增步驟的輸出",
                }
                plan.setdefault("steps", []).append(new_step)

        # 修改現有步驟
        if modifications.get("modify_steps"):
            step_modifications = modifications["modify_steps"]
            steps = plan.get("steps", [])

            for step_id, modification in step_modifications.items():
                for step in steps:
                    if step.get("step_id") == step_id:
                        step["description"] = modification
                        break

        # 移除步驟
        if modifications.get("remove_steps"):
            remove_step_ids = modifications["remove_steps"]
            steps = plan.get("steps", [])
            plan["steps"] = [step for step in steps if step.get("step_id") not in remove_step_ids]

        logger.info("計劃修改已應用")

    async def cleanup(self):
        """清理資源"""
        try:
            if self.runtime:
                await self.runtime.stop()
                logger.info("AutoGen 運行時環境已停止")
        except Exception as e:
            logger.error(f"清理資源失敗: {e}")

    def get_conversation_summary(self) -> Dict[str, Any]:
        """獲取對話摘要"""
        return {
            "state": self.conversation_state.workflow_state.value,
            "user_input": self.conversation_state.user_input,
            "research_topic": self.conversation_state.research_topic,
            "plan_iterations": self.conversation_state.plan_iterations,
            "execution_step": self.conversation_state.execution_step,
            "total_steps": len(self.conversation_state.current_plan.get("steps", []))
            if self.conversation_state.current_plan
            else 0,
            "has_error": bool(self.conversation_state.error_message),
            "error_message": self.conversation_state.error_message,
            "created_at": self.conversation_state.created_at.isoformat(),
            "updated_at": self.conversation_state.updated_at.isoformat(),
            "execution_history_count": len(self.conversation_state.execution_history),
        }


# 便利函數
async def create_conversation_manager(
    model_client: ChatCompletionClient, config: ConversationConfig = None
) -> AutoGenConversationManager:
    """創建對話管理器"""
    manager = AutoGenConversationManager(model_client, config)
    await manager.initialize_runtime()
    return manager


async def run_research_workflow(
    user_input: str, model_client: ChatCompletionClient, config: ConversationConfig = None
) -> ConversationState:
    """運行研究工作流"""
    manager = await create_conversation_manager(model_client, config)
    try:
        result = await manager.start_conversation(user_input)
        return result
    finally:
        await manager.cleanup()
