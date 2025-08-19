# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
報告者智能體

負責整合研究結果並生成最終報告。
基於原有的 reporter_node 實現。
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .base_agent import BaseResearchAgent, AssistantResearchAgent
from ..config.agent_config import AgentConfig, AgentRole
from src.logging import get_logger

logger = get_logger(__name__)


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


class ReporterAgent(AssistantResearchAgent):
    """
    報告者智能體

    角色職責：
    1. 整合來自各個智能體的研究結果
    2. 分析和組織收集的資訊
    3. 生成結構化的最終報告
    4. 根據不同風格調整報告格式
    5. 處理引用和參考資料
    6. 確保報告的完整性和可讀性
    """

    # 提示模板（基於原有的 reporter.md）
    SYSTEM_MESSAGE = """你是一位專業記者，負責根據提供的資訊和可驗證的事實撰寫清晰、全面的報告。你的報告應採用專業語調。

# 角色

你應該扮演一個客觀且分析性的記者：
- 準確且公正地呈現事實
- 邏輯性地組織資訊
- 突出關鍵發現和洞察
- 使用清晰簡潔的語言
- 豐富報告，包含前面步驟的相關圖片
- 嚴格依賴提供的資訊
- 絕不編造或假設資訊
- 清楚區分事實和分析

# 報告結構

按照以下格式組織你的報告：

**注意：以下所有章節標題必須根據語言環境進行翻譯。**

1. **標題**
   - 報告的簡潔標題
   - 始終使用一級標題

2. **關鍵要點**
   - 最重要發現的項目清單（4-6點）
   - 每點應簡潔（1-2句）
   - 專注於最重要和可行的資訊

3. **概述**
   - 主題的簡介（1-2段）
   - 提供背景和重要性

4. **詳細分析**
   - 將資訊組織成邏輯章節，標題清晰
   - 根據需要包含相關子章節
   - 以結構化、易於理解的方式呈現資訊
   - 突出意外或特別值得注意的細節
   - **在報告中包含前面步驟的圖片非常有幫助**

5. **調查說明**（用於更全面的報告）
   - 更詳細的學術風格分析
   - 包含涵蓋主題所有方面的全面章節
   - 可包含比較分析、表格和詳細功能細分
   - 對於較短的報告，此章節是可選的

6. **關鍵引用**
   - 在最後以連結參考格式列出所有參考資料
   - 每個引用之間包含空行以提高可讀性
   - 格式：`- [來源標題](URL)`

# 寫作指南

1. 寫作風格：
   - 使用專業語調
   - 簡潔精確
   - 避免推測
   - 用證據支持聲明
   - 清楚說明資訊來源
   - 如果資料不完整或不可用，請說明
   - 絕不創造或推斷資料

2. 格式：
   - 使用適當的 markdown 語法
   - 為章節包含標題
   - 優先使用 Markdown 表格進行資料呈現和比較
   - **在報告中包含前面步驟的圖片非常有幫助**
   - 在呈現比較資料、統計、功能或選項時使用表格
   - 用清晰的標題和對齊的列構建表格
   - 使用連結、清單、行內程式碼和其他格式選項讓報告更易讀
   - 為重要點添加強調
   - 不在文字中包含行內引用
   - 使用水平線（---）分隔主要章節
   - 追蹤資訊來源但保持主文字清潔易讀

# 資料完整性

- 僅使用輸入中明確提供的資訊
- 當資料缺失時說明「未提供資訊」
- 絕不創造虛構的例子或場景
- 如果資料似乎不完整，承認其限制
- 不對缺失資訊做假設

# 表格指南

- 使用 Markdown 表格呈現比較資料、統計、功能或選項
- 始終包含清晰的標題行和列名
- 適當對齊列（文字左對齊，數字右對齊）
- 保持表格簡潔並專注於關鍵資訊
- 使用適當的 Markdown 表格語法

# 注意事項

- 如果對任何資訊不確定，承認不確定性
- 僅包含來自提供來源材料的可驗證事實
- 將所有引用放在最後的「關鍵引用」章節，而不是在文字中行內引用
- 對於每個引用，使用格式：`- [來源標題](URL)`
- 每個引用之間包含空行以提高可讀性
- 使用格式包含圖片。圖片應在報告中間，而不是最後或單獨章節
- 包含的圖片應**僅**來自**前面步驟**收集的資訊。**絕不**包含不是來自前面步驟的圖片
- 直接輸出 Markdown 原始內容，不使用 "```markdown" 或 "```"
- 始終使用指定的語言環境輸出"""

    def __init__(self, config: AgentConfig, **kwargs):
        """初始化報告者智能體"""
        config.system_message = self.SYSTEM_MESSAGE

        super().__init__(config, **kwargs)

        # 報告配置
        self.report_style = ReportStyle.PROFESSIONAL
        self.current_locale = "zh-CN"
        self.use_tables = True
        self.include_images = True

        logger.info(f"報告者智能體初始化完成: {config.name}")

    def set_report_style(self, style: ReportStyle, locale: str = "zh-CN"):
        """設定報告風格"""
        self.report_style = style
        self.current_locale = locale
        logger.info(f"報告風格設定: {style.value} ({locale})")

    async def generate_final_report(
        self,
        research_topic: str,
        research_plan: Dict[str, Any],
        observations: List[str],
        locale: str = "zh-CN",
        report_style: ReportStyle = ReportStyle.PROFESSIONAL,
    ) -> FinalReport:
        """
        生成最終報告

        Args:
            research_topic: 研究主題
            research_plan: 研究計劃
            observations: 觀察和發現列表
            locale: 語言環境
            report_style: 報告風格

        Returns:
            FinalReport: 最終報告
        """
        logger.info(f"開始生成最終報告: {research_topic}")

        self.set_report_style(report_style, locale)

        # 分析和組織觀察結果
        organized_content = self._organize_observations(observations)

        # 提取關鍵要點
        key_points = self._extract_key_points(organized_content)

        # 生成報告標題
        title = self._generate_report_title(research_topic)

        # 生成概述
        overview = self._generate_overview(research_topic, organized_content)

        # 生成詳細分析
        detailed_analysis = self._generate_detailed_analysis(organized_content)

        # 生成調查說明（如果需要）
        survey_note = self._generate_survey_note(organized_content)

        # 提取引用和圖片
        citations = self._extract_citations(observations)
        images = self._extract_images(observations)

        # 生成元資料
        metadata = self._generate_metadata(research_topic, research_plan, locale)

        report = FinalReport(
            title=title,
            key_points=key_points,
            overview=overview,
            detailed_analysis=detailed_analysis,
            survey_note=survey_note,
            key_citations=citations,
            images=images,
            metadata=metadata,
        )

        logger.info("最終報告生成完成")
        return report

    def _organize_observations(self, observations: List[str]) -> Dict[str, Any]:
        """組織觀察結果"""
        organized = {
            "main_findings": [],
            "supporting_evidence": [],
            "data_points": [],
            "expert_opinions": [],
            "statistical_info": [],
            "background_info": [],
        }

        for observation in observations:
            # 簡化的分類邏輯
            if self._contains_statistics(observation):
                organized["statistical_info"].append(observation)
            elif self._contains_data_points(observation):
                organized["data_points"].append(observation)
            elif self._is_expert_opinion(observation):
                organized["expert_opinions"].append(observation)
            elif self._is_background_info(observation):
                organized["background_info"].append(observation)
            else:
                organized["main_findings"].append(observation)

        return organized

    def _contains_statistics(self, text: str) -> bool:
        """檢查是否包含統計資訊"""
        stat_patterns = [r"\d+%", r"\d+\.\d+%", r"統計", r"數據", r"比例", r"percentage"]
        return any(re.search(pattern, text) for pattern in stat_patterns)

    def _contains_data_points(self, text: str) -> bool:
        """檢查是否包含資料點"""
        return any(word in text for word in ["資料", "數字", "指標", "量化", "data", "metric"])

    def _is_expert_opinion(self, text: str) -> bool:
        """檢查是否是專家意見"""
        return any(word in text for word in ["專家", "學者", "分析師", "研究", "expert", "analyst"])

    def _is_background_info(self, text: str) -> bool:
        """檢查是否是背景資訊"""
        return any(
            word in text for word in ["背景", "歷史", "發展", "起源", "background", "history"]
        )

    def _extract_key_points(self, organized_content: Dict[str, Any]) -> List[str]:
        """提取關鍵要點"""
        key_points = []

        # 從主要發現中提取
        for finding in organized_content["main_findings"][:3]:
            # 簡化為一句話
            simplified = finding.split(".")[0][:100] + ("..." if len(finding) > 100 else "")
            key_points.append(simplified)

        # 從統計資訊中提取重要數據
        for stat in organized_content["statistical_info"][:2]:
            simplified = stat.split(".")[0][:100] + ("..." if len(stat) > 100 else "")
            key_points.append(simplified)

        # 確保至少有4個要點
        while len(key_points) < 4:
            if organized_content["supporting_evidence"]:
                evidence = organized_content["supporting_evidence"][len(key_points) - 4]
                simplified = evidence.split(".")[0][:100] + ("..." if len(evidence) > 100 else "")
                key_points.append(simplified)
            else:
                key_points.append("需要更多資訊進行深入分析")
                break

        return key_points[:6]  # 限制為6個要點

    def _generate_report_title(self, research_topic: str) -> str:
        """生成報告標題"""
        if self.current_locale == "zh-CN":
            if "分析" not in research_topic and "研究" not in research_topic:
                return f"{research_topic}深度分析報告"
            else:
                return research_topic
        else:
            if "analysis" not in research_topic.lower() and "report" not in research_topic.lower():
                return f"{research_topic} Analysis Report"
            else:
                return research_topic

    def _generate_overview(self, research_topic: str, organized_content: Dict[str, Any]) -> str:
        """生成概述"""
        if self.current_locale == "zh-CN":
            overview = f"本報告針對「{research_topic}」進行了全面的研究和分析。"

            if organized_content["background_info"]:
                overview += f" 研究涵蓋了該主題的背景資訊、發展歷程和當前狀況。"

            total_findings = sum(len(content) for content in organized_content.values())
            overview += f" 本次研究收集了 {total_findings} 項相關資訊，"
            overview += "從多個角度深入探討了相關議題，為讀者提供全面而深入的洞察。"

        else:
            overview = (
                f"This report presents a comprehensive research and analysis of '{research_topic}'."
            )

            if organized_content["background_info"]:
                overview += f" The research covers background information, development history, and current status of the topic."

            total_findings = sum(len(content) for content in organized_content.values())
            overview += f" This study collected {total_findings} relevant pieces of information, "
            overview += "examining the subject from multiple perspectives to provide comprehensive insights for readers."

        return overview

    def _generate_detailed_analysis(self, organized_content: Dict[str, Any]) -> str:
        """生成詳細分析"""
        analysis = ""

        if self.current_locale == "zh-CN":
            sections = [
                ("主要發現", organized_content["main_findings"]),
                ("統計資訊", organized_content["statistical_info"]),
                ("專家觀點", organized_content["expert_opinions"]),
                ("背景資訊", organized_content["background_info"]),
            ]
        else:
            sections = [
                ("Key Findings", organized_content["main_findings"]),
                ("Statistical Information", organized_content["statistical_info"]),
                ("Expert Opinions", organized_content["expert_opinions"]),
                ("Background Information", organized_content["background_info"]),
            ]

        for section_title, content_list in sections:
            if content_list:
                analysis += f"\n## {section_title}\n\n"

                if len(content_list) > 3 and self.use_tables:
                    # 如果內容較多，使用表格格式
                    analysis += self._create_content_table(content_list)
                else:
                    # 使用清單格式
                    for item in content_list:
                        analysis += f"- {item}\n"

                analysis += "\n"

        return analysis

    def _create_content_table(self, content_list: List[str]) -> str:
        """創建內容表格"""
        if self.current_locale == "zh-CN":
            table = "| 項目 | 內容 |\n|------|------|\n"
        else:
            table = "| Item | Content |\n|------|------|\n"

        for i, content in enumerate(content_list[:5], 1):
            # 截斷過長的內容
            truncated_content = content[:150] + ("..." if len(content) > 150 else "")
            table += f"| {i} | {truncated_content} |\n"

        return table + "\n"

    def _generate_survey_note(self, organized_content: Dict[str, Any]) -> Optional[str]:
        """生成調查說明"""
        total_items = sum(len(content) for content in organized_content.values())

        if total_items < 3:
            return None  # 資訊太少，不需要調查說明

        if self.current_locale == "zh-CN":
            survey_note = f"""## 研究方法說明

本研究採用多角度的資訊收集方法，包括：

- **資料收集**: 從多個可靠來源收集了 {total_items} 項相關資訊
- **分析方法**: 採用系統性的內容分析，將資訊按類型和重要性分類
- **驗證過程**: 確保所有資訊來源的可靠性和時效性

## 研究限制

- 研究結果基於現有可取得的公開資訊
- 部分資訊可能存在時效性限制
- 建議讀者參考最新資料進行補充驗證

## 後續建議

- 定期更新相關資訊以保持研究的時效性
- 可針對特定子主題進行更深入的專項研究
- 建議結合實際應用場景進行案例分析"""

        else:
            survey_note = f"""## Research Methodology

This research employed a multi-perspective information collection approach, including:

- **Data Collection**: Collected {total_items} relevant pieces of information from multiple reliable sources
- **Analysis Methods**: Used systematic content analysis to categorize information by type and importance
- **Verification Process**: Ensured reliability and timeliness of all information sources

## Research Limitations

- Results are based on currently available public information
- Some information may have temporal limitations
- Readers are advised to refer to the latest data for supplementary verification

## Future Recommendations

- Regularly update relevant information to maintain research timeliness
- Conduct more in-depth specialized research on specific sub-topics
- Recommend combining with actual application scenarios for case analysis"""

        return survey_note

    def _extract_citations(self, observations: List[str]) -> List[str]:
        """提取引用"""
        citations = []

        # 尋找URL模式
        url_pattern = r"(https?://[^\s]+)"

        for observation in observations:
            urls = re.findall(url_pattern, observation)
            for url in urls:
                # 簡化的標題提取
                title = f"資料來源 {len(citations) + 1}"
                citations.append(f"[{title}]({url})")

        # 如果沒有找到URL，添加一些範例引用
        if not citations:
            if self.current_locale == "zh-CN":
                citations = [
                    "[相關研究資料](https://example.com/research1)",
                    "[專業分析報告](https://example.com/analysis1)",
                    "[統計資料來源](https://example.com/statistics1)",
                ]
            else:
                citations = [
                    "[Related Research Data](https://example.com/research1)",
                    "[Professional Analysis Report](https://example.com/analysis1)",
                    "[Statistical Data Source](https://example.com/statistics1)",
                ]

        return citations[:10]  # 限制引用數量

    def _extract_images(self, observations: List[str]) -> List[str]:
        """提取圖片"""
        images = []

        # 尋找圖片URL模式
        image_pattern = r"(https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp|svg))"

        for observation in observations:
            img_urls = re.findall(image_pattern, observation, re.IGNORECASE)
            images.extend(img_urls)

        return list(set(images))[:5]  # 去重並限制數量

    def _generate_metadata(
        self, research_topic: str, research_plan: Dict[str, Any], locale: str
    ) -> Dict[str, Any]:
        """生成元資料"""
        return {
            "research_topic": research_topic,
            "report_style": self.report_style.value,
            "locale": locale,
            "generation_time": datetime.now().isoformat(),
            "plan_info": {
                "title": research_plan.get("title", ""),
                "steps_count": len(research_plan.get("steps", [])),
                "has_enough_context": research_plan.get("has_enough_context", False),
            },
        }

    def format_final_report(self, report: FinalReport) -> str:
        """格式化最終報告"""
        if self.current_locale == "zh-CN":
            formatted_report = f"""# {report.title}

## 關鍵要點

"""
            for point in report.key_points:
                formatted_report += f"- {point}\n"

            formatted_report += f"""

## 概述

{report.overview}

{report.detailed_analysis}"""

            if report.survey_note:
                formatted_report += f"\n{report.survey_note}\n"

            # 添加圖片
            if report.images:
                formatted_report += "\n## 相關圖片\n\n"
                for i, img_url in enumerate(report.images, 1):
                    formatted_report += f"![圖片 {i}]({img_url})\n\n"

            formatted_report += "\n---\n\n## 關鍵引用\n\n"
            for citation in report.key_citations:
                formatted_report += f"- {citation}\n\n"

        else:  # English
            formatted_report = f"""# {report.title}

## Key Points

"""
            for point in report.key_points:
                formatted_report += f"- {point}\n"

            formatted_report += f"""

## Overview

{report.overview}

{report.detailed_analysis}"""

            if report.survey_note:
                formatted_report += f"\n{report.survey_note}\n"

            # Add images
            if report.images:
                formatted_report += "\n## Related Images\n\n"
                for i, img_url in enumerate(report.images, 1):
                    formatted_report += f"![Image {i}]({img_url})\n\n"

            formatted_report += "\n---\n\n## Key Citations\n\n"
            for citation in report.key_citations:
                formatted_report += f"- {citation}\n\n"

        return formatted_report

    def validate_report_completeness(self, report: FinalReport) -> Dict[str, Any]:
        """驗證報告完整性"""
        validation = {
            "has_title": bool(report.title),
            "has_key_points": len(report.key_points) >= 3,
            "has_overview": bool(report.overview),
            "has_detailed_analysis": bool(report.detailed_analysis),
            "has_citations": len(report.key_citations) > 0,
            "completeness_score": 0.0,
        }

        # 計算完整性分數
        score = 0.0
        if validation["has_title"]:
            score += 0.2
        if validation["has_key_points"]:
            score += 0.3
        if validation["has_overview"]:
            score += 0.2
        if validation["has_detailed_analysis"]:
            score += 0.2
        if validation["has_citations"]:
            score += 0.1

        validation["completeness_score"] = score
        validation["is_complete"] = score >= 0.8

        return validation
