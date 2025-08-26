# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
研究者智能體 - AutoGen 框架版本

負責執行網路搜尋、資訊收集和內容爬取任務。
基於 researcher_node 實現，使用 AutoGen 的 BaseChatAgent。
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Callable
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
class SearchResult:
    """搜尋結果"""

    title: str
    url: str
    content: str
    source: str
    timestamp: datetime


@dataclass
class ResearchFindings:
    """研究發現"""

    problem_statement: str
    findings: List[Dict[str, Any]]
    conclusion: str
    references: List[str]
    images: List[str] = None


class ResearcherAgent(BaseChatAgent):
    """
    研究者智能體 - AutoGen 框架版本

    基於 researcher_node 實現，角色職責：
    1. 進行網路搜尋和資訊收集
    2. 爬取特定 URL 的內容
    3. 使用本地知識庫搜尋
    4. 整合多來源資訊
    5. 生成結構化的研究報告
    6. 處理時間範圍約束
    """

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        description: str = "研究者智能體 - 執行網路搜尋和資訊收集任務",
        system_messages: Optional[List[SystemMessage]] = None,
        tools: List[Callable] = None,
    ):
        """
        初始化研究者智能體

        Args:
            name: 智能體名稱
            model_client: ChatCompletionClient 實例
            description: 智能體描述
            system_messages: 系統消息列表
            tools: 工具列表
        """
        super().__init__(name=name, description=description)

        self._model_client = model_client
        self._system_messages = system_messages or []
        self._chat_history: List[LLMMessage] = []
        self._tools = tools or []

        # 線程管理
        self._current_thread_id: Optional[str] = None
        self._thread_logger = None

        # 狀態管理
        self._state: Dict[str, Any] = {}
        self._configuration: Optional[Any] = None

        # 兼容屬性
        self.role = "researcher"
        self.locale = "zh-TW"
        self.max_results = 5

        logger.info(f"ResearcherAgent 初始化完成: {name}")

    # 提示模板（基於原有的 researcher.md）
    DEFAULT_SYSTEM_MESSAGE = """你是由監督智能體管理的 `researcher` 智能體。

你的職責是使用搜尋工具進行全面的研究，以收集詳細和相關的資訊。你的任務將包括使用網路搜尋工具和爬取工具來收集資料，然後將這些資訊整理成一致、詳細的回應。

## 核心職責

1. **網路搜尋**: 使用提供的網路搜尋工具來尋找相關資訊
2. **內容爬取**: 使用爬取工具來獲得特定網站或文件的詳細資訊
3. **本地搜尋**: 當可用時，使用本地搜尋工具查詢特定的資料庫或知識庫
4. **資訊整合**: 將來自多個來源的資訊整合成一致的回應
5. **引用管理**: 適當地引用所有來源，並確保資訊的可追溯性

## 搜尋策略

- 開始進行廣泛搜尋以了解主題概況
- 然後進行更具體的搜尋以獲得詳細資訊
- 使用多個搜尋詞來確保全面性
- 優先選擇權威和最新的來源
- 交叉驗證來自多個來源的資訊

## 輸出格式

確保你的回應：
- 結構化且易於閱讀
- 包含詳細的研究發現
- 在回應末尾包含所有引用的來源列表
- 使用適當的 Markdown 格式
- 當呈現比較資料、統計資料或特徵時，優先使用表格格式

記住，你的目標是提供全面、準確和有用的資訊，幫助使用者充分了解他們詢問的主題。"""

    def _setup_thread_context(self, thread_id: str):
        """設置線程上下文和日誌"""
        self._current_thread_id = thread_id

        if HAS_THREAD_LOGGING:
            try:
                self._thread_logger = setup_thread_logging(thread_id)
                set_thread_context(thread_id)

                if self._thread_logger:
                    self._thread_logger.info("ResearcherAgent talking.")
                else:
                    logger.info("ResearcherAgent talking.")
            except Exception as e:
                logger.warning(f"線程日誌設置失敗，使用標準 logger: {e}")
                self._thread_logger = logger
                logger.info("ResearcherAgent talking.")
        else:
            self._thread_logger = logger
            logger.info("ResearcherAgent talking.")

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

        thread_id = f"researcher_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
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
                                "researcher", template_state, config_obj
                            )
                        except Exception as config_error:
                            if self._thread_logger:
                                self._thread_logger.warning(
                                    f"配置轉換失敗，使用無配置版本: {config_error}"
                                )
                            template_messages = apply_prompt_template("researcher", template_state)
                    else:
                        template_messages = apply_prompt_template(
                            "researcher", template_state, self._configuration
                        )
                else:
                    template_messages = apply_prompt_template("researcher", template_state)

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
                self._thread_logger.info(f"ResearcherAgent 開始處理研究任務: {user_input}")

            # 調用研究邏輯
            research_result = await self._conduct_research_with_llm(user_input, cancellation_token)

            return TextMessage(content=research_result, source=self.name)

        except Exception as e:
            error_msg = f"處理研究任務失敗: {str(e)}"
            logger.error(error_msg)

            if self._thread_logger:
                self._thread_logger.error(error_msg)

            return TextMessage(content=f"抱歉，執行研究時出現錯誤：{str(e)}", source=self.name)

    async def _conduct_research_with_llm(
        self, user_input: str, cancellation_token: Optional[CancellationToken] = None
    ) -> str:
        """使用 LLM 進行研究"""
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
                self._thread_logger.info("調用 LLM API 進行研究...")

            # 調用 LLM，如果有工具則綁定工具
            if self._tools:
                response = await self._model_client.create(
                    messages=messages,
                    tools=self._tools,
                    cancellation_token=cancellation_token,
                )
            else:
                response = await self._model_client.create(
                    messages=messages,
                    cancellation_token=cancellation_token,
                )

            response_content = response.content

            if self._thread_logger:
                self._thread_logger.info("LLM API 調用成功")
                self._thread_logger.debug(f"LLM 回應: {response_content}")

            return str(response_content)

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.error(f"LLM API 調用失敗: {e}")

            # 降級到模擬研究
            return await self._generate_fallback_research(user_input)

    async def _generate_fallback_research(self, user_input: str) -> str:
        """生成降級研究結果"""
        if self._thread_logger:
            self._thread_logger.info("使用降級研究生成")

        return f"""# {user_input} 研究報告

## 概述
由於技術限制，無法進行完整的網路搜尋和資料收集。以下是基於一般知識的初步分析。

## 建議研究方向
1. **基礎概念**: 了解{user_input}的基本定義和核心概念
2. **應用領域**: 探索{user_input}在各個領域的應用情況
3. **發展趨勢**: 分析{user_input}的未來發展方向和潛在機會

## 注意事項
此報告為降級版本，建議使用完整的搜尋工具進行更深入的研究。

## 參考資料
- 需要進一步的網路搜尋和資料收集
"""

    def set_research_parameters(self, locale: str = "zh-TW", max_results: int = 5):
        """設定研究參數"""
        self.locale = locale
        self.max_results = max_results
        if self._thread_logger:
            self._thread_logger.info(f"研究參數更新: locale={locale}, max_results={max_results}")
        else:
            logger.info(f"研究參數更新: locale={locale}, max_results={max_results}")

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
            "role": "researcher",
            "tools": [
                tool.__name__ if hasattr(tool, "__name__") else str(tool) for tool in self._tools
            ],
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

            # 進行研究
            research_result = await self._conduct_research_with_llm(user_input)

            return {
                "response": research_result,
                "locale": self.locale,
                "status": "success",
            }

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.error(f"處理用戶輸入失敗: {e}")
            else:
                logger.error(f"處理用戶輸入失敗: {e}")

            return {
                "response": f"抱歉，進行研究時發生錯誤：{str(e)}",
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
    async def conduct_research(
        self,
        research_task: str,
        locale: str = "zh-TW",
        resources: List[str] = None,
        time_range: str = None,
    ) -> ResearchFindings:
        """
        進行研究（兼容舊接口）

        Args:
            research_task: 研究任務
            locale: 語言設定
            resources: 資源列表
            time_range: 時間範圍

        Returns:
            ResearchFindings: 研究發現
        """
        try:
            # 設置參數
            self.set_research_parameters(locale)

            # 建構研究輸入
            research_input = f"# 研究任務\n{research_task}\n"
            if resources:
                research_input += f"\n# 可用資源\n" + "\n".join(f"- {res}" for res in resources)
            if time_range:
                research_input += f"\n# 時間範圍\n{time_range}\n"

            # 進行研究
            research_result = await self._conduct_research_with_llm(research_input)

            # 解析結果為 ResearchFindings
            return self._parse_research_result(research_task, research_result)

        except Exception as e:
            logger.error(f"進行研究失敗: {e}")
            # 返回降級結果
            return self._create_fallback_research_findings(research_task, locale)

    def _parse_research_result(self, research_task: str, research_result: str) -> ResearchFindings:
        """解析研究結果"""
        # 簡化解析 - 在實際實現中可以更複雜
        findings = [
            {
                "type": "research_result",
                "content": research_result,
                "timestamp": datetime.now().isoformat(),
            }
        ]

        # 提取引用（簡化版本）
        references = []
        for line in research_result.split("\n"):
            if line.strip().startswith("- [") and "](http" in line:
                references.append(line.strip())

        return ResearchFindings(
            problem_statement=research_task,
            findings=findings,
            conclusion="研究完成，詳細結果請參考以上內容。",
            references=references,
            images=[],
        )

    def _create_fallback_research_findings(
        self, research_task: str, locale: str
    ) -> ResearchFindings:
        """創建降級研究發現"""
        findings = [
            {
                "type": "fallback",
                "content": f"由於技術限制，無法完成對「{research_task}」的完整研究。建議使用完整的搜尋工具進行更深入的調查。",
                "timestamp": datetime.now().isoformat(),
            }
        ]

        return ResearchFindings(
            problem_statement=research_task,
            findings=findings,
            conclusion="需要進一步的研究工具支持。",
            references=[],
            images=[],
        )

    async def investigate_topic(self, research_topic: str) -> str:
        """調查主題（兼容舊接口）"""
        result = await self._conduct_research_with_llm(f"請深入調查以下主題：{research_topic}")
        return result

    async def execute_research_step(self, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """執行研究步驟（兼容舊接口）"""
        try:
            step_description = step_input.get("description", "")
            step_title = step_input.get("title", "研究步驟")

            research_input = f"# {step_title}\n{step_description}"

            result = await self._conduct_research_with_llm(research_input)

            return {
                "step_title": step_title,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "step_title": step_input.get("title", "研究步驟"),
                "result": f"執行失敗：{str(e)}",
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
            }

    async def analyze_research_data(self, analysis_input: Dict[str, Any]) -> Dict[str, Any]:
        """分析研究資料（兼容舊接口）"""
        try:
            data = analysis_input.get("data", "")
            analysis_type = analysis_input.get("analysis_type", "general")

            analysis_prompt = f"# 資料分析任務\n分析類型：{analysis_type}\n\n資料內容：\n{data}"

            result = await self._conduct_research_with_llm(analysis_prompt)

            return {
                "analysis_type": analysis_type,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "analysis_type": analysis_input.get("analysis_type", "general"),
                "result": f"分析失敗：{str(e)}",
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
            }
