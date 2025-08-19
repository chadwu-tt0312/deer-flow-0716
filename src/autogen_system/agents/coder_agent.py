# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
程式設計師智能體

負責程式碼分析、實現和執行任務。
基於原有的 coder_node 實現。
"""

import ast
import sys
import traceback
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from io import StringIO

from .base_agent import BaseResearchAgent, AssistantResearchAgent
from ..config.agent_config import AgentConfig, AgentRole, CodeExecutionConfig
from src.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CodeExecutionResult:
    """程式碼執行結果"""

    code: str
    output: str
    error: Optional[str]
    execution_time: float
    timestamp: datetime
    success: bool


@dataclass
class CodeAnalysisResult:
    """程式碼分析結果"""

    methodology: str
    implementation: str
    test_results: List[str]
    final_output: str
    code_snippets: List[str]


class CoderAgent(AssistantResearchAgent):
    """
    程式設計師智能體

    角色職責：
    1. 分析程式設計需求
    2. 實現高效的 Python 解決方案
    3. 執行程式碼並處理結果
    4. 進行資料分析和演算法實現
    5. 測試解決方案並處理邊界情況
    6. 提供清晰的方法論文件
    """

    # 提示模板（基於原有的 coder.md）
    SYSTEM_MESSAGE = """你是由監督智能體管理的 `coder` 智能體。
你是一位精通 Python 腳本的專業軟體工程師。你的任務是分析需求、使用 Python 實現高效解決方案，並提供清晰的方法論和結果文件。

# 步驟

1. **分析需求**：仔細審查任務描述以了解目標、約束和預期結果
2. **規劃解決方案**：確定任務是否需要 Python。概述實現解決方案所需的步驟
3. **實現解決方案**：
   - 使用 Python 進行資料分析、演算法實現或問題解決
   - 在 Python 中使用 `print(...)` 印出結果以顯示結果或除錯值
4. **測試解決方案**：驗證實現以確保滿足需求並處理邊界情況
5. **記錄方法論**：清楚說明你的方法，包括選擇的理由和所做的任何假設
6. **呈現結果**：清楚顯示最終輸出和任何必要的中間結果

# 注意事項

- 始終確保解決方案高效並遵循最佳實務
- 優雅地處理邊界情況，如空檔案或缺少輸入
- 在程式碼中使用註解以提高可讀性和可維護性
- 如果你想看到某個值的輸出，你必須使用 `print(...)` 印出來
- 始終且僅使用 Python 進行數學運算
- 始終使用 `yfinance` 進行金融市場資料：
    - 使用 `yf.download()` 取得歷史資料
    - 使用 `Ticker` 物件存取公司資訊
    - 為資料檢索使用適當的日期範圍
- 必需的 Python 套件已預安裝：
    - `pandas` 用於資料操作
    - `numpy` 用於數值運算
    - `yfinance` 用於金融市場資料
