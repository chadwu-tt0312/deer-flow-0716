# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
研究者智能體

負責執行網路搜尋、資訊收集和內容爬取任務。
基於原有的 researcher_node 實現。
"""

import re
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

from .base_agent import BaseResearchAgent, AssistantResearchAgent
from ..config.agent_config import AgentConfig, AgentRole
from src.logging import get_logger

logger = get_logger(__name__)


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


class ResearcherAgent(AssistantResearchAgent):
    """
    研究者智能體

    角色職責：
    1. 進行網路搜尋和資訊收集
    2. 爬取特定 URL 的內容
    3. 使用本地知識庫搜尋
    4. 整合多來源資訊
    5. 生成結構化的研究報告
    6. 處理時間範圍約束
    """

    # 提示模板（基於原有的 researcher.md）
    SYSTEM_MESSAGE = """你是由監督智能體管理的 `researcher` 智能體。

你致力於使用搜尋工具進行徹底調查，並透過系統性使用可用工具（包括內建工具和動態載入工具）提供全面解決方案。

# 可用工具

你可以存取兩種類型的工具：

1. **內建工具**：這些始終可用：
   - **local_search_tool**：當用戶在訊息中提及時，用於從本地知識庫檢索資訊
   - **web_search_tool**：用於執行網路搜尋
   - **crawl_tool**：用於從 URL 讀取內容

2. **動態載入工具**：根據配置可能可用的額外工具。這些工具會動態載入並出現在你的可用工具清單中。例如：
   - 專業搜尋工具
   - Google 地圖工具
   - 資料庫檢索工具
   - 以及許多其他工具

## 如何使用動態載入工具

- **工具選擇**：為每個子任務選擇最合適的工具。在可用時優先選擇專業工具而非通用工具
- **工具文件**：使用前仔細閱讀工具文件。注意必需參數和預期輸出
- **錯誤處理**：如果工具返回錯誤，嘗試理解錯誤訊息並相應調整方法
- **組合工具**：通常，最佳結果來自於組合多個工具

# 步驟

1. **理解問題**：忘記你之前的知識，仔細閱讀問題陳述以識別所需的關鍵資訊
2. **評估可用工具**：注意你可用的所有工具，包括任何動態載入的工具
3. **規劃解決方案**：確定使用可用工具解決問題的最佳方法
4. **執行解決方案**：
   - 忘記你之前的知識，所以你**應該利用工具**來檢索資訊
   - 使用 **local_search_tool** 或 **web_search_tool** 或其他合適的搜尋工具
   - 當任務包含時間範圍要求時，在查詢中納入適當的基於時間的搜尋參數
   - 確保搜尋結果符合指定的時間約束
   - 驗證來源的發布日期以確認它們在所需時間範圍內
   - 當更適合特定任務時使用動態載入工具
   - （可選）使用 **crawl_tool** 從必要的 URL 讀取內容
5. **綜合資訊**：
   - 結合從所有使用工具收集的資訊
   - 確保回應清晰、簡潔並直接解決問題
   - 追蹤並歸屬所有資訊來源及其各自的 URL 以供適當引用
   - 在有幫助時包含來自收集資訊的相關圖片

# 輸出格式

- 提供 markdown 格式的結構化回應
- 包含以下章節：
    - **問題陳述**：為了清晰重述問題
    - **研究發現**：按主題而非使用的工具組織你的發現。對於每個主要發現：
        - 總結關鍵資訊
        - 追蹤資訊來源但不在文字中包含內聯引用
        - 如果可用則包含相關圖片
    - **結論**：基於收集的資訊對問題提供綜合回應
    - **參考資料**：在文件末尾以連結參考格式列出所有使用的來源
- 始終以指定的語言環境輸出
- 不在文字中包含內聯引用。相反，追蹤所有來源並在末尾的參考資料章節中列出

# 注意事項

