# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 程式碼執行工具

提供安全的 Python 程式碼執行功能。
"""

import asyncio
import sys
import traceback
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

from langchain_experimental.utilities import PythonREPL
from src.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CodeExecutionResult:
    """程式碼執行結果"""

    code: str
    output: str
    error: Optional[str]
    execution_time: float
    success: bool
    timestamp: datetime


class AutoGenPythonExecutor:
    """
    AutoGen Python 程式碼執行器

    提供安全的 Python 程式碼執行功能，支援輸出捕獲和錯誤處理。
    """

    def __init__(self, timeout_seconds: int = 30):
        """
        初始化程式碼執行器

        Args:
            timeout_seconds: 程式碼執行超時時間（秒）
        """
        self.timeout_seconds = timeout_seconds
        self.repl = PythonREPL()
        self.execution_history: list[CodeExecutionResult] = []

        logger.info(f"AutoGen Python 執行器初始化完成，超時設定: {timeout_seconds}秒")

    async def execute_code(self, code: str) -> str:
        """
        執行 Python 程式碼

        Args:
            code: 要執行的 Python 程式碼

        Returns:
            str: 執行結果（JSON 格式）
        """
        if not isinstance(code, str):
            error_msg = f"程式碼必須是字串格式，收到: {type(code)}"
            logger.error(error_msg)
            return self._format_error_result(code, error_msg)

        logger.info("開始執行 Python 程式碼")
        start_time = time.time()

        try:
            # 在事件循環中執行程式碼
            result = await asyncio.wait_for(
                self._execute_code_async(code), timeout=self.timeout_seconds
            )

            execution_time = time.time() - start_time

            # 記錄執行歷史
            execution_result = CodeExecutionResult(
                code=code,
                output=result,
                error=None,
                execution_time=execution_time,
                success=True,
                timestamp=datetime.now(),
            )
            self.execution_history.append(execution_result)

            logger.info(f"程式碼執行成功，耗時: {execution_time:.2f}秒")
            return self._format_success_result(execution_result)

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            error_msg = f"程式碼執行超時（{self.timeout_seconds}秒）"
            logger.error(error_msg)
            return self._format_timeout_result(code, execution_time)

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"程式碼執行失敗: {str(e)}"
            logger.error(error_msg)

            # 記錄執行歷史
            execution_result = CodeExecutionResult(
                code=code,
                output="",
                error=str(e),
                execution_time=execution_time,
                success=False,
                timestamp=datetime.now(),
            )
            self.execution_history.append(execution_result)

            return self._format_error_result(code, error_msg, execution_time)

    async def _execute_code_async(self, code: str) -> str:
        """非同步執行程式碼"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_code_sync, code)

    def _execute_code_sync(self, code: str) -> str:
        """同步執行程式碼"""
        try:
            # 使用 PythonREPL 執行程式碼
            result = self.repl.run(code)
            return result if result else ""
        except Exception as e:
            # 如果 PythonREPL 失敗，嘗試直接執行
            return self._direct_execute(code)

    def _direct_execute(self, code: str) -> str:
        """直接執行程式碼（備用方法）"""
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        try:
            # 重定向標準輸出和錯誤輸出
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # 編譯並執行程式碼
                compiled_code = compile(code, "<string>", "exec")
                exec(compiled_code)

            # 獲取輸出
            output = stdout_capture.getvalue()
            error_output = stderr_capture.getvalue()

            if error_output:
                return f"錯誤: {error_output}"

            return output if output else "程式碼執行完成（無輸出）"

        except SyntaxError as e:
            return f"語法錯誤: {str(e)}"
        except Exception as e:
            error_details = traceback.format_exc()
            return f"執行錯誤: {str(e)}\n詳細錯誤:\n{error_details}"

    def _format_success_result(self, result: CodeExecutionResult) -> str:
        """格式化成功結果"""
        return f"""✅ 程式碼執行成功

**執行代碼:**
```python
{result.code}
```

**執行結果:**
```
{result.output}
```

**執行資訊:**
- 執行時間: {result.execution_time:.2f} 秒
- 執行時間戳: {result.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
"""

    def _format_error_result(self, code: str, error_msg: str, execution_time: float = 0) -> str:
        """格式化錯誤結果"""
        return f"""❌ 程式碼執行失敗

**執行代碼:**
```python
{code}
```

**錯誤訊息:**
```
{error_msg}
```

**執行資訊:**
- 執行時間: {execution_time:.2f} 秒
- 執行時間戳: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    def _format_timeout_result(self, code: str, execution_time: float) -> str:
        """格式化超時結果"""
        return f"""⏰ 程式碼執行超時