- 始終以指定的語言環境輸出"""

    def __init__(self, config: AgentConfig, tools: List[Callable] = None, **kwargs):
        """初始化程式設計師智能體"""
        config.system_message = self.SYSTEM_MESSAGE

        # 設定程式碼執行配置
        if not config.code_execution_config:
            config.code_execution_config = CodeExecutionConfig(enabled=True)

        # 設定程式設計師專用的工具
        coder_tools = tools or []

        super().__init__(config, coder_tools, **kwargs)

        # 初始化程式碼執行環境
        self.execution_globals = {
            "__builtins__": __builtins__,
            "print": print,
            "len": len,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "sum": sum,
            "max": max,
            "min": min,
            "abs": abs,
            "round": round,
        }

        # 嘗試導入常用套件
        self._import_common_packages()

        # 程式碼執行歷史
        self.execution_history: List[CodeExecutionResult] = []

        logger.info(f"程式設計師智能體初始化完成: {config.name}")

    def _import_common_packages(self):
        """導入常用套件到執行環境"""
        common_packages = {
            "pandas": "pd",
            "numpy": "np",
            "yfinance": "yf",
            "datetime": "datetime",
            "json": "json",
            "math": "math",
            "os": "os",
            "sys": "sys",
            "re": "re",
        }

        for package, alias in common_packages.items():
            try:
                if alias:
                    exec(f"import {package} as {alias}", self.execution_globals)
                else:
                    exec(f"import {package}", self.execution_globals)
                logger.debug(f"成功導入套件: {package}")
            except ImportError:
                logger.warning(f"無法導入套件: {package}")

    async def analyze_and_implement(
        self, task_description: str, locale: str = "zh-CN", additional_context: str = None
    ) -> CodeAnalysisResult:
        """
        分析並實現程式設計任務

        Args:
            task_description: 任務描述
            locale: 語言環境
            additional_context: 額外上下文

        Returns:
            CodeAnalysisResult: 分析和實現結果
        """
        logger.info(f"開始分析程式設計任務: {task_description}")

        # 分析需求
        requirements = self._analyze_requirements(task_description)

        # 規劃解決方案
        solution_plan = self._plan_solution(requirements)

        # 實現解決方案
        implementation_result = await self._implement_solution(solution_plan)

        # 測試解決方案
        test_results = await self._test_solution(implementation_result)

        # 生成方法論文件
        methodology = self._document_methodology(requirements, solution_plan, implementation_result)

        result = CodeAnalysisResult(
            methodology=methodology,
            implementation=implementation_result.get("code", ""),
            test_results=test_results,
            final_output=implementation_result.get("output", ""),
            code_snippets=implementation_result.get("snippets", []),
        )

        logger.info("程式設計任務分析完成")
        return result

    def _analyze_requirements(self, task_description: str) -> Dict[str, Any]:
        """分析需求"""
        requirements = {
            "description": task_description,
            "task_type": self._classify_task_type(task_description),
            "required_inputs": self._identify_required_inputs(task_description),
            "expected_outputs": self._identify_expected_outputs(task_description),
            "constraints": self._identify_constraints(task_description),
            "complexity": self._assess_complexity(task_description),
        }

        logger.info(f"需求分析完成: {requirements['task_type']}")
        return requirements

    def _classify_task_type(self, description: str) -> str:
        """分類任務類型"""
        description_lower = description.lower()

        if any(
            word in description_lower
            for word in ["資料分析", "data analysis", "統計", "statistics"]
        ):
            return "data_analysis"
        elif any(word in description_lower for word in ["演算法", "algorithm", "排序", "搜尋"]):
            return "algorithm"
        elif any(word in description_lower for word in ["金融", "股票", "finance", "stock"]):
            return "financial"
        elif any(word in description_lower for word in ["爬蟲", "crawl", "網頁", "web"]):
            return "web_scraping"
        elif any(word in description_lower for word in ["計算", "math", "數學", "calculate"]):
            return "calculation"
        else:
            return "general"

    def _identify_required_inputs(self, description: str) -> List[str]:
        """識別所需輸入"""
        # 簡化的輸入識別邏輯
        inputs = []

        if "檔案" in description or "file" in description.lower():
            inputs.append("file_input")
        if "資料" in description or "data" in description.lower():
            inputs.append("data_input")
        if "參數" in description or "parameter" in description.lower():
            inputs.append("parameters")

        return inputs

    def _identify_expected_outputs(self, description: str) -> List[str]:
        """識別預期輸出"""
        outputs = []

        if "圖表" in description or "chart" in description.lower():
            outputs.append("chart")
        if "報告" in description or "report" in description.lower():
            outputs.append("report")
        if "結果" in description or "result" in description.lower():
            outputs.append("result")

        return outputs

    def _identify_constraints(self, description: str) -> List[str]:
        """識別約束條件"""
        constraints = []

        if "時間" in description or "time" in description.lower():
            constraints.append("time_constraint")
        if "記憶體" in description or "memory" in description.lower():
            constraints.append("memory_constraint")
        if "效能" in description or "performance" in description.lower():
            constraints.append("performance_constraint")

        return constraints

    def _assess_complexity(self, description: str) -> str:
        """評估複雜度"""
        if len(description) < 50:
            return "simple"
        elif len(description) < 200:
            return "medium"
        else:
            return "complex"

    def _plan_solution(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """規劃解決方案"""
        task_type = requirements["task_type"]

        if task_type == "data_analysis":
            steps = [
                "導入必要的資料分析套件",
                "載入和檢查資料",
                "進行資料清理和預處理",
                "執行分析和統計",
                "生成視覺化結果",
            ]
        elif task_type == "financial":
            steps = [
                "導入金融資料套件",
                "獲取金融資料",
                "進行資料處理和分析",
                "計算金融指標",
                "輸出分析結果",
            ]
        elif task_type == "algorithm":
            steps = ["定義演算法邏輯", "實現核心功能", "處理邊界情況", "測試演算法效能", "輸出結果"]
        else:
            steps = ["分析問題", "設計解決方案", "實現程式碼", "測試和驗證", "輸出結果"]

        return {
            "task_type": task_type,
            "steps": steps,
            "estimated_complexity": requirements["complexity"],
            "required_packages": self._determine_required_packages(task_type),
        }

    def _determine_required_packages(self, task_type: str) -> List[str]:
        """確定所需套件"""
        package_map = {
            "data_analysis": ["pandas", "numpy"],
            "financial": ["yfinance", "pandas", "numpy"],
            "algorithm": ["numpy"],
            "web_scraping": ["requests", "bs4"],
            "calculation": ["math", "numpy"],
            "general": ["pandas", "numpy"],
        }

        return package_map.get(task_type, ["pandas", "numpy"])

    async def _implement_solution(self, solution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """實現解決方案"""
        task_type = solution_plan["task_type"]

        # 根據任務類型生成範例程式碼
        if task_type == "financial":
            code = self._generate_financial_code()
        elif task_type == "data_analysis":
            code = self._generate_data_analysis_code()
        elif task_type == "algorithm":
            code = self._generate_algorithm_code()
        else:
            code = self._generate_general_code()

        # 執行程式碼
        execution_result = await self.execute_code(code)

        return {
            "code": code,
            "output": execution_result.output,
            "error": execution_result.error,
            "success": execution_result.success,
            "snippets": [code],  # 可以包含多個程式碼片段
        }

    def _generate_financial_code(self) -> str:
        """生成金融分析程式碼範例"""
        return """# 金融資料分析範例
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("開始金融資料分析...")