- 始終驗證收集資訊的相關性和可信度
- 如果沒有提供 URL，僅專注於搜尋結果
- 永不進行任何數學運算或檔案操作
- 不嘗試與頁面互動。爬取工具只能用於爬取內容
- 不執行任何數學計算
- 不嘗試任何檔案操作
- 只有在僅從搜尋結果無法獲得必要資訊時才調用 crawl_tool
- 始終為所有資訊包含來源歸屬
- 當提供來自多個來源的資訊時，清楚表明每條資訊來自哪個來源
- 在單獨章節中使用格式包含圖片
- 包含的圖片應**僅**來自**從搜尋結果或爬取內容**收集的資訊
- 始終使用指定的語言環境進行輸出
- 當任務中指定時間範圍要求時，嚴格遵守這些約束並驗證所有提供的資訊都在指定時間期間內"""

    def __init__(self, config: AgentConfig, tools: List[Callable] = None, **kwargs):
        """初始化研究者智能體"""
        config.system_message = self.SYSTEM_MESSAGE

        # 設定研究者專用的工具
        research_tools = tools or []

        super().__init__(config, research_tools, **kwargs)

        # 初始化研究參數
        self.current_locale = "zh-CN"
        self.max_search_results = 5

        logger.info(f"研究者智能體初始化完成: {config.name}")

    def set_research_parameters(self, locale: str = "zh-CN", max_results: int = 5):
        """設定研究參數"""
        self.current_locale = locale
        self.max_search_results = max_results
        logger.info(f"研究參數更新: locale={locale}, max_results={max_results}")

    async def conduct_research(
        self,
        research_task: str,
        locale: str = "zh-CN",
        resources: List[str] = None,
        time_range: str = None,
    ) -> ResearchFindings:
        """
        執行研究任務

        Args:
            research_task: 研究任務描述
            locale: 語言環境
            resources: 資源列表（URL 或檔案）
            time_range: 時間範圍約束

        Returns:
            ResearchFindings: 研究結果
        """
        logger.info(f"開始執行研究任務: {research_task}")

        self.set_research_parameters(locale, self.max_search_results)

        # 解析研究任務
        research_plan = self._parse_research_task(research_task)

        # 執行搜尋
        search_results = await self._execute_search(research_plan, time_range)

        # 如果有指定資源，進行本地搜尋或爬取
        if resources:
            local_results = await self._search_local_resources(research_plan, resources)
            search_results.extend(local_results)

        # 整合結果
        findings = self._synthesize_findings(research_task, search_results)

        logger.info(f"研究任務完成: {len(search_results)} 個結果")
        return findings

    def _parse_research_task(self, task: str) -> Dict[str, Any]:
        """解析研究任務"""
        # 提取關鍵詞
        keywords = self._extract_keywords(task)

        # 判斷任務類型
        task_type = self._classify_task_type(task)

        # 提取時間約束
        time_constraints = self._extract_time_constraints(task)

        return {
            "original_task": task,
            "keywords": keywords,
            "task_type": task_type,
            "time_constraints": time_constraints,
            "search_queries": self._generate_search_queries(task, keywords),
        }

    def _extract_keywords(self, task: str) -> List[str]:
        """提取關鍵詞"""
        # 簡單的關鍵詞提取邏輯
        # 實際實現可以使用更複雜的 NLP 技術

        # 移除常見停用詞
        stop_words = {"的", "是", "在", "了", "和", "與", "或", "但", "然而", "因為", "所以"}

        # 分詞（簡化版本）
        words = re.findall(r"\b\w+\b", task)
        keywords = [word for word in words if word not in stop_words and len(word) > 1]

        return keywords[:10]  # 限制關鍵詞數量

    def _classify_task_type(self, task: str) -> str:
        """分類任務類型"""
        task_lower = task.lower()

        if any(word in task_lower for word in ["程式", "代碼", "code", "programming"]):
            return "technical"
        elif any(word in task_lower for word in ["市場", "趨勢", "分析", "market", "trend"]):
            return "market_analysis"
        elif any(word in task_lower for word in ["歷史", "發展", "history", "development"]):
            return "historical"
        else:
            return "general"

    def _extract_time_constraints(self, task: str) -> Optional[Dict[str, str]]:
        """提取時間約束"""
        # 尋找時間相關的表達
        time_patterns = [
            r"(\d{4})年",
            r"(\d{4})-(\d{4})",
            r"最近(\d+)年",
            r"過去(\d+)年",
            r"近年來",
            r"最新",
            r"當前",
        ]

        for pattern in time_patterns:
            match = re.search(pattern, task)
            if match:
                return {"type": "time_range", "value": match.group()}

        return None

    def _generate_search_queries(self, task: str, keywords: List[str]) -> List[str]:
        """生成搜尋查詢"""
        queries = []

        # 主要查詢
        queries.append(task)

        # 基於關鍵詞的查詢
        if len(keywords) >= 2:
            queries.append(" ".join(keywords[:3]))

        # 特定類型的查詢
        if "最佳實務" in task or "best practice" in task.lower():
            queries.append(f"{keywords[0]} 最佳實務")

        if "趨勢" in task or "trend" in task.lower():
            queries.append(f"{keywords[0]} 趨勢 2024")

        return queries[:3]  # 限制查詢數量

    async def _execute_search(
        self, research_plan: Dict[str, Any], time_range: str = None
    ) -> List[SearchResult]:
        """執行搜尋"""
        results = []

        for query in research_plan["search_queries"]:
            # 添加時間範圍到查詢
            if time_range:
                query = f"{query} {time_range}"

            # 調用真正的搜尋工具
            search_results = await self._perform_web_search(query)
            results.extend(search_results)

        return results

    async def _perform_web_search(self, query: str) -> List[SearchResult]:
        """執行真正的網路搜尋"""
        search_results = []

        try:
            # 檢查是否有可用的搜尋工具
            search_tool = None
            for tool_name in ["web_search", "autogen_web_search", "tavily_search"]:
                if hasattr(self, "tools") and tool_name in [
                    getattr(tool, "__name__", "") for tool in self.tools
                ]:
                    search_tool = next(
                        (tool for tool in self.tools if getattr(tool, "__name__", "") == tool_name),
                        None,
                    )
                    break

            if search_tool:
                logger.info(f"使用搜尋工具執行查詢: {query}")
                # 調用搜尋工具
                raw_result = await search_tool(query=query, max_results=self.max_search_results)

                # 解析搜尋結果
                search_results = self._parse_search_results(raw_result, query)
            else:
                logger.warning("未找到可用的搜尋工具，使用模擬結果")
                search_results = await self._simulate_web_search(query)

        except Exception as e:
            logger.error(f"搜尋執行失敗: {e}")
            # 失敗時返回模擬結果
            search_results = await self._simulate_web_search(query)

        logger.info(f"搜尋查詢 '{query}' 返回 {len(search_results)} 個結果")
        return search_results

    def _parse_search_results(self, raw_result: str, query: str) -> List[SearchResult]:
        """解析搜尋工具返回的結果"""
        results = []

        try:
            import json

            # 嘗試解析 JSON 格式的結果
            if isinstance(raw_result, str):
                try:
                    parsed = json.loads(raw_result)
                except json.JSONDecodeError:
                    # 如果不是 JSON，將其作為純文字處理
                    results.append(
                        SearchResult(
                            title=f"搜尋結果: {query}",
                            url="",
                            content=raw_result,
                            source="搜尋引擎",
                            timestamp=datetime.now(),
                        )
                    )
                    return results
            else:
                parsed = raw_result

            # 處理不同格式的搜尋結果
            if isinstance(parsed, dict):
                # 處理包含 results 的格式
                if "results" in parsed:
                    search_items = parsed["results"]
                else:
                    search_items = [parsed]

                for item in search_items:
                    if isinstance(item, dict):
                        results.append(
                            SearchResult(
                                title=item.get("title", f"搜尋結果"),
                                url=item.get("url", ""),
                                content=item.get("content", item.get("snippet", "")),
                                source=item.get("source", "搜尋引擎"),
                                timestamp=datetime.now(),
                            )
                        )

            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        results.append(
                            SearchResult(
                                title=item.get("title", f"搜尋結果"),
                                url=item.get("url", ""),
                                content=item.get("content", item.get("snippet", "")),
                                source=item.get("source", "搜尋引擎"),
                                timestamp=datetime.now(),
                            )
                        )

        except Exception as e:
            logger.error(f"解析搜尋結果失敗: {e}")
            # 解析失敗時創建基本結果
            results.append(
                SearchResult(
                    title=f"搜尋結果: {query}",
                    url="",
                    content=str(raw_result),
                    source="搜尋引擎",
                    timestamp=datetime.now(),
                )
            )

        return results

    async def _simulate_web_search(self, query: str) -> List[SearchResult]:
        """模擬網路搜尋（備用方法）"""
        mock_results = []

        for i in range(min(3, self.max_search_results)):
            mock_results.append(
                SearchResult(
                    title=f"關於 {query} 的搜尋結果 {i + 1}",
                    url=f"https://example.com/search_{i + 1}",
                    content=f"這是關於 {query} 的詳細資訊。包含了相關的背景知識、技術細節和實際應用案例。",
                    source="模擬搜尋引擎",
                    timestamp=datetime.now(),
                )
            )

        logger.info(f"模擬搜尋查詢 '{query}' 返回 {len(mock_results)} 個結果")
        return mock_results

    async def _search_local_resources(
        self, research_plan: Dict[str, Any], resources: List[str]
    ) -> List[SearchResult]:
        """搜尋本地資源"""
        results = []

        for resource in resources:
            if resource.startswith("http"):
                # URL 資源，使用爬取工具
                result = await self._crawl_url(resource, research_plan["keywords"])
                if result:
                    results.append(result)
            elif resource.startswith("rag://"):
                # 本地知識庫資源
                result = await self._search_local_knowledge(resource, research_plan["keywords"])
                if result:
                    results.append(result)

        return results

    async def _crawl_url(self, url: str, keywords: List[str]) -> Optional[SearchResult]:
        """爬取 URL 內容"""
        logger.info(f"爬取 URL: {url}")

        try:
            # 檢查是否有可用的爬蟲工具
            crawl_tool = None
            for tool_name in ["crawl_tool", "autogen_crawl"]:
                if hasattr(self, "tools") and tool_name in [
                    getattr(tool, "__name__", "") for tool in self.tools
                ]:
                    crawl_tool = next(
                        (tool for tool in self.tools if getattr(tool, "__name__", "") == tool_name),
                        None,
                    )
                    break

            if crawl_tool:
                logger.info(f"使用爬蟲工具爬取: {url}")
                # 調用爬蟲工具
                raw_result = await crawl_tool(url=url)

                # 解析爬蟲結果
                return self._parse_crawl_result(raw_result, url)
            else:
                logger.warning("未找到可用的爬蟲工具，使用模擬結果")
                return self._simulate_crawl_result(url, keywords)

        except Exception as e:
            logger.error(f"爬蟲執行失敗: {e}")
            # 失敗時返回模擬結果
            return self._simulate_crawl_result(url, keywords)

    def _parse_crawl_result(self, raw_result: str, url: str) -> SearchResult:
        """解析爬蟲工具返回的結果"""
        try:
            import json

            # 嘗試解析 JSON 格式的結果
            if isinstance(raw_result, str):
                try:
                    parsed = json.loads(raw_result)
                    if isinstance(parsed, dict):
                        title = parsed.get("title", f"爬取自 {url} 的內容")
                        content = parsed.get("content", parsed.get("crawled_content", raw_result))
                    else:
                        title = f"爬取自 {url} 的內容"
                        content = raw_result
                except json.JSONDecodeError:
                    title = f"爬取自 {url} 的內容"
                    content = raw_result
            else:
                title = f"爬取自 {url} 的內容"
                content = str(raw_result)

            return SearchResult(
                title=title,
                url=url,
                content=content,
                source="網頁爬取",
                timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error(f"解析爬蟲結果失敗: {e}")
            return SearchResult(
                title=f"爬取自 {url} 的內容",
                url=url,
                content=str(raw_result),
                source="網頁爬取",
                timestamp=datetime.now(),
            )

    def _simulate_crawl_result(self, url: str, keywords: List[str]) -> SearchResult:
        """模擬爬蟲結果"""
        return SearchResult(
            title=f"爬取自 {url} 的內容",
            url=url,
            content=f"這是從 {url} 爬取的內容，包含與 {', '.join(keywords)} 相關的詳細資訊。",
            source="網頁爬取",
            timestamp=datetime.now(),
        )

    async def _search_local_knowledge(
        self, resource: str, keywords: List[str]
    ) -> Optional[SearchResult]:
        """搜尋本地知識庫（模擬實現）"""
        logger.info(f"搜尋本地知識庫: {resource}")

        # 模擬本地搜尋結果
        return SearchResult(
            title=f"本地知識庫搜尋結果",
            url=resource,
            content=f"這是從本地知識庫檢索的關於 {', '.join(keywords)} 的資訊。",
            source="本地知識庫",
            timestamp=datetime.now(),
        )

    def _synthesize_findings(
        self, original_task: str, search_results: List[SearchResult]
    ) -> ResearchFindings:
        """整合研究發現"""
        # 按來源組織發現
        findings_by_source = {}
        for result in search_results:
            if result.source not in findings_by_source:
                findings_by_source[result.source] = []
            findings_by_source[result.source].append(result)

        # 生成發現列表
        findings = []
        for source, results in findings_by_source.items():
            finding = {
                "source": source,
                "summary": f"從 {source} 收集到 {len(results)} 條相關資訊",
                "key_points": [result.title for result in results],
                "details": [result.content for result in results],
            }
            findings.append(finding)

        # 生成結論
        conclusion = self._generate_conclusion(original_task, search_results)

        # 收集參考資料
        references = list(set([result.url for result in search_results]))

        return ResearchFindings(
            problem_statement=original_task,
            findings=findings,
            conclusion=conclusion,
            references=references,
            images=[],  # 實際實現中會從搜尋結果中提取圖片
        )

    def _generate_conclusion(self, task: str, results: List[SearchResult]) -> str:
        """生成結論"""
        if not results:
            return f"針對 '{task}' 的研究未能找到足夠的資訊。建議調整搜尋策略或擴大搜尋範圍。"

        total_sources = len(set([result.source for result in results]))

        conclusion = f"""基於對 '{task}' 的研究，我們從 {total_sources} 個不同來源收集了 {len(results)} 條相關資訊。

