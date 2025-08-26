# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
計劃者智能體 - AutoGen 框架版本

負責分析研究需求並制定詳細的執行計劃。
基於 planner_node 實現，使用 AutoGen 的 BaseChatAgent。
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

# AutoGen 核心組件
from autogen_core import CancellationToken
from autogen_core.models import (
    ChatCompletionClient,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    LLMMessage,
)

# AutoGen AgentChat 基礎類
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage

# 嘗試導入線程管理功能
try:
    from src.logging import (
        setup_thread_logging,
        set_thread_context,
        get_current_thread_id,
        get_current_thread_logger,
    )

    HAS_THREAD_LOGGING = True
except ImportError:
    HAS_THREAD_LOGGING = False

# 嘗試導入提示模板功能
try:
    from src.prompts.template import apply_prompt_template
    from src.config.configuration import Configuration

    HAS_PROMPT_TEMPLATES = True
except ImportError:
    HAS_PROMPT_TEMPLATES = False

logger = logging.getLogger(__name__)


@dataclass
class ResearchStep:
    """研究步驟"""

    need_search: bool
    title: str
    description: str
    step_type: str  # "research" or "processing"
    execution_res: Optional[str] = None


@dataclass
class ResearchPlan:
    """研究計劃"""

    locale: str
    has_enough_context: bool
    thought: str
    title: str
    steps: List[ResearchStep]