# 獲取股票資料
ticker = "AAPL"  # 蘋果股票
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

print(f"獲取 {ticker} 股票資料...")
stock_data = yf.download(ticker, start=start_date, end=end_date)

if not stock_data.empty:
    print(f"成功獲取 {len(stock_data)} 天的資料")
    
    # 計算基本統計
    current_price = stock_data['Close'].iloc[-1]
    avg_price = stock_data['Close'].mean()
    price_change = ((current_price - stock_data['Close'].iloc[0]) / stock_data['Close'].iloc[0]) * 100
    
    print(f"當前價格: ${current_price:.2f}")
    print(f"平均價格: ${avg_price:.2f}")
    print(f"年度變化: {price_change:.2f}%")
    
    # 計算移動平均
    stock_data['MA_20'] = stock_data['Close'].rolling(window=20).mean()
    stock_data['MA_50'] = stock_data['Close'].rolling(window=50).mean()
    
    print("移動平均計算完成")
    print(f"最近20日移動平均: ${stock_data['MA_20'].iloc[-1]:.2f}")
    print(f"最近50日移動平均: ${stock_data['MA_50'].iloc[-1]:.2f}")
else:
    print("無法獲取股票資料")

print("金融分析完成!")"""

    def _generate_data_analysis_code(self) -> str:
        """生成資料分析程式碼範例"""
        return """# 資料分析範例
import pandas as pd
import numpy as np

print("開始資料分析...")

# 創建範例資料
np.random.seed(42)
data = {
    'A': np.random.randn(100),
    'B': np.random.randn(100),
    'C': np.random.randint(1, 10, 100),
    'Category': np.random.choice(['X', 'Y', 'Z'], 100)
}

df = pd.DataFrame(data)
print(f"創建了包含 {len(df)} 行資料的 DataFrame")

# 基本統計
print("\\n基本統計資訊:")
print(df.describe())

# 分組分析
print("\\n按類別分組分析:")
grouped = df.groupby('Category').agg({
    'A': 'mean',
    'B': 'mean', 
    'C': 'sum'
})
print(grouped)

# 相關性分析
print("\\n相關性分析:")
correlation = df[['A', 'B', 'C']].corr()
print(correlation)

print("\\n資料分析完成!")"""

    def _generate_algorithm_code(self) -> str:
        """生成演算法程式碼範例"""
        return """# 演算法實現範例
import numpy as np

print("開始演算法實現...")

def quick_sort(arr):
    \"\"\"快速排序演算法\"\"\"
    if len(arr) <= 1:
        return arr
    
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    
    return quick_sort(left) + middle + quick_sort(right)

def binary_search(arr, target):
    \"\"\"二分搜尋演算法\"\"\"
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1

# 測試演算法
test_data = [64, 34, 25, 12, 22, 11, 90, 88, 76, 50]
print(f"原始資料: {test_data}")

sorted_data = quick_sort(test_data.copy())
print(f"排序後: {sorted_data}")