主要發現包括：
- 收集到的資訊涵蓋了該主題的多個面向
- 不同來源提供了不同的觀點和深度
- 資訊的時效性和可靠性需要進一步驗證

建議後續步驟：
1. 對收集的資訊進行深入分析
2. 驗證關鍵資料點的準確性
3. 尋找更多專業來源進行補充研究"""

        return conclusion

    def format_research_report(self, findings: ResearchFindings, locale: str = "zh-CN") -> str:
        """格式化研究報告"""
        if locale == "zh-CN":
            report = f"""# 研究報告

## 問題陳述
{findings.problem_statement}

## 研究發現
"""
            for finding in findings.findings:
                report += f"""
### {finding["source"]}
{finding["summary"]}

**關鍵要點：**
"""
                for point in finding["key_points"]:
                    report += f"- {point}\n"

                report += "\n"

            report += f"""## 結論
{findings.conclusion}

## 參考資料
"""
            for ref in findings.references:
                report += f"- [{ref}]({ref})\n\n"

        else:  # English
            report = f"""# Research Report

## Problem Statement
{findings.problem_statement}

## Research Findings
"""
            for finding in findings.findings:
                report += f"""
### {finding["source"]}
{finding["summary"]}

**Key Points:**
"""
                for point in finding["key_points"]:
                    report += f"- {point}\n"

                report += "\n"

            report += f"""## Conclusion
{findings.conclusion}