**執行代碼:**
```python
{code}
```

**超時資訊:**
- 設定超時: {self.timeout_seconds} 秒
- 實際執行時間: {execution_time:.2f} 秒
- 執行時間戳: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**建議:**
1. 檢查程式碼是否有無限循環
2. 優化算法效率
3. 分解複雜的計算任務
"""

    def get_execution_history(self) -> list[Dict[str, Any]]:
        """獲取執行歷史"""
        return [
            {
                "code": result.code[:100] + "..." if len(result.code) > 100 else result.code,
                "success": result.success,
                "execution_time": result.execution_time,
                "timestamp": result.timestamp.isoformat(),
                "has_error": result.error is not None,
            }
            for result in self.execution_history
        ]

    def clear_history(self):
        """清除執行歷史"""
        self.execution_history.clear()
        logger.info("程式碼執行歷史已清除")

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        if not self.execution_history:
            return {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "average_execution_time": 0,
                "total_execution_time": 0,
            }

        successful = sum(1 for r in self.execution_history if r.success)
        total_time = sum(r.execution_time for r in self.execution_history)

        return {
            "total_executions": len(self.execution_history),
            "successful_executions": successful,
            "failed_executions": len(self.execution_history) - successful,
            "success_rate": successful / len(self.execution_history) * 100,
            "average_execution_time": total_time / len(self.execution_history),
            "total_execution_time": total_time,
        }


class AutoGenCodeAnalyzer:
    """
    AutoGen 程式碼分析器

    提供程式碼靜態分析功能。
    """

    def __init__(self):
        """初始化程式碼分析器"""
        self.analysis_history: list[Dict[str, Any]] = []
        logger.info("AutoGen 程式碼分析器初始化完成")

    async def analyze_code(self, code: str) -> str:
        """
        分析程式碼

        Args:
            code: 要分析的程式碼

        Returns:
            str: 分析結果
        """
        logger.info("開始分析程式碼")

        try:
            analysis_result = {
                "code": code,
                "timestamp": datetime.now(),
                "lines": len(code.split("\n")),
                "chars": len(code),
                "has_imports": "import " in code,
                "has_functions": "def " in code,
                "has_classes": "class " in code,
                "has_loops": any(keyword in code for keyword in ["for ", "while "]),
                "has_conditions": any(keyword in code for keyword in ["if ", "elif ", "else:"]),
                "complexity_estimate": self._estimate_complexity(code),
            }

            self.analysis_history.append(analysis_result)

            return self._format_analysis_result(analysis_result)

        except Exception as e:
            error_msg = f"程式碼分析失敗: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _estimate_complexity(self, code: str) -> str:
        """估算程式碼複雜度"""
        lines = len(code.split("\n"))

        if lines <= 5:
            return "簡單"
        elif lines <= 20:
            return "中等"
        elif lines <= 50:
            return "複雜"
        else:
            return "非常複雜"

    def _format_analysis_result(self, result: Dict[str, Any]) -> str:
        """格式化分析結果"""
        return f"""📊 程式碼分析結果

**程式碼概覽:**
- 總行數: {result["lines"]}
- 總字元數: {result["chars"]}
- 複雜度估算: {result["complexity_estimate"]}

**語言特徵:**
- 包含 import 語句: {"✅" if result["has_imports"] else "❌"}
- 包含函數定義: {"✅" if result["has_functions"] else "❌"}
- 包含類別定義: {"✅" if result["has_classes"] else "❌"}
- 包含迴圈結構: {"✅" if result["has_loops"] else "❌"}
- 包含條件語句: {"✅" if result["has_conditions"] else "❌"}

**分析時間:** {result["timestamp"].strftime("%Y-%m-%d %H:%M:%S")}
"""


# 便利函數
async def execute_python_code(code: str) -> str:
    """執行 Python 程式碼"""
    executor = AutoGenPythonExecutor()
    return await executor.execute_code(code)


async def analyze_python_code(code: str) -> str:
    """分析 Python 程式碼"""
    analyzer = AutoGenCodeAnalyzer()
    return await analyzer.analyze_code(code)