target = 22
index = binary_search(sorted_data, target)
print(f"搜尋 {target} 的位置: {index}")

print("演算法測試完成!")"""

    def _generate_general_code(self) -> str:
        """生成通用程式碼範例"""
        return """# 通用程式處理範例
import math

print("開始通用程式處理...")

# 基本數學計算
def calculate_statistics(numbers):
    \"\"\"計算基本統計量\"\"\"
    if not numbers:
        return {}
    
    return {
        'count': len(numbers),
        'sum': sum(numbers),
        'mean': sum(numbers) / len(numbers),
        'min': min(numbers),
        'max': max(numbers),
        'std': math.sqrt(sum((x - sum(numbers)/len(numbers))**2 for x in numbers) / len(numbers))
    }

# 範例資料
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
print(f"處理資料: {numbers}")

stats = calculate_statistics(numbers)
print("統計結果:")
for key, value in stats.items():
    print(f"  {key}: {value:.2f}" if isinstance(value, float) else f"  {key}: {value}")

print("通用程式處理完成!")"""

    async def execute_code(self, code: str) -> CodeExecutionResult:
        """執行程式碼"""
        start_time = datetime.now()

        # 首先嘗試使用AutoGen工具系統
        try:
            execution_result = await self._execute_with_autogen_tools(code)
            if execution_result:
                return execution_result
        except Exception as e:
            logger.warning(f"AutoGen工具執行失敗，回退到內建執行: {e}")

        # 回退到內建執行方式
        return await self._execute_with_builtin(code, start_time)

    async def _execute_with_autogen_tools(self, code: str) -> Optional[CodeExecutionResult]:
        """使用AutoGen工具執行程式碼"""
        # 檢查是否有可用的程式碼執行工具
        code_execution_tool = None
        for tool_name in ["python_repl_tool", "autogen_python_executor", "execute_python_code"]:
            if hasattr(self, "tools") and tool_name in [
                getattr(tool, "__name__", "") for tool in self.tools
            ]:
                code_execution_tool = next(
                    (tool for tool in self.tools if getattr(tool, "__name__", "") == tool_name),
                    None,
                )
                break

        if not code_execution_tool:
            return None

        logger.info(f"使用AutoGen工具執行程式碼: {code_execution_tool.__name__}")

        try:
            # 調用AutoGen程式碼執行工具
            raw_result = await code_execution_tool(code=code)

            # 解析執行結果
            return self._parse_execution_result(raw_result, code, datetime.now())

        except Exception as e:
            logger.error(f"AutoGen工具執行失敗: {e}")
            return None

    def _parse_execution_result(
        self, raw_result: str, code: str, start_time: datetime
    ) -> CodeExecutionResult:
        """解析AutoGen工具的執行結果"""
        execution_time = (datetime.now() - start_time).total_seconds()

        try:
            # 檢查結果是否包含成功/失敗指示
            if "✅" in raw_result or "成功" in raw_result or "Successfully executed" in raw_result:
                success = True
                error = None
            elif "❌" in raw_result or "失敗" in raw_result or "Error executing" in raw_result:
                success = False
                error = "程式碼執行失敗"
            else:
                # 預設為成功，除非明確包含錯誤資訊
                success = "Error" not in raw_result and "Exception" not in raw_result
                error = None if success else "程式碼執行可能失敗"

            # 提取輸出內容
            output = raw_result

            # 如果結果包含格式化的輸出，嘗試提取實際的執行輸出
            if "執行結果:" in raw_result:
                lines = raw_result.split("\n")
                in_output_section = False
                output_lines = []

                for line in lines:
                    if "執行結果:" in line or "Stdout:" in line:
                        in_output_section = True
                        continue
                    elif in_output_section and (
                        line.startswith("**") or line.startswith("## ") or line.startswith("---")
                    ):
                        break
                    elif in_output_section:
                        output_lines.append(line)

                if output_lines:
                    output = "\n".join(output_lines).strip()

            result = CodeExecutionResult(
                code=code,
                output=output,
                error=error,
                execution_time=execution_time,
                timestamp=start_time,
                success=success,
            )

            self.execution_history.append(result)

            if success:
                logger.info(f"AutoGen工具執行成功，耗時 {execution_time:.3f} 秒")
            else:
                logger.error(f"AutoGen工具執行失敗: {error}")

            return result

        except Exception as e:
            logger.error(f"解析執行結果失敗: {e}")
            # 返回基本結果
            result = CodeExecutionResult(
                code=code,
                output=str(raw_result),
                error=f"結果解析失敗: {str(e)}",
                execution_time=execution_time,
                timestamp=start_time,
                success=False,
            )
            self.execution_history.append(result)
            return result

    async def _execute_with_builtin(self, code: str, start_time: datetime) -> CodeExecutionResult:
        """使用內建方式執行程式碼"""
        # 創建字串緩衝區來捕獲輸出
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            # 執行程式碼
            exec(code, self.execution_globals)

            output = captured_output.getvalue()
            error = None
            success = True

        except Exception as e:
            output = captured_output.getvalue()
            error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            success = False

        finally:
            # 恢復標準輸出
            sys.stdout = old_stdout

        execution_time = (datetime.now() - start_time).total_seconds()

        result = CodeExecutionResult(
            code=code,
            output=output,
            error=error,
            execution_time=execution_time,
            timestamp=start_time,
            success=success,
        )

        self.execution_history.append(result)

        if success:
            logger.info(f"內建執行成功，耗時 {execution_time:.3f} 秒")
        else:
            logger.error(f"內建執行失敗: {error}")

        return result

    async def _test_solution(self, implementation_result: Dict[str, Any]) -> List[str]:
        """測試解決方案"""
        test_results = []

        if implementation_result["success"]:
            test_results.append("✅ 程式碼執行成功")

            if implementation_result["output"]:
                test_results.append(f"✅ 產生輸出: {len(implementation_result['output'])} 字元")
            else:
                test_results.append("⚠️ 沒有產生輸出")

        else:
            test_results.append("❌ 程式碼執行失敗")
            if implementation_result["error"]:
                test_results.append(f"❌ 錯誤: {implementation_result['error'][:100]}...")

        # 檢查程式碼品質
        code_quality_issues = self._check_code_quality(implementation_result["code"])
        test_results.extend(code_quality_issues)

        return test_results

    def _check_code_quality(self, code: str) -> List[str]:
        """檢查程式碼品質"""
        issues = []

        try:
            # 檢查語法
            ast.parse(code)
            issues.append("✅ 語法檢查通過")
        except SyntaxError:
            issues.append("❌ 語法錯誤")

        # 檢查是否有print語句
        if "print(" in code:
            issues.append("✅ 包含輸出語句")
        else:
            issues.append("⚠️ 缺少輸出語句")

        # 檢查是否有註解
        comment_lines = [line for line in code.split("\n") if line.strip().startswith("#")]
        if comment_lines:
            issues.append(f"✅ 包含 {len(comment_lines)} 行註解")
        else:
            issues.append("⚠️ 缺少註解")

        return issues

    def _document_methodology(
        self,
        requirements: Dict[str, Any],
        solution_plan: Dict[str, Any],
        implementation_result: Dict[str, Any],
    ) -> str:
        """記錄方法論"""
        methodology = f"""# 程式設計方法論

