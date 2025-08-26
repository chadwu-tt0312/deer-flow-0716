# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
報告者智能體 - AutoGen 框架版本

負責整合研究結果並生成最終報告。
基於 reporter_node 實現，使用 AutoGen 的 BaseChatAgent。
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

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


class ReportStyle(Enum):
    """報告風格"""

    ACADEMIC = "academic"
    POPULAR_SCIENCE = "popular_science"
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"
    PROFESSIONAL = "professional"


@dataclass
class ReportSection:
    """報告章節"""

    title: str
    content: str
    section_type: str
    order: int


@dataclass
class FinalReport:
    """最終報告"""

    title: str
    key_points: List[str]
    overview: str
    detailed_analysis: str
    survey_note: Optional[str]
    key_citations: List[str]
    images: List[str]
    metadata: Dict[str, Any]


class ReporterAgent(BaseChatAgent):
    """
    報告者智能體 - AutoGen 框架版本

    基於 reporter_node 實現，角色職責：
    1. 整合來自各個智能體的研究結果
    2. 分析和組織收集的資訊
    3. 生成結構化的最終報告
    4. 根據不同風格調整報告格式
    5. 處理引用和參考資料
    6. 確保報告的完整性和可讀性
    """

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        description: str = "報告者智能體 - 整合研究結果並生成最終報告",
        system_messages: Optional[List[SystemMessage]] = None,
    ):
        """
        初始化報告者智能體

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
        self.role = "reporter"
        self.report_style = ReportStyle.PROFESSIONAL
        self.locale = "zh-TW"

        logger.info(f"ReporterAgent 初始化完成: {name}")

    # 提示模板（基於原有的 reporter.md）
    DEFAULT_SYSTEM_MESSAGE = """你是一位專業記者，負責根據提供的資訊和可驗證的事實撰寫清晰、全面的報告。你的報告應採用專業語調。

## 職責

1. **資訊整合**: 將來自多個來源的資訊整合成連貫的報告
2. **結構化撰寫**: 創建清晰的報告結構，包括概述、詳細分析和結論
3. **事實核查**: 確保所有資訊都是準確和可驗證的
4. **引用管理**: 適當地引用所有來源和參考資料
5. **格式化**: 使用適當的 Markdown 格式，包括表格和列表

## 報告結構

每個報告應包含以下部分：

### 1. 關鍵要點
- 以項目符號列出最重要的發現
- 每個要點應簡潔且資訊豐富

### 2. 概述
- 對主題的簡短介紹
- 為什麼這個主題重要
- 報告將涵蓋的內容概要

### 3. 詳細分析
- 深入探討主題的各個方面
- 組織成邏輯清晰的章節
- 包含具體的資料、統計數據和例子

### 4. 調查說明（可選）
- 對於更全面的報告，包含調查方法和限制的說明

### 5. 重要引用
- 在報告末尾列出所有參考資料
- 使用格式：`- [來源標題](URL)`
- 每個引用之間留空行

## 格式要求

- **表格優先**: 在呈現比較資料、統計數據或特徵時，優先使用 Markdown 表格
- **無內文引用**: 不要在文本中包含內文引用
- **清晰的標題**: 使用適當的標題層級（## ### ####）
- **視覺層次**: 使用粗體、斜體和列表來增強可讀性"""

    def _setup_thread_context(self, thread_id: str):
        """設置線程上下文和日誌"""
        self._current_thread_id = thread_id

        if HAS_THREAD_LOGGING:
            try:
                self._thread_logger = setup_thread_logging(thread_id)
                set_thread_context(thread_id)

                if self._thread_logger:
                    self._thread_logger.info("ReporterAgent talking.")
                else:
                    logger.info("ReporterAgent talking.")
            except Exception as e:
                logger.warning(f"線程日誌設置失敗，使用標準 logger: {e}")
                self._thread_logger = logger
                logger.info("ReporterAgent talking.")
        else:
            self._thread_logger = logger
            logger.info("ReporterAgent talking.")

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

        thread_id = f"reporter_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
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
                                "reporter", template_state, config_obj
                            )
                        except Exception as config_error:
                            if self._thread_logger:
                                self._thread_logger.warning(
                                    f"配置轉換失敗，使用無配置版本: {config_error}"
                                )
                            template_messages = apply_prompt_template("reporter", template_state)
                    else:
                        template_messages = apply_prompt_template(
                            "reporter", template_state, self._configuration
                        )
                else:
                    template_messages = apply_prompt_template("reporter", template_state)

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
                self._thread_logger.info(f"ReporterAgent 開始處理報告生成: {user_input}")

            # 調用報告生成邏輯
            report_result = await self._generate_report_with_llm(user_input, cancellation_token)

            return TextMessage(content=report_result, source=self.name)

        except Exception as e:
            error_msg = f"處理報告生成失敗: {str(e)}"
            logger.error(error_msg)

            if self._thread_logger:
                self._thread_logger.error(error_msg)

            return TextMessage(content=f"抱歉，生成報告時出現錯誤：{str(e)}", source=self.name)

    async def _generate_report_with_llm(
        self, user_input: str, cancellation_token: Optional[CancellationToken] = None
    ) -> str:
        """使用 LLM 生成報告"""
        try:
            # 更新狀態
            self._state.update(
                {
                    "messages": [{"role": "user", "content": user_input}],
                    "locale": self.locale,
                    "research_topic": self._extract_topic_from_input(user_input),
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
                self._thread_logger.info("調用 LLM API 進行報告生成...")

            # 調用 LLM
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

            # 降級到模擬報告
            return await self._generate_fallback_report(user_input)

    def _extract_topic_from_input(self, user_input: str) -> str:
        """從輸入中提取主題"""
        # 簡化版本 - 實際實現可以更複雜
        lines = user_input.split("\n")
        for line in lines:
            if "主題" in line or "Topic" in line or "研究任務" in line:
                return line.split(":", 1)[-1].strip() if ":" in line else line.strip()

        # 降級到前100個字符
        return user_input[:100] + "..." if len(user_input) > 100 else user_input

    async def _generate_fallback_report(self, user_input: str) -> str:
        """生成降級報告"""
        if self._thread_logger:
            self._thread_logger.info("使用降級報告生成")

        topic = self._extract_topic_from_input(user_input)

        return f"""# {topic} - 研究報告