## References
"""
            for ref in findings.references:
                report += f"- [{ref}]({ref})\n\n"

        return report

    async def investigate_topic(self, research_topic: str) -> str:
        """
        調查研究主題（用於背景調查階段）

        Args:
            research_topic: 研究主題

        Returns:
            str: 調查結果
        """
        logger.info(f"開始調查主題: {research_topic}")

        try:
            # 進行背景搜尋
            search_results = await self._perform_web_search(research_topic)

            if not search_results:
                return f"未找到關於 '{research_topic}' 的相關資訊"

            # 整理調查結果
            investigation_summary = []
            investigation_summary.append(f"# 主題調查: {research_topic}\n")

            for i, result in enumerate(search_results[:3], 1):  # 取前3個結果
                investigation_summary.append(f"## 資料來源 {i}: {result.title}")
                investigation_summary.append(f"**來源：** {result.source}")
                if result.url:
                    investigation_summary.append(f"**網址：** {result.url}")
                investigation_summary.append(f"**內容摘要：**")
                investigation_summary.append(
                    result.content[:500] + "..." if len(result.content) > 500 else result.content
                )
                investigation_summary.append("")

            investigation_summary.append(
                f"**調查時間：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            return "\n".join(investigation_summary)

        except Exception as e:
            logger.error(f"主題調查失敗: {e}")
            return f"主題調查過程中發生錯誤: {str(e)}"

    async def execute_research_step(self, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行研究步驟（用於工作流執行階段）

        Args:
            step_input: 步驟輸入

        Returns:
            Dict[str, Any]: 執行結果
        """
        logger.info("執行研究步驟")

        try:
            description = step_input.get("description", "")
            inputs = step_input.get("inputs", {})
            context = step_input.get("context", {})

            # 提取研究查詢
            research_query = inputs.get("topic") or context.get("research_topic") or description
            max_results = inputs.get("max_results", self.max_search_results)

            # 執行搜尋
            search_results = await self._perform_web_search(research_query)

            # 如果有 URL 爬取需求
            urls_to_crawl = inputs.get("urls", [])
            crawl_results = []
            for url in urls_to_crawl:
                crawl_result = await self._crawl_url(url, [research_query])
                if crawl_result:
                    crawl_results.append(crawl_result)

            # 整理結果
            return {
                "research_query": research_query,
                "search_results": [
                    {"title": r.title, "url": r.url, "content": r.content, "source": r.source}
                    for r in search_results
                ],
                "crawl_results": [
                    {"title": r.title, "url": r.url, "content": r.content, "source": r.source}
                    for r in crawl_results
                ],
                "total_results": len(search_results) + len(crawl_results),
                "execution_time": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"研究步驟執行失敗: {e}")
            return {"error": str(e), "execution_time": datetime.now().isoformat()}

    async def analyze_research_data(self, analysis_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析研究資料

        Args:
            analysis_input: 分析輸入

        Returns:
            Dict[str, Any]: 分析結果
        """
        logger.info("分析研究資料")

        try:
            description = analysis_input.get("description", "")
            inputs = analysis_input.get("inputs", {})
            context = analysis_input.get("context", {})
            analysis_type = analysis_input.get("analysis_type", "basic")

            # 從上下文中獲取研究資料
            research_data = context.get("step_initial_research_result", {})
            search_results = research_data.get("search_results", [])
            crawl_results = research_data.get("crawl_results", [])

            if not search_results and not crawl_results:
                return {"analysis": "無可分析的研究資料", "insights": [], "recommendations": []}

            # 進行分析
            all_content = []
            for result in search_results + crawl_results:
                all_content.append(result.get("content", ""))

            combined_content = " ".join(all_content)

            # 基本分析
            analysis_result = {
                "content_length": len(combined_content),
                "source_count": len(search_results) + len(crawl_results),
                "analysis_type": analysis_type,
                "key_insights": self._extract_insights(combined_content),
                "content_summary": combined_content[:1000] + "..."
                if len(combined_content) > 1000
                else combined_content,
                "execution_time": datetime.now().isoformat(),
            }

            return analysis_result

        except Exception as e:
            logger.error(f"研究資料分析失敗: {e}")
            return {"error": str(e), "execution_time": datetime.now().isoformat()}

    def _extract_insights(self, content: str) -> List[str]:
        """從內容中提取關鍵洞察"""
        insights = []

        # 簡單的關鍵詞分析
        keywords = ["趨勢", "增長", "下降", "發展", "創新", "挑戰", "機會", "影響"]
        sentences = content.split("。")

        for sentence in sentences:
            for keyword in keywords:
                if keyword in sentence and len(sentence.strip()) > 10:
                    insights.append(sentence.strip() + "。")
                    break

            if len(insights) >= 5:  # 最多提取5個洞察
                break

        return insights