## 需求分析
- **任務類型**: {requirements["task_type"]}
- **複雜度**: {requirements["complexity"]}
- **所需輸入**: {", ".join(requirements["required_inputs"]) if requirements["required_inputs"] else "無"}
- **預期輸出**: {", ".join(requirements["expected_outputs"]) if requirements["expected_outputs"] else "無"}

## 解決方案設計
- **預估複雜度**: {solution_plan["estimated_complexity"]}
- **所需套件**: {", ".join(solution_plan["required_packages"])}

## 實現步驟
"""
        for i, step in enumerate(solution_plan["steps"], 1):
            methodology += f"{i}. {step}\n"

        methodology += f"""
## 執行結果
- **執行狀態**: {"成功" if implementation_result["success"] else "失敗"}
- **輸出長度**: {len(implementation_result["output"]) if implementation_result["output"] else 0} 字元
"""

        if implementation_result["error"]:
            methodology += f"- **錯誤資訊**: {implementation_result['error'][:200]}...\n"

        return methodology

    def get_execution_summary(self) -> Dict[str, Any]:
        """取得執行摘要"""
        if not self.execution_history:
            return {"total_executions": 0}

        successful_executions = sum(1 for result in self.execution_history if result.success)
        total_time = sum(result.execution_time for result in self.execution_history)

        return {
            "total_executions": len(self.execution_history),
            "successful_executions": successful_executions,
            "success_rate": successful_executions / len(self.execution_history),
            "total_execution_time": total_time,
            "average_execution_time": total_time / len(self.execution_history),
        }

    async def execute_coding_step(self, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行編程步驟（用於工作流執行階段）

        Args:
            step_input: 步驟輸入

        Returns:
            Dict[str, Any]: 執行結果
        """
        logger.info("執行編程步驟")

        try:
            description = step_input.get("description", "")
            inputs = step_input.get("inputs", {})
            context = step_input.get("context", {})

            # 根據描述和上下文生成程式碼任務
            task_description = description or inputs.get("task", "通用程式碼任務")

            # 從上下文中獲取研究資料（如果有的話）
            research_data = context.get("step_initial_research_result", {})
            analysis_data = context.get("step_deep_analysis_result", {})

            # 建立編程需求
            requirements = {
                "task_description": task_description,
                "has_research_data": bool(research_data),
                "has_analysis_data": bool(analysis_data),
                "context_keys": list(context.keys()),
            }

            # 執行程式碼分析
            code_analysis = await self.analyze_programming_task(requirements)

            # 如果分析建議需要程式碼執行
            if code_analysis.code_snippets:
                execution_results = []
                for code in code_analysis.code_snippets:
                    exec_result = await self.execute_code(code)
                    execution_results.append(
                        {
                            "code": code,
                            "output": exec_result.output,
                            "success": exec_result.success,
                            "error": exec_result.error,
                        }
                    )

                return {
                    "task_description": task_description,
                    "analysis": code_analysis,
                    "execution_results": execution_results,
                    "total_executions": len(execution_results),
                    "successful_executions": sum(1 for r in execution_results if r["success"]),
                    "execution_time": datetime.now().isoformat(),
                }
            else:
                return {
                    "task_description": task_description,
                    "analysis": code_analysis,
                    "execution_results": [],
                    "message": "分析完成，但無需執行程式碼",
                    "execution_time": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"編程步驟執行失敗: {e}")
            return {"error": str(e), "execution_time": datetime.now().isoformat()}

    async def process_data(self, processing_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        處理資料（用於資料處理步驟）

        Args:
            processing_input: 處理輸入

        Returns:
            Dict[str, Any]: 處理結果
        """
        logger.info("執行資料處理")

        try:
            description = processing_input.get("description", "")
            inputs = processing_input.get("inputs", {})
            context = processing_input.get("context", {})
            processing_type = processing_input.get("processing_type", "data_analysis")

            # 從上下文中獲取資料
            available_data = {}
            for key, value in context.items():
                if "result" in key and isinstance(value, dict):
                    available_data[key] = value

            if not available_data:
                return {
                    "processing_type": processing_type,
                    "message": "無可處理的資料",
                    "data_summary": {},
                }

            # 生成資料處理程式碼
            data_processing_code = self._generate_data_processing_code(
                available_data, processing_type
            )

            # 執行資料處理
            exec_result = await self.execute_code(data_processing_code)

            return {
                "processing_type": processing_type,
                "data_sources": list(available_data.keys()),
                "processing_code": data_processing_code,
                "execution_result": {
                    "output": exec_result.output,
                    "success": exec_result.success,
                    "error": exec_result.error,
                },
                "execution_time": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"資料處理失敗: {e}")
            return {"error": str(e), "execution_time": datetime.now().isoformat()}

    def _generate_data_processing_code(self, data: Dict[str, Any], processing_type: str) -> str:
        """生成資料處理程式碼"""

        if processing_type == "data_analysis":
            return f"""
# 資料分析程式碼
import json

# 可用資料源
data_sources = {list(data.keys())}
print(f"可用資料源: {{data_sources}}")

# 資料統計
total_data_size = 0
for source in data_sources:
    print(f"\\n資料源: {{source}}")
    # 這裡會是實際的資料分析邏輯
    print("  - 資料分析已完成")
    total_data_size += 1

print(f"\\n總計處理了 {{total_data_size}} 個資料源")
print("資料處理完成！")
"""

        elif processing_type == "statistical_summary":
            return f"""
# 統計摘要程式碼
print("執行統計摘要分析...")

# 模擬統計分析
data_points = {len(data)}
print(f"分析了 {{data_points}} 個資料點")

# 基本統計
print("統計摘要:")
print("- 平均值: 計算中...")
print("- 中位數: 計算中...")
print("- 標準差: 計算中...")

print("統計分析完成！")
"""

        else:
            return f"""
# 通用資料處理程式碼
print("執行通用資料處理...")

# 處理可用資料
available_data = {list(data.keys())}
for data_source in available_data:
    print(f"處理資料源: {{data_source}}")

print("資料處理完成！")
"""