## 關鍵要點

- 由於技術限制，本報告為簡化版本
- 建議使用完整的研究工具進行更深入的分析
- 需要進一步的資料收集和驗證

## 概述

本報告旨在提供關於「{topic}」的基本資訊。由於當前技術限制，無法進行完整的資料收集和分析。

## 詳細分析

### 基本資訊
需要進一步的研究來收集詳細資訊。

### 現狀分析
建議使用專業的搜尋工具和資料庫來獲取最新資訊。

### 趨勢分析
需要更多資料來進行趨勢分析。

## 調查說明

本報告為降級版本，主要限制包括：
- 無法進行網路搜尋
- 缺乏實時資料存取
- 無法驗證資訊來源

## 重要引用

- 需要進一步的資料收集
"""

    def set_report_style(self, style: ReportStyle, locale: str = "zh-TW"):
        """設定報告風格"""
        self.report_style = style
        self.locale = locale
        if self._thread_logger:
            self._thread_logger.info(f"報告風格更新: style={style.value}, locale={locale}")
        else:
            logger.info(f"報告風格更新: style={style.value}, locale={locale}")

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
            "role": "reporter",
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

            # 生成報告
            report_result = await self._generate_report_with_llm(user_input)

            return {
                "response": report_result,
                "locale": self.locale,
                "status": "success",
            }

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.error(f"處理用戶輸入失敗: {e}")
            else:
                logger.error(f"處理用戶輸入失敗: {e}")

            return {
                "response": f"抱歉，生成報告時發生錯誤：{str(e)}",
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
    async def generate_final_report(
        self,
        research_topic: str,
        research_plan: Dict[str, Any],
        observations: List[str],
        locale: str = "zh-TW",
        report_style: ReportStyle = ReportStyle.PROFESSIONAL,
    ) -> FinalReport:
        """
        生成最終報告（兼容舊接口）
        """
        try:
            # 設置參數
            self.set_report_style(report_style, locale)

            # 建構報告輸入
            report_input = f"# 研究主題\n{research_topic}\n\n"

            if research_plan:
                report_input += (
                    f"# 研究計劃\n{json.dumps(research_plan, ensure_ascii=False, indent=2)}\n\n"
                )

            if observations:
                report_input += f"# 觀察結果\n"
                for i, obs in enumerate(observations, 1):
                    report_input += f"## 觀察 {i}\n{obs}\n\n"

            # 生成報告
            report_content = await self._generate_report_with_llm(report_input)

            # 解析報告為 FinalReport
            return self._parse_report_content(research_topic, report_content)

        except Exception as e:
            logger.error(f"生成最終報告失敗: {e}")
            # 返回降級報告
            return self._create_fallback_final_report(research_topic, locale)

    def _parse_report_content(self, research_topic: str, report_content: str) -> FinalReport:
        """解析報告內容"""
        # 簡化解析 - 實際實現可以更複雜
        lines = report_content.split("\n")

        # 提取標題
        title = research_topic
        for line in lines:
            if line.startswith("#") and not line.startswith("##"):
                title = line.strip("# ").strip()
                break

        # 提取關鍵要點
        key_points = []
        in_key_points = False
        for line in lines:
            if "關鍵要點" in line or "Key Points" in line:
                in_key_points = True
                continue
            if in_key_points and line.startswith("- "):
                key_points.append(line[2:].strip())
            elif in_key_points and line.startswith("#"):
                break

        # 提取引用
        key_citations = []
        for line in lines:
            if line.strip().startswith("- [") and "](http" in line:
                key_citations.append(line.strip())

        return FinalReport(
            title=title,
            key_points=key_points,
            overview="報告概述",
            detailed_analysis=report_content,
            survey_note=None,
            key_citations=key_citations,
            images=[],
            metadata={
                "generated_at": datetime.now().isoformat(),
                "locale": self.locale,
                "style": self.report_style.value,
            },
        )

    def _create_fallback_final_report(self, research_topic: str, locale: str) -> FinalReport:
        """創建降級最終報告"""
        key_points = [
            "由於技術限制，本報告為簡化版本",
            "建議使用完整的研究工具進行更深入的分析",
            "需要進一步的資料收集和驗證",
        ]

        overview = f"本報告旨在提供關於「{research_topic}」的基本資訊。由於當前技術限制，無法進行完整的資料收集和分析。"

        detailed_analysis = f"""# {research_topic} - 研究報告

## 概述
{overview}

## 詳細分析
需要進一步的研究來收集詳細資訊。

## 結論
建議使用專業的搜尋工具和資料庫來獲取最新資訊。
"""

        return FinalReport(
            title=f"{research_topic} - 研究報告",
            key_points=key_points,
            overview=overview,
            detailed_analysis=detailed_analysis,
            survey_note="本報告為降級版本，存在技術限制。",
            key_citations=[],
            images=[],
            metadata={
                "generated_at": datetime.now().isoformat(),
                "locale": locale,
                "style": "fallback",
            },
        )