class PlannerAgent(BaseChatAgent):
    """
    計劃者智能體 - AutoGen 框架版本

    基於 planner_node 實現，角色職責：
    1. 分析研究需求的深度和廣度
    2. 評估是否有足夠的上下文資訊
    3. 制定詳細的執行計劃
    4. 分解任務為具體的研究和處理步驟
    5. 決定每個步驟是否需要網路搜尋
    """

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        description: str = "計劃者智能體 - 分析研究需求並制定執行計劃",
        system_messages: Optional[List[SystemMessage]] = None,
    ):
        """
        初始化計劃者智能體

        Args:
            name: 智能體名稱
            model_client: ChatCompletionClient 實例
            description: 智能體描述
            system_messages: 系統消息列表
        """
        super().__init__(name=name, description=description)

        self._model_client = model_client
        self._system_messages = system_messages or []
        self._chat_history: List[LLMMessage] = []

        # 線程管理
        self._current_thread_id: Optional[str] = None
        self._thread_logger = None

        # 狀態管理
        self._state: Dict[str, Any] = {}
        self._configuration: Optional[Any] = None

        # 兼容屬性
        self.role = "planner"
        self.max_step_num = 3
        self.locale = "zh-TW"

        logger.info(f"PlannerAgent 初始化完成: {name}")

    # 提示模板（基於原有的 planner.md）
    DEFAULT_SYSTEM_MESSAGE = """你是一位專業的深度研究員。研究和規劃使用專業智能體團隊收集全面資料的資訊收集任務。

# 詳細說明

你的任務是協調研究團隊為給定需求收集全面資訊。最終目標是產生一份詳盡的詳細報告，因此收集多面向的豐富資訊是關鍵。資訊不足或有限將導致最終報告不夠完善。

作為深度研究員，你可以將主要主題分解為子主題，並在適用時擴展用戶初始問題的深度廣度。

## 資訊數量和品質標準

成功的研究計劃必須滿足這些標準：
- 涵蓋主題的所有關鍵面向
- 從多個角度收集資訊（技術、商業、學術、社會等）
- 尋找最新和權威的資訊來源
- 包含量化數據和定性分析
- 確保資訊來源的多樣性和可信度

**回應格式** 你必須以JSON格式回應，包含以下字段:

```json
{
  "locale": "使用者的語言環境（如：zh-TW、en-US）",
  "has_enough_context": false, // 除非已有充分資訊，否則總是false
  "thought": "對研究需求的深入分析和計劃思路",
  "title": "研究計劃的標題",
  "steps": [
    {
      "need_search": true, // 是否需要網路搜尋
      "title": "步驟標題",
      "description": "詳細描述要收集的資訊類型和搜尋策略",
      "step_type": "research" // 或 "processing"
    }
  ]
}
```

## 指導原則

- 創建一個在3個步驟內涵蓋最關鍵面向的全面資料收集計劃
- 優先考慮廣度（涵蓋重要面向）和深度（每個面向的詳細資訊）
- 永不滿足於最低限度的資訊 - 目標是全面、詳細的最終報告
- 有限或不足的資訊將導致不完善的最終報告
- 根據步驟性質仔細評估每個步驟的網路搜尋需求
- 除非滿足最嚴格的足夠上下文標準，否則預設收集更多資訊"""

    def _setup_thread_context(self, thread_id: str):
        """設置線程上下文和日誌"""
        self._current_thread_id = thread_id

        if HAS_THREAD_LOGGING:
            try:
                self._thread_logger = setup_thread_logging(thread_id)
                set_thread_context(thread_id)

                if self._thread_logger:
                    self._thread_logger.info("PlannerAgent talking.")
                else:
                    logger.info("PlannerAgent talking.")
            except Exception as e:
                logger.warning(f"線程日誌設置失敗，使用標準 logger: {e}")
                self._thread_logger = logger
                logger.info("PlannerAgent talking.")
        else:
            self._thread_logger = logger
            logger.info("PlannerAgent talking.")

    def _get_thread_id_from_context(
        self, cancellation_token: Optional[CancellationToken] = None
    ) -> str:
        """從上下文獲取線程 ID"""
        if self._current_thread_id:
            return self._current_thread_id

        if HAS_THREAD_LOGGING:
            try:
                current_thread_id = get_current_thread_id()
                if current_thread_id:
                    return current_thread_id
            except Exception:
                pass

        thread_id = f"planner_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        logger.debug(f"生成新線程 ID: {thread_id}")
        return thread_id

    def _apply_dynamic_system_message(self, state: Dict[str, Any]) -> List[SystemMessage]:
        """應用動態提示模板"""
        if HAS_PROMPT_TEMPLATES:
            try:
                template_state = {
                    "messages": state.get("messages", []),
                    "locale": state.get("locale", "zh-TW"),
                    "research_topic": state.get("research_topic", ""),
                    **state,
                }

                if self._thread_logger:
                    self._thread_logger.debug(f"模板狀態: {template_state}")

                if self._configuration and HAS_PROMPT_TEMPLATES:
                    if isinstance(self._configuration, dict):
                        try:
                            from src.config.configuration import Configuration

                            config_obj = Configuration.from_runnable_config(
                                {"configurable": self._configuration}
                            )
                            template_messages = apply_prompt_template(
                                "planner", template_state, config_obj
                            )
                        except Exception as config_error:
                            if self._thread_logger:
                                self._thread_logger.warning(
                                    f"配置轉換失敗，使用無配置版本: {config_error}"
                                )
                            template_messages = apply_prompt_template("planner", template_state)
                    else:
                        template_messages = apply_prompt_template(
                            "planner", template_state, self._configuration
                        )
                else:
                    template_messages = apply_prompt_template("planner", template_state)

                system_messages = []
                for msg in template_messages:
                    if isinstance(msg, dict) and msg.get("role") == "system":
                        system_messages.append(SystemMessage(content=msg["content"]))

                if system_messages:
                    if self._thread_logger:
                        self._thread_logger.info("成功應用動態提示模板")
                    return system_messages

            except Exception as e:
                error_details = f"動態提示模板應用失敗: {type(e).__name__}: {str(e)}"
                if self._thread_logger:
                    self._thread_logger.warning(error_details)
                else:
                    logger.warning(error_details)

        # 降級到預設系統消息
        if self._thread_logger:
            self._thread_logger.info("使用預設系統提示")
        else:
            logger.info("使用預設系統提示")

        return [SystemMessage(content=self.DEFAULT_SYSTEM_MESSAGE)]

    async def on_messages(
        self, messages: List[TextMessage], cancellation_token: Optional[CancellationToken] = None
    ) -> TextMessage:
        """
        處理輸入消息的主要方法（AutoGen 標準接口）
        """
        try:
            if not messages:
                return TextMessage(content="沒有收到消息", source=self.name)

            latest_message = messages[-1]
            user_input = (
                latest_message.content
                if hasattr(latest_message, "content")
                else str(latest_message)
            )

            # 設置線程上下文
            thread_id = self._get_thread_id_from_context(cancellation_token)
            self._setup_thread_context(thread_id)

            if self._thread_logger:
                self._thread_logger.info(f"PlannerAgent 開始處理計劃請求: {user_input}")

            # 調用計劃生成邏輯
            plan_result = await self._generate_plan_with_llm(user_input, cancellation_token)

            return TextMessage(content=plan_result, source=self.name)

        except Exception as e:
            error_msg = f"處理計劃請求失敗: {str(e)}"
            logger.error(error_msg)

            if self._thread_logger:
                self._thread_logger.error(error_msg)

            return TextMessage(content=f"抱歉，生成計劃時出現錯誤：{str(e)}", source=self.name)

    async def _generate_plan_with_llm(
        self, user_input: str, cancellation_token: Optional[CancellationToken] = None
    ) -> str:
        """使用 LLM 生成計劃"""
        try:
            # 更新狀態
            self._state.update(
                {
                    "messages": [{"role": "user", "content": user_input}],
                    "locale": self.locale,
                    "research_topic": user_input.strip(),
                }
            )

            # 準備動態系統消息
            system_messages = self._apply_dynamic_system_message(self._state)

            # 準備消息列表
            messages = (
                system_messages
                + self._chat_history
                + [UserMessage(content=user_input, source="user")]
            )

            if self._thread_logger:
                self._thread_logger.info("調用 LLM API 進行計劃生成...")

            # 調用 LLM
            response = await self._model_client.create(
                messages=messages,
                cancellation_token=cancellation_token,
            )

            response_content = response.content

            if self._thread_logger:
                self._thread_logger.info("LLM API 調用成功")
                self._thread_logger.debug(f"LLM 回應: {response_content}")

            # 解析並驗證計劃
            plan_json = self._validate_and_format_plan(response_content)

            return plan_json

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.error(f"LLM API 調用失敗: {e}")

            # 降級到模擬計劃
            return await self._generate_fallback_plan(user_input)

    def _validate_and_format_plan(self, response_content: str) -> str:
        """驗證和格式化計劃"""
        try:
            # 嘗試解析 JSON
            if isinstance(response_content, str):
                plan_data = json.loads(response_content)
            else:
                plan_data = response_content

            # 驗證必要字段
            required_fields = ["locale", "has_enough_context", "thought", "title", "steps"]
            for field in required_fields:
                if field not in plan_data:
                    raise ValueError(f"計劃缺少必要字段: {field}")

            # 驗證步驟
            steps = plan_data.get("steps", [])
            for i, step in enumerate(steps):
                step_required_fields = ["need_search", "title", "description", "step_type"]
                for field in step_required_fields:
                    if field not in step:
                        raise ValueError(f"步驟 {i} 缺少必要字段: {field}")

            if self._thread_logger:
                self._thread_logger.info("計劃驗證成功")

            return json.dumps(plan_data, ensure_ascii=False, indent=2)

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.warning(f"計劃驗證失敗: {e}")

            # 返回降級計劃
            return self._create_fallback_plan_json()

    async def _generate_fallback_plan(self, user_input: str) -> str:
        """生成降級計劃"""
        if self._thread_logger:
            self._thread_logger.info("使用降級計劃生成")

        steps = [
            {
                "need_search": True,
                "title": f"收集{user_input}的基礎資訊",
                "description": f"搜尋並收集關於{user_input}的基本定義、發展歷史、主要特點和當前狀況",
                "step_type": "research",
            },
            {
                "need_search": True,
                "title": f"深入研究{user_input}的應用和趨勢",
                "description": f"收集{user_input}的實際應用案例、市場趨勢和未來發展方向",
                "step_type": "research",
            },
            {
                "need_search": True,
                "title": f"收集{user_input}的專家觀點和分析",
                "description": f"搜尋專家評論、學術研究和行業分析報告",
                "step_type": "research",
            },
        ]

        plan = {
            "locale": self.locale,
            "has_enough_context": False,
            "thought": f"用戶想要了解{user_input}的相關資訊。這需要全面的研究來收集充足的資料。",
            "title": f"{user_input}深度研究報告",
            "steps": steps[: self.max_step_num],
        }

        return json.dumps(plan, ensure_ascii=False, indent=2)

    def _create_fallback_plan_json(self) -> str:
        """創建降級計劃 JSON"""
        plan = {
            "locale": self.locale,
            "has_enough_context": False,
            "thought": "計劃解析失敗，使用預設計劃",
            "title": "研究計劃",
            "steps": [
                {
                    "need_search": True,
                    "title": "基礎資訊收集",
                    "description": "收集基本資訊",
                    "step_type": "research",
                }
            ],
        }

        return json.dumps(plan, ensure_ascii=False, indent=2)

    def set_parameters(self, max_step_num: int = 3, locale: str = "zh-TW"):
        """設定計劃參數"""
        self.max_step_num = max_step_num
        self.locale = locale
        if self._thread_logger:
            self._thread_logger.info(f"計劃參數更新: max_step_num={max_step_num}, locale={locale}")
        else:
            logger.info(f"計劃參數更新: max_step_num={max_step_num}, locale={locale}")

    def set_configuration(self, configuration: Any):
        """設置配置對象"""
        self._configuration = configuration

        if self._thread_logger:
            self._thread_logger.info(f"配置已更新: {type(configuration).__name__}")
        else:
            logger.info(f"配置已更新: {type(configuration).__name__}")

    def get_role_info(self) -> Dict[str, Any]:
        """取得角色資訊（兼容 BaseResearchAgent 接口）"""
        return {
            "name": self.name,
            "description": self.description,
            "role": "planner",
            "tools": [],
            "config": None,
        }

    async def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        處理用戶輸入（兼容 BaseResearchAgent 接口）

        Args:
            user_input: 用戶輸入的內容

        Returns:
            Dict[str, Any]: 包含回應的字典
        """
        try:
            # 設置線程上下文
            thread_id = self._get_thread_id_from_context()
            self._setup_thread_context(thread_id)

            # 生成計劃
            plan_result = await self._generate_plan_with_llm(user_input)

            return {
                "response": plan_result,
                "locale": self.locale,
                "status": "success",
            }

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.error(f"處理用戶輸入失敗: {e}")
            else:
                logger.error(f"處理用戶輸入失敗: {e}")

            return {
                "response": f"抱歉，生成計劃時發生錯誤：{str(e)}",
                "locale": self.locale,
                "status": "error",
            }

    # 實現 BaseChatAgent 的抽象方法
    async def on_reset(self) -> None:
        """處理重置事件"""
        self._chat_history.clear()
        self._state.clear()
        self._current_thread_id = None
        self._thread_logger = None

    @property
    def produced_message_types(self) -> List[type]:
        """返回此智能體產生的消息類型"""
        return [TextMessage]

    # 兼容方法 - 保留舊接口
    async def create_research_plan(
        self,
        research_topic: str,
        locale: str = "zh-TW",
        background_context: str = None,
        max_step_num: int = 3,
    ) -> ResearchPlan:
        """
        創建研究計劃（兼容舊接口）

        Args:
            research_topic: 研究主題
            locale: 語言設定
            background_context: 背景上下文
            max_step_num: 最大步驟數

        Returns:
            ResearchPlan: 研究計劃對象
        """
        try:
            # 設置參數
            self.set_parameters(max_step_num, locale)

            # 建構計劃輸入
            plan_input = f"# 研究主題\n{research_topic}\n"
            if background_context:
                plan_input += f"\n# 背景資訊\n{background_context}\n"

            # 生成計劃
            plan_json = await self._generate_plan_with_llm(plan_input)

            # 解析計劃
            plan_data = json.loads(plan_json)

            steps = []
            for step_data in plan_data.get("steps", []):
                steps.append(
                    ResearchStep(
                        need_search=step_data.get("need_search", True),
                        title=step_data.get("title", ""),
                        description=step_data.get("description", ""),
                        step_type=step_data.get("step_type", "research"),
                    )
                )

            return ResearchPlan(
                locale=plan_data.get("locale", locale),
                has_enough_context=plan_data.get("has_enough_context", False),
                thought=plan_data.get("thought", ""),
                title=plan_data.get("title", ""),
                steps=steps,
            )

        except Exception as e:
            logger.error(f"創建研究計劃失敗: {e}")
            # 返回降級計劃
            return self._create_fallback_research_plan(research_topic, locale, max_step_num)

    def _create_fallback_research_plan(
        self, research_topic: str, locale: str, max_step_num: int
    ) -> ResearchPlan:
        """創建降級研究計劃"""
        steps = [
            ResearchStep(
                need_search=True,
                title=f"收集{research_topic}的基礎資訊",
                description=f"搜尋並收集關於{research_topic}的基本定義、發展歷史、主要特點和當前狀況",
                step_type="research",
            ),
            ResearchStep(
                need_search=True,
                title=f"深入研究{research_topic}的應用和趨勢",
                description=f"收集{research_topic}的實際應用案例、市場趨勢和未來發展方向",
                step_type="research",
            ),
            ResearchStep(
                need_search=True,
                title=f"收集{research_topic}的專家觀點和分析",
                description=f"搜尋專家評論、學術研究和行業分析報告",
                step_type="research",
            ),
        ]

        return ResearchPlan(
            locale=locale,
            has_enough_context=False,
            thought=f"用戶想要了解{research_topic}的相關資訊。這需要全面的研究來收集充足的資料。",
            title=f"{research_topic}深度研究報告",
            steps=steps[:max_step_num],
        )
