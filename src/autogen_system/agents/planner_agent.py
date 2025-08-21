# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
計劃者智能體

負責分析研究需求並制定詳細的執行計劃。
基於原有的 planner_node 實現。
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from .base_agent import BaseResearchAgent, AssistantResearchAgent
from ..config.agent_config import AgentConfig, AgentRole
from src.logging import get_logger
from src.llms.llm import get_llm_by_type
from langchain.schema import HumanMessage, SystemMessage
from src.config.agents import AGENT_LLM_MAP

logger = get_logger(__name__)


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


class PlannerAgent(AssistantResearchAgent):
    """
    計劃者智能體

    角色職責：
    1. 分析研究需求的深度和廣度
    2. 評估是否有足夠的上下文資訊
    3. 制定詳細的執行計劃
    4. 分解任務為具體的研究和處理步驟
    5. 決定每個步驟是否需要網路搜尋
    """

    # 提示模板（基於原有的 planner.md）
    SYSTEM_MESSAGE = """你是一位專業的深度研究員。研究和規劃使用專業智能體團隊收集全面資料的資訊收集任務。

# 詳細說明

你的任務是協調研究團隊為給定需求收集全面資訊。最終目標是產生一份詳盡的詳細報告，因此收集多面向的豐富資訊是關鍵。資訊不足或有限將導致最終報告不夠完善。

作為深度研究員，你可以將主要主題分解為子主題，並在適用時擴展用戶初始問題的深度廣度。

## 資訊數量和品質標準

成功的研究計劃必須滿足這些標準：

1. **全面覆蓋**：
   - 資訊必須涵蓋主題的所有面向
   - 必須呈現多重觀點
   - 應包括主流和替代觀點

2. **足夠深度**：
   - 表面資訊是不夠的
   - 需要詳細的資料點、事實、統計數據
   - 需要來自多個來源的深入分析

3. **充足數量**：
   - 收集"剛好夠用"的資訊是不可接受的
   - 目標是豐富的相關資訊
   - 更多高品質的資訊總比較少的要好

## 上下文評估

在創建詳細計劃之前，評估是否有足夠的上下文來回答用戶的問題。對於判定足夠上下文應用嚴格標準：

1. **足夠上下文**（應用非常嚴格的標準）：
   - 只有在滿足所有以下條件時才設定 `has_enough_context` 為 true：
     - 當前資訊完全回答用戶問題的所有面向，有具體細節
     - 資訊全面、最新，來自可靠來源
     - 在可用資訊中沒有重大差距、模糊或矛盾
     - 資料點有可信證據或來源支持
     - 資訊涵蓋事實資料和必要上下文
     - 資訊量足以撰寫全面報告
   - 即使你90%確定資訊足夠，也要選擇收集更多資訊

2. **上下文不足**（預設假設）：
   - 如果存在以下任何條件，設定 `has_enough_context` 為 false：
     - 問題的某些面向仍然部分或完全未回答
     - 可用資訊過時、不完整或來源可疑
     - 缺少關鍵資料點、統計數據或證據
     - 缺乏替代觀點或重要上下文
     - 對資訊完整性存在任何合理懷疑
     - 資訊量對於全面報告來說太有限
   - 有疑問時，總是傾向於收集更多資訊

## 步驟類型和網路搜尋

不同類型的步驟有不同的網路搜尋需求：

1. **研究步驟** (`need_search: true`)：
   - 從用戶指定的 `rag://` 或 `http://` 前綴的URL檔案中檢索資訊
   - 收集市場資料或行業趨勢
   - 尋找歷史資訊
   - 收集競爭對手分析
   - 研究時事或新聞
   - 尋找統計資料或報告

2. **資料處理步驟** (`need_search: false`)：
   - API呼叫和資料提取
   - 資料庫查詢
   - 從現有來源收集原始資料
   - 數學計算和分析
   - 統計計算和資料處理

## 排除項目

- **研究步驟中不直接計算**：
  - 研究步驟應只收集資料和資訊
  - 所有數學計算必須由處理步驟處理
  - 數值分析必須委託給處理步驟
  - 研究步驟專注於資訊收集

## 分析框架

在規劃資訊收集時，考慮這些關鍵面向並確保全面覆蓋：

1. **歷史背景**：需要什麼歷史資料和趨勢？
2. **現狀**：需要收集什麼當前資料點？
3. **未來指標**：需要什麼預測資料或面向未來的資訊？
4. **利害關係人資料**：需要什麼所有相關利害關係人的資訊？
5. **量化資料**：應該收集什麼全面的數字、統計和指標？
6. **定性資料**：需要收集什麼非數值資訊？
7. **比較資料**：需要什麼比較點或基準資料？
8. **風險資料**：應該收集什麼所有潛在風險的資訊？

# 執行規則

- 首先，用你自己的話重複用戶的需求作為 `thought`
- 嚴格評估是否有足夠的上下文來回答問題
- 如果上下文足夠：設定 `has_enough_context` 為 true，不需要創建資訊收集步驟
- 如果上下文不足（預設假設）：
  - 使用分析框架分解所需資訊
  - 創建不超過3個專注且全面的步驟，涵蓋最重要的面向
  - 確保每個步驟實質且涵蓋相關資訊類別
  - 在3步驟限制內優先考慮廣度和深度
  - 對每個步驟，仔細評估是否需要網路搜尋
- 在步驟的 `description` 中指定要收集的確切資料
- 優先考慮相關資訊的深度和數量 - 有限的資訊是不可接受的
- 使用與用戶相同的語言生成計劃
- 不包括總結或整合收集資訊的步驟

# 輸出格式

直接輸出 `Plan` 的原始JSON格式，不要使用 "```json"。`Plan` 介面定義如下：

```ts
interface Step {
  need_search: boolean; // 每個步驟必須明確設定
  title: string;
  description: string; // 指定要收集的確切資料。如果用戶輸入包含連結，請在必要時保留完整的Markdown格式。
  step_type: "research" | "processing"; // 表示步驟的性質
}

interface Plan {
  locale: string; // 例如 "en-US" 或 "zh-CN"，基於用戶的語言或特定請求
  has_enough_context: boolean;
  thought: string;
  title: string;
  steps: Step[]; // 研究和處理步驟以獲得更多上下文
}
```

# 注意事項

- 專注於研究步驟中的資訊收集 - 將所有計算委託給處理步驟
- 確保每個步驟都有明確、具體的資料點或資訊要收集
- 創建一個在3個步驟內涵蓋最關鍵面向的全面資料收集計劃
- 優先考慮廣度（涵蓋重要面向）和深度（每個面向的詳細資訊）
- 永不滿足於最低限度的資訊 - 目標是全面、詳細的最終報告
- 有限或不足的資訊將導致不完善的最終報告
- 根據步驟性質仔細評估每個步驟的網路搜尋需求
- 除非滿足最嚴格的足夠上下文標準，否則預設收集更多資訊"""

    def __init__(self, config: AgentConfig, **kwargs):
        """初始化計劃者智能體"""
        config.system_message = self.SYSTEM_MESSAGE

        super().__init__(config, **kwargs)

        # 設定計劃相關的參數
        self.max_step_num = 3
        self.locale = "zh-CN"

        logger.info(f"計劃者智能體初始化完成: {config.name}")

    def set_parameters(self, max_step_num: int = 3, locale: str = "zh-CN"):
        """設定計劃參數"""
        self.max_step_num = max_step_num
        self.locale = locale
        logger.info(f"計劃參數更新: max_step_num={max_step_num}, locale={locale}")

    async def create_research_plan(
        self,
        research_topic: str,
        locale: str = "zh-CN",
        background_context: str = None,
        max_step_num: int = 3,
    ) -> ResearchPlan:
        """
        創建研究計劃

        Args:
            research_topic: 研究主題
            locale: 語言環境
            background_context: 背景上下文（可選）
            max_step_num: 最大步驟數

        Returns:
            ResearchPlan: 研究計劃
        """
        logger.info(f"開始創建研究計劃: {research_topic}")

        # 更新參數
        self.set_parameters(max_step_num, locale)

        # 構建提示
        prompt = self._build_planning_prompt(research_topic, background_context)

        try:
            # 調用真正的 LLM API 生成研究計劃
            plan_json = await self._generate_planning_response(prompt, research_topic, locale)
        except Exception as e:
            logger.warning(f"LLM API 調用失敗，使用預設計劃: {e}")
            # 降級到預設計劃
            plan_json = await self._simulate_planning_response(research_topic, locale)

        # 解析計劃
        plan = self._parse_plan_json(plan_json)

        logger.info(f"研究計劃創建完成: {plan.title}")
        return plan

    def _build_planning_prompt(self, research_topic: str, background_context: str = None) -> str:
        """構建計劃提示"""
        prompt = f"研究主題: {research_topic}\n"

        if background_context:
            prompt += f"背景資訊: {background_context}\n"

        prompt += f"""
請為此研究主題創建詳細的執行計劃。

參數:
- 最大步驟數: {self.max_step_num}
- 語言環境: {self.locale}

請按照系統訊息中的指示，評估上下文充足性並創建計劃。
"""
        return prompt

    async def _generate_planning_response(
        self, prompt: str, research_topic: str, locale: str
    ) -> str:
        """使用 LLM API 生成計劃響應"""
        logger.info(f"使用 LLM API 生成研究計劃: {research_topic}")

        try:
            # 使用 AGENT_LLM_MAP 中定義的計劃者 LLM 類型
            llm_type = AGENT_LLM_MAP["planner"]
            llm = get_llm_by_type(llm_type)

            # 構建訊息格式
            messages = [SystemMessage(content=self.SYSTEM_MESSAGE), HumanMessage(content=prompt)]

            # 調用 LLM
            logger.info(f"正在調用 {llm_type} LLM API 生成研究計劃...")
            response = llm.invoke(messages)

            # 提取回應內容
            planning_response = response.content.strip()
            logger.info(f"{llm_type} LLM API 調用成功，已生成研究計劃")

            return planning_response

        except Exception as e:
            logger.error(f"LLM API 調用失敗: {e}")
            raise

    async def _simulate_planning_response(self, research_topic: str, locale: str) -> str:
        """模擬計劃響應（實際實現會調用 LLM）"""
        # 這裡提供一個基於規則的計劃生成模擬

        # 判斷是否是程式碼相關主題
        is_code_related = any(
            keyword in research_topic.lower()
            for keyword in ["程式", "程式碼", "code", "programming", "軟體", "software"]
        )

        steps = []

        # 始終需要背景研究
        steps.append(
            {
                "need_search": True,
                "title": f"收集{research_topic}的基礎資訊",
                "description": f"搜尋並收集關於{research_topic}的基本定義、發展歷史、主要特點和當前狀況",
                "step_type": "research",
            }
        )

        # 根據主題類型添加特定步驟
        if is_code_related:
            steps.append(
                {
                    "need_search": True,
                    "title": f"研究{research_topic}的技術實現和最佳實務",
                    "description": f"深入研究{research_topic}的技術細節、實現方法、常用工具和最佳實務案例",
                    "step_type": "research",
                }
            )

            steps.append(
                {
                    "need_search": False,
                    "title": f"分析和整理{research_topic}的技術要點",
                    "description": f"對收集的技術資訊進行分析，整理關鍵要點和實施建議",
                    "step_type": "processing",
                }
            )
        else:
            steps.append(
                {
                    "need_search": True,
                    "title": f"深入研究{research_topic}的應用和趨勢",
                    "description": f"收集{research_topic}的實際應用案例、市場趨勢和未來發展方向",
                    "step_type": "research",
                }
            )

            steps.append(
                {
                    "need_search": True,
                    "title": f"收集{research_topic}的專家觀點和分析",
                    "description": f"搜尋專家評論、學術研究和行業分析報告",
                    "step_type": "research",
                }
            )

        plan = {
            "locale": locale,
            "has_enough_context": False,  # 預設需要更多資訊
            "thought": f"用戶想要了解{research_topic}的相關資訊。這需要全面的研究來收集充足的資料。",
            "title": f"{research_topic}深度研究報告",
            "steps": steps[: self.max_step_num],  # 限制步驟數
        }

        return json.dumps(plan, ensure_ascii=False, indent=2)

    def _parse_plan_json(self, plan_json: str) -> ResearchPlan:
        """解析計劃 JSON"""
        try:
            plan_dict = json.loads(plan_json)

            steps = []
            for step_dict in plan_dict.get("steps", []):
                steps.append(
                    ResearchStep(
                        need_search=step_dict["need_search"],
                        title=step_dict["title"],
                        description=step_dict["description"],
                        step_type=step_dict["step_type"],
                    )
                )

            return ResearchPlan(
                locale=plan_dict["locale"],
                has_enough_context=plan_dict["has_enough_context"],
                thought=plan_dict["thought"],
                title=plan_dict["title"],
                steps=steps,
            )

        except Exception as e:
            logger.error(f"解析計劃 JSON 失敗: {e}")
            # 返回預設計劃
            return ResearchPlan(
                locale=self.locale,
                has_enough_context=False,
                thought="計劃解析失敗，使用預設計劃",
                title="研究計劃",
                steps=[
                    ResearchStep(
                        need_search=True,
                        title="基礎資訊收集",
                        description="收集基本資訊",
                        step_type="research",
                    )
                ],
            )

    def evaluate_plan_quality(self, plan: ResearchPlan) -> Dict[str, Any]:
        """評估計劃品質"""
        evaluation = {
            "total_steps": len(plan.steps),
            "research_steps": sum(1 for step in plan.steps if step.step_type == "research"),
            "processing_steps": sum(1 for step in plan.steps if step.step_type == "processing"),
            "search_required_steps": sum(1 for step in plan.steps if step.need_search),
            "has_enough_context": plan.has_enough_context,
            "quality_score": 0.0,
        }

        # 計算品質分數
        score = 0.0

        # 步驟數量適中
        if 2 <= evaluation["total_steps"] <= 3:
            score += 0.3

        # 有研究步驟
        if evaluation["research_steps"] > 0:
            score += 0.3

        # 有處理步驟
        if evaluation["processing_steps"] > 0:
            score += 0.2

        # 計劃思考清晰
        if len(plan.thought) > 10:
            score += 0.2

        evaluation["quality_score"] = score

        return evaluation

    def _generate_research_plan(self, research_topic: str, locale: str = "zh-TW") -> str:
        """生成研究計劃"""
        logger.info(f"生成研究計劃: {research_topic}")

        # 創建研究步驟
        steps = []

        steps.append(
            {
                "need_search": True,
                "title": f"收集{research_topic}的基礎資訊",
                "description": f"搜尋{research_topic}的基本概念、定義和背景資料",
                "step_type": "research",
            }
        )

        steps.append(
            {
                "need_search": True,
                "title": f"收集{research_topic}的最新發展",
                "description": f"搜尋{research_topic}的最新趨勢、技術進展和應用案例",
                "step_type": "research",
            }
        )

        steps.append(
            {
                "need_search": True,
                "title": f"收集{research_topic}的專家觀點",
                "description": f"搜尋專家評論、學術研究和行業分析報告",
                "step_type": "research",
            }
        )

        plan = {
            "locale": locale,
            "has_enough_context": False,  # 預設需要更多資訊
            "thought": f"用戶想要了解{research_topic}的相關資訊。這需要全面的研究來收集充足的資料。",
            "title": f"{research_topic}深度研究報告",
            "steps": steps,
        }

        return str(plan)
