# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 智能體選擇器

提供智能體選擇邏輯，用於決定 SelectorGroupChat 中下一個應該發言的智能體。
重構自原有的 selector_func，提供更清晰的結構和更好的可維護性。
"""

from typing import Sequence, Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass

from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage

from src.deerflow_logging import get_logger, get_thread_logger
from ..agents.message_framework import (
    parse_workflow_message,
    MessageType,
    StepType,
    extract_workflow_info,
)


# 延遲初始化 logger，避免在模組導入時就調用 get_thread_logger
class LazyLogger:
    def __getattr__(self, name):
        try:
            return getattr(get_thread_logger(), name)
        except RuntimeError as e:
            # 如果 thread context 未設定，使用 get_logger 作為備用
            return getattr(get_logger(__name__), name)


logger = LazyLogger()


class AgentName(str, Enum):
    """智能體名稱枚舉"""

    COORDINATOR = "CoordinatorAgentV3"
    PLANNER = "PlannerAgentV3"
    RESEARCHER = "ResearcherAgentV3"
    CODER = "CoderAgentV3"
    REPORTER = "ReporterAgentV3"
    RESEARCH_TEAM = "ResearchTeamCoordinator"  # 新增研究團隊協調者（虛擬角色）

    USER = "user"
    BACKGROUND_INVESTIGATOR = "BackgroundInvestigatorAgentV3"
    HUMAN_FEEDBACKER = "HumanFeedbackerAgentV3"


class WorkflowPhase(str, Enum):
    """工作流程階段枚舉"""

    INITIALIZATION = "initialization"
    COORDINATION = "coordination"
    BACKGROUND_INVESTIGATION = "background_investigation"
    PLANNING = "planning"
    HUMAN_FEEDBACK = "human_feedback"
    RESEARCH_TEAM_COORDINATION = "research_team_coordination"  # 新增研究團隊協調階段
    EXECUTION = "execution"
    REPORTING = "reporting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SelectionContext:
    """選擇上下文"""

    last_speaker: str
    last_message_content: str
    workflow_phase: WorkflowPhase
    parsed_message: Optional[Any] = None
    workflow_info: Dict[str, Any] = None
    # 添加流程參數
    max_plan_iterations: int = 1
    max_step_num: int = 3
    max_search_results: int = 3
    auto_accepted_plan: bool = False
    enable_background_investigation: bool = False
    current_plan_iterations: int = 0

    def __post_init__(self):
        if self.workflow_info is None:
            self.workflow_info = extract_workflow_info(self.last_message_content)


class AgentSelector:
    """智能體選擇器"""

    def __init__(
        self,
        max_turns: int = 50,
        enable_debug: bool = True,
        max_plan_iterations: int = 1,
        max_step_num: int = 3,
        max_search_results: int = 3,
        auto_accepted_plan: bool = False,
        enable_background_investigation: bool = False,
    ):
        """
        初始化選擇器

        Args:
            max_turns: 最大輪次數
            enable_debug: 是否啟用除錯模式
            max_plan_iterations: 最大計劃迭代次數
            max_step_num: 計劃中的最大步驟數
            max_search_results: 最大搜尋結果數
            auto_accepted_plan: 是否自動接受計劃
            enable_background_investigation: 是否啟用背景調查
        """
        self.max_turns = max_turns
        self.enable_debug = enable_debug
        self.turn_count = 0
        self.workflow_state = {}

        # 添加流程控制參數
        self.max_plan_iterations = max_plan_iterations
        self.max_step_num = max_step_num
        self.max_search_results = max_search_results
        self.auto_accepted_plan = auto_accepted_plan
        self.enable_background_investigation = enable_background_investigation
        self.current_plan_iterations = 0

    def select_next_agent(
        self, messages: Sequence[BaseAgentEvent | BaseChatMessage]
    ) -> Optional[str]:
        """
        選擇下一個智能體

        Args:
            messages: 對話歷史訊息

        Returns:
            str | None: 下一個智能體的名稱，或 None 讓模型自動選擇
        """
        self.turn_count += 1

        if self.enable_debug:
            logger.info(f"=== Agent Selection Round {self.turn_count} ===")

        # 檢查是否超過最大輪次
        if self.turn_count > self.max_turns:
            logger.warning(f"達到最大輪次限制 ({self.max_turns})，結束對話")
            return None

        # 處理空訊息列表
        if not messages:
            return self._handle_initial_state()

        # 建立選擇上下文
        context = self._build_selection_context(messages)

        if self.enable_debug:
            logger.info(
                f"選擇上下文: 上一個發言者={context.last_speaker}, 階段={context.workflow_phase}"
            )

        # 根據上下文選擇下一個智能體
        next_agent = self._select_based_on_context(context)

        if self.enable_debug:
            logger.info(f"選擇結果: {next_agent}")

        return next_agent

    def _handle_initial_state(self) -> str:
        """處理初始狀態"""
        logger.info("0. Selector: 初始狀態，啟動協調者")
        return AgentName.COORDINATOR

    def _build_selection_context(
        self, messages: Sequence[BaseAgentEvent | BaseChatMessage]
    ) -> SelectionContext:
        """建立選擇上下文"""
        last_message = messages[-1]
        last_speaker = last_message.source
        last_content = last_message.content

        # 解析工作流程訊息
        parsed_message = parse_workflow_message(last_content)

        # 判斷工作流程階段
        workflow_phase = self._determine_workflow_phase(last_speaker, last_content, parsed_message)

        return SelectionContext(
            last_speaker=last_speaker,
            last_message_content=last_content,
            workflow_phase=workflow_phase,
            parsed_message=parsed_message,
            max_plan_iterations=self.max_plan_iterations,
            max_step_num=self.max_step_num,
            max_search_results=self.max_search_results,
            auto_accepted_plan=self.auto_accepted_plan,
            enable_background_investigation=self.enable_background_investigation,
            current_plan_iterations=self.current_plan_iterations,
        )

    def _determine_workflow_phase(
        self, last_speaker: str, content: str, parsed_message: Optional[Any]
    ) -> WorkflowPhase:
        """判斷工作流程階段"""

        # 檢查是否為錯誤狀態
        if "error" in content.lower() or "錯誤" in content:
            return WorkflowPhase.ERROR

        # 檢查是否已完成
        if (
            "WORKFLOW_COMPLETE" in content
            or "TERMINATE" in content
            or "完成" in content
            and last_speaker == AgentName.REPORTER
        ):
            return WorkflowPhase.COMPLETED

        # 根據發言者判斷階段
        if last_speaker == AgentName.USER:
            return WorkflowPhase.INITIALIZATION
        elif last_speaker == AgentName.COORDINATOR:
            return WorkflowPhase.COORDINATION
        elif last_speaker == AgentName.BACKGROUND_INVESTIGATOR:
            return WorkflowPhase.BACKGROUND_INVESTIGATION
        elif last_speaker == AgentName.PLANNER:
            return WorkflowPhase.PLANNING
        elif last_speaker == AgentName.RESEARCH_TEAM:
            return WorkflowPhase.RESEARCH_TEAM_COORDINATION
        elif last_speaker in [AgentName.RESEARCHER, AgentName.CODER]:
            return WorkflowPhase.EXECUTION
        elif last_speaker == AgentName.REPORTER:
            return WorkflowPhase.REPORTING
        else:
            return WorkflowPhase.INITIALIZATION

    def _select_based_on_context(self, context: SelectionContext) -> Optional[str]:
        """根據上下文選擇智能體"""

        # 選擇策略映射（基於 mermaid 流程圖）
        selection_strategies = {
            WorkflowPhase.INITIALIZATION: self._handle_initialization_phase,
            WorkflowPhase.COORDINATION: self._handle_coordination_phase,
            WorkflowPhase.BACKGROUND_INVESTIGATION: self._handle_background_investigation_phase,
            WorkflowPhase.PLANNING: self._handle_planning_phase,
            WorkflowPhase.HUMAN_FEEDBACK: self._handle_human_feedback_phase,
            WorkflowPhase.RESEARCH_TEAM_COORDINATION: self._handle_research_team_coordination_phase,
            WorkflowPhase.EXECUTION: self._handle_execution_phase,
            WorkflowPhase.REPORTING: self._handle_reporting_phase,
            WorkflowPhase.COMPLETED: self._handle_completed_phase,
            WorkflowPhase.ERROR: self._handle_error_phase,
        }

        strategy = selection_strategies.get(context.workflow_phase)
        if strategy:
            return strategy(context)
        else:
            logger.warning(f"未知的工作流程階段: {context.workflow_phase}")
            return None

    def _handle_initialization_phase(self, context: SelectionContext) -> str:
        """處理初始化階段"""
        logger.info("1. Selector: 使用者發言，轉到協調者")
        return AgentName.COORDINATOR

    def _handle_coordination_phase(self, context: SelectionContext) -> str:
        """處理協調階段"""
        # 根據 mermaid 流程圖：協調者 -> 檢查是否啟用背景調查
        if context.enable_background_investigation:
            logger.info("2. Selector: 協調者完成分析，啟用背景調查，轉到背景調查者")
            return AgentName.BACKGROUND_INVESTIGATOR
        else:
            logger.info("2. Selector: 協調者完成分析，跳過背景調查，直接轉到規劃者")
            return AgentName.PLANNER

    def _handle_background_investigation_phase(self, context: SelectionContext) -> str:
        """處理背景調查階段"""
        # 根據 mermaid 流程圖：背景調查完成 -> 規劃者
        logger.info("2.5. Selector: 背景調查完成，轉到規劃者")
        return AgentName.PLANNER

    def _handle_planning_phase(self, context: SelectionContext) -> Optional[str]:
        """處理規劃階段"""

        # 首先檢查計劃迭代次數是否已達上限
        if context.current_plan_iterations >= context.max_plan_iterations:
            logger.info(
                f"3. Selector: 計劃迭代次數已達上限 ({context.max_plan_iterations})，轉到報告者"
            )
            return AgentName.REPORTER

        # 解析規劃訊息
        if not context.parsed_message:
            logger.info("3. Selector: 無法解析規劃訊息，讓模型自動選擇")
            return None

        if context.parsed_message.message_type != MessageType.PLAN:
            logger.info("3. Selector: 非計劃訊息，讓模型自動選擇")
            return None

        plan_data = context.parsed_message.data
        logger.info(f"3. Selector: parsed_message.data = {plan_data}")
        logger.info(f"3. Selector: parsed_message 類型 = {type(context.parsed_message)}")
        logger.info(f"3. Selector: parsed_message 內容 = {context.parsed_message}")

        # 檢查計劃是否為空
        if not plan_data.get("steps"):
            logger.info("3. Selector: 計劃為空，保持在規劃者")
            return AgentName.PLANNER

        # 檢查步驟數量是否超過限制
        total_steps = plan_data.get("steps", [])
        if not self._check_step_limits(total_steps, context):
            logger.info("3. Selector: 步驟數量超過限制，要求重新規劃")
            return AgentName.PLANNER

        # 檢查計劃是否有足夠上下文（has_enough_context）
        if plan_data.get("has_enough_context", False):
            logger.info("3. Selector: 計劃有足夠上下文，直接轉到報告者")
            return AgentName.REPORTER

        # 檢查是否所有步驟都已完成
        total_steps = plan_data.get("steps", [])

        # 優先使用 completed_steps 列表（測試案例格式）
        completed_steps_from_list = plan_data.get("completed_steps", [])

        # 如果 completed_steps 列表不為空，使用它
        if completed_steps_from_list:
            completed_steps = set(completed_steps_from_list)
            logger.info(f"3. Selector: 使用 completed_steps 列表: {completed_steps_from_list}")
        else:
            # 否則從步驟狀態中提取已完成的步驟（實際 PlanMessage 格式）
            completed_steps_list = []
            for step in total_steps:
                step_id = step.get("id", step.get("step_type", ""))
                step_status = step.get("status")
                if (
                    step_status
                    and hasattr(step_status, "value")
                    and step_status.value == "completed"
                ):
                    completed_steps_list.append(step_id)
            completed_steps = set(completed_steps_list)
            logger.info(f"3. Selector: 從步驟狀態提取已完成步驟: {completed_steps_list}")

        logger.info(f"3. Selector: 總步驟: {[s.get('id', 'unknown') for s in total_steps]}")
        logger.info(f"3. Selector: 已完成步驟集合: {completed_steps}")

        # 注意：這裡不再處理迭代計數邏輯，迭代計數將在研究團隊協調階段處理
        # 這確保了與 LangGraph 流程的語義一致性：所有步驟完成 -> 迭代次數+1 -> 重新規劃

        # 如果自動接受計劃，進入研究團隊協調階段（與 LangGraph 流程一致）
        if context.auto_accepted_plan:
            logger.info("3. Selector: 自動接受計劃，轉到研究團隊協調階段")
            return self._simulate_research_team_coordination(total_steps, completed_steps)
        else:
            # 需要人工回饋
            logger.info("3. Selector: 需要人工回饋，轉到人工回饋階段")
            return AgentName.HUMAN_FEEDBACKER

    def _handle_human_feedback_phase(self, context: SelectionContext) -> str:
        """處理人工回饋階段"""
        # 根據 mermaid 流程圖：人工回饋 -> 檢查計劃是否被接受
        content = context.last_message_content

        if "[EDIT_PLAN]" in content:
            logger.info("3.5. Selector: 計劃需要修改，轉回規劃者")
            return AgentName.PLANNER
        elif "[ACCEPTED]" in content or context.auto_accepted_plan:
            logger.info("3.5. Selector: 計劃被接受，轉到研究團隊協調階段")
            # 這裡需要找到下一個執行步驟
            if context.parsed_message and context.parsed_message.message_type == MessageType.PLAN:
                plan_data = context.parsed_message.data
                completed_steps = set(plan_data.get("completed_steps", []))
                total_steps = plan_data.get("steps", [])
                return self._simulate_research_team_coordination(total_steps, completed_steps)

            # 如果找不到步驟，轉到報告者
            logger.info("3.5. Selector: 找不到執行步驟，轉到報告者")
            return AgentName.REPORTER
        else:
            logger.info("3.5. Selector: 未知的回饋類型，讓模型自動選擇")
            return None

    def _handle_execution_phase(self, context: SelectionContext) -> str:
        """處理執行階段"""
        if context.last_speaker == AgentName.RESEARCHER:
            if "more_research_needed" in context.last_message_content:
                logger.info("4. Selector: 需要更多研究，保持在研究者")
                return AgentName.RESEARCHER
            else:
                logger.info("4. Selector: 研究步驟完成，轉回研究團隊協調檢查下一步")
                # 標記步驟完成並回到研究團隊協調
                return self._return_to_research_team_coordination(context)

        elif context.last_speaker == AgentName.CODER:
            if "more_coding_needed" in context.last_message_content:
                logger.info("4. Selector: 需要更多程式碼工作，保持在程式設計師")
                return AgentName.CODER
            else:
                logger.info("4. Selector: 程式碼步驟完成，轉回研究團隊協調檢查下一步")
                # 標記步驟完成並回到研究團隊協調
                return self._return_to_research_team_coordination(context)

        # 預設返回研究團隊協調
        logger.info("4. Selector: 執行階段完成，轉回研究團隊協調")
        return self._return_to_research_team_coordination(context)

    def _handle_reporting_phase(self, context: SelectionContext) -> Optional[str]:
        """處理報告階段"""
        # 檢查是否包含終止標記
        has_termination = (
            "WORKFLOW_COMPLETE" in context.last_message_content
            or "TERMINATE" in context.last_message_content
        )

        if has_termination:
            logger.info("5. Selector: 報告者完成工作流程，包含終止標記，準備結束")
            return None  # 讓 AutoGen 處理結束邏輯
        else:
            logger.info("5. Selector: 報告者發言，但未包含終止標記，繼續執行")
            return None  # 讓模型自動選擇

    def _handle_completed_phase(self, context: SelectionContext) -> Optional[str]:
        """處理完成階段"""
        logger.info("6. Selector: 工作流程已完成")
        return None

    def _handle_error_phase(self, context: SelectionContext) -> Optional[str]:
        """處理錯誤階段"""
        logger.error("7. Selector: 工作流程遇到錯誤，讓模型自動選擇")
        return None

    def _find_next_step(
        self, steps: List[Dict[str, Any]], completed_steps: set
    ) -> Optional[Dict[str, Any]]:
        """找到下一個未完成的步驟"""
        logger.info(f"_find_next_step: 檢查 {len(steps)} 個步驟，已完成: {completed_steps}")
        for step in steps:
            step_id = step.get("id", step.get("step_type", ""))
            logger.info(
                f"_find_next_step: 檢查步驟 {step_id}，是否已完成: {step_id in completed_steps}"
            )
            if step_id not in completed_steps:
                logger.info(f"_find_next_step: 找到未完成步驟: {step_id}")
                return step
        logger.info("_find_next_step: 所有步驟都已完成")
        return None

    def _select_agent_for_step(self, step: Dict[str, Any]) -> str:
        """為步驟選擇合適的智能體"""
        step_type = step.get("step_type", "").lower()
        step_id = step.get("id", "unknown")

        if "research" in step_type or "search" in step_type:
            logger.info(f"4. Selector: 需要執行研究步驟 {step_id}，轉到研究者")
            return AgentName.RESEARCHER
        elif "code" in step_type or "processing" in step_type:
            logger.info(f"4. Selector: 需要執行程式碼步驟 {step_id}，轉到程式設計師")
            return AgentName.CODER
        else:
            logger.info(f"4. Selector: 未知步驟類型 {step_type}，預設轉到研究者")
            return AgentName.RESEARCHER

    def _check_step_limits(
        self, total_steps: List[Dict[str, Any]], context: SelectionContext
    ) -> bool:
        """檢查步驟數量是否超過限制"""
        if len(total_steps) > context.max_step_num:
            logger.warning(f"計劃包含 {len(total_steps)} 個步驟，超過限制 {context.max_step_num}")
            return False
        return True

    def _update_step_completion(self, step_id: str, result: str):
        """更新步驟完成狀態"""
        if "completed_steps" not in self.workflow_state:
            self.workflow_state["completed_steps"] = set()

        self.workflow_state["completed_steps"].add(step_id)
        logger.info(f"步驟 {step_id} 已標記為完成")

    def _handle_research_team_coordination_phase(self, context: SelectionContext) -> str:
        """處理研究團隊協調階段（模擬 LangGraph 中的 Research Team 節點）"""
        logger.info("3.6. Selector: 研究團隊協調階段 - 檢查待執行步驟")

        # 嘗試從上下文中獲取計劃資訊
        if context.parsed_message and context.parsed_message.message_type == MessageType.PLAN:
            plan_data = context.parsed_message.data
            completed_steps = set(plan_data.get("completed_steps", []))
            total_steps = plan_data.get("steps", [])
        else:
            # 如果沒有解析的計劃，嘗試從工作流程資訊中獲取
            completed_steps = set(context.workflow_info.get("completed_steps", []))
            total_steps = context.workflow_info.get("steps", [])

        return self._coordinate_research_team(total_steps, completed_steps)

    def _simulate_research_team_coordination(
        self, total_steps: List[Dict[str, Any]], completed_steps: set
    ) -> str:
        """模擬研究團隊協調邏輯（對應 LangGraph 流程圖中的 Research Team 節點）"""
        logger.info("3.6. Selector: 模擬研究團隊協調 - 檢查步驟執行狀態")
        return self._coordinate_research_team(total_steps, completed_steps)

    def _coordinate_research_team(
        self, total_steps: List[Dict[str, Any]], completed_steps: set
    ) -> str:
        """協調研究團隊，決定下一個執行步驟或完成狀態"""
        logger.info(f"研究團隊協調: 總步驟數={len(total_steps)}, 已完成={len(completed_steps)}")

        # 檢查是否所有步驟都已完成
        if len(completed_steps) >= len(total_steps):
            logger.info("研究團隊協調: 所有步驟已完成，增加迭代次數並回到規劃者")
            # 這裡與 LangGraph 流程一致：所有步驟完成 -> 迭代次數+1 -> 回到 Planner
            self.current_plan_iterations += 1
            return AgentName.PLANNER

        # 尋找下一個未完成步驟
        next_step = self._find_next_step(total_steps, completed_steps)
        if next_step:
            logger.info(f"研究團隊協調: 找到下一個步驟 {next_step.get('id', 'unknown')}")
            return self._select_agent_for_step(next_step)
        else:
            logger.info("研究團隊協調: 找不到未完成步驟，轉到報告者")
            return AgentName.REPORTER

    def _return_to_research_team_coordination(self, context: SelectionContext) -> str:
        """從執行階段返回研究團隊協調階段"""
        logger.info("4.5. Selector: 步驟執行完成，返回研究團隊協調階段")

        # 這裡我們模擬研究團隊協調的邏輯
        # 由於我們沒有真實的 Research Team 智能體，我們直接執行協調邏輯
        if context.parsed_message and context.parsed_message.message_type == MessageType.PLAN:
            plan_data = context.parsed_message.data
            completed_steps = set(plan_data.get("completed_steps", []))
            total_steps = plan_data.get("steps", [])
            return self._coordinate_research_team(total_steps, completed_steps)
        else:
            # 如果無法獲取計劃資訊，回到規劃者重新評估
            logger.info("4.5. Selector: 無法獲取計劃資訊，回到規劃者重新評估")
            return AgentName.PLANNER

    def reset(self):
        """重設選擇器狀態"""
        self.turn_count = 0
        self.workflow_state.clear()
        self.current_plan_iterations = 0  # 重設迭代計數
        logger.info("智能體選擇器已重設")


class AdvancedAgentSelector(AgentSelector):
    """進階智能體選擇器

    提供更複雜的選擇邏輯，包括：
    - 智能體負載平衡
    - 步驟依賴關係檢查
    - 動態優先級調整
    """

    def __init__(self, max_turns: int = 50, enable_debug: bool = True, **kwargs):
        super().__init__(max_turns, enable_debug, **kwargs)
        self.agent_usage_count = {}
        self.step_dependencies = {}

    def select_next_agent(
        self, messages: Sequence[BaseAgentEvent | BaseChatMessage]
    ) -> Optional[str]:
        """選擇下一個智能體（進階版本）"""
        # 先執行基本選擇邏輯
        basic_selection = super().select_next_agent(messages)

        # 如果基本邏輯返回 None，不進行進一步處理
        if basic_selection is None:
            return None

        # 更新智能體使用統計
        self._update_agent_usage(basic_selection)

        # 檢查負載平衡（可選）
        balanced_selection = self._apply_load_balancing(basic_selection)

        return balanced_selection

    def _update_agent_usage(self, agent_name: str):
        """更新智能體使用統計"""
        self.agent_usage_count[agent_name] = self.agent_usage_count.get(agent_name, 0) + 1

    def _apply_load_balancing(self, selected_agent: str) -> str:
        """應用負載平衡邏輯"""
        # 簡單的負載平衡：如果某個智能體使用過多，可以考慮替代方案
        usage_count = self.agent_usage_count.get(selected_agent, 0)

        if usage_count > 10:  # 閾值可以調整
            logger.warning(f"智能體 {selected_agent} 使用次數過多 ({usage_count})，考慮負載平衡")
            # 這裡可以實現更複雜的負載平衡邏輯

        return selected_agent

    def get_usage_statistics(self) -> Dict[str, int]:
        """獲取智能體使用統計"""
        return self.agent_usage_count.copy()


def create_selector_function(config: dict, selector_type: str = "basic", **kwargs) -> callable:
    """
    創建選擇器函數的工廠函數

    Args:
        config: 配置字典
        selector_type: 選擇器類型 ("basic" 或 "advanced")
        **kwargs: 選擇器初始化參數

    Returns:
        callable: 選擇器函數
    """
    # 從配置中讀取 selector_config
    selector_config = config.get("selector_config", {})
    # 合併配置設定和參數（參數優先）
    kwargs = {**selector_config, **kwargs}

    if selector_type == "advanced":
        selector = AdvancedAgentSelector(**kwargs)
    else:
        selector = AgentSelector(**kwargs)

    def selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> Optional[str]:
        """選擇器函數包裝器"""
        try:
            return selector.select_next_agent(messages)
        except Exception as e:
            logger.error(f"選擇器函數執行錯誤: {e}")
            return None

    # 將選擇器實例附加到函數上，以便外部訪問
    selector_func.selector = selector

    return selector_func


# 為了向後兼容，提供原始的函數介面
def selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> Optional[str]:
    """
    預設的智能體選擇函數

    這是原始 selector_func 的重構版本，保持相同的介面。
    """
    # 使用基本選擇器
    selector = AgentSelector(enable_debug=True)
    return selector.select_next_agent(messages)
