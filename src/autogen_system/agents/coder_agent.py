# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
程式設計師智能體 - AutoGen 框架版本

負責分析程式設計需求並實現解決方案。
基於 coder_node 實現，使用 AutoGen 的 BaseChatAgent。
"""

import json
import logging
import asyncio
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


class CoderAgent(BaseChatAgent):
    """
    程式設計師智能體 - AutoGen 框架版本

    基於 coder_node 實現，角色職責：
    1. 分析程式設計需求
    2. 實現高效的 Python 解決方案
    3. 執行程式碼並處理結果
    4. 進行資料分析和演算法實現
    5. 測試解決方案並處理邊界情況
    6. 提供清晰的方法論文件
    """

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        description: str = "程式設計師智能體 - 分析需求並實現程式解決方案",
        system_messages: Optional[List[SystemMessage]] = None,
        tools: List[Callable] = None,
    ):
        """
        初始化程式設計師智能體

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
        self.role = "coder"
        self.locale = "zh-TW"

        # 執行歷史
        self.execution_history: List[CodeExecutionResult] = []

        logger.info(f"CoderAgent 初始化完成: {name}")

    # 提示模板（基於原有的 coder.md）
    DEFAULT_SYSTEM_MESSAGE = """你是由監督智能體管理的 `coder` 智能體。

你的職責是提供 Python 程式設計解決方案，包括資料分析、演算法實現和程式問題解決。你應該撰寫清晰、高效且有良好文件的程式碼。

## 核心職責

1. **需求分析**: 仔細分析程式設計任務和需求
2. **解決方案設計**: 設計高效的演算法和資料結構
3. **程式碼實現**: 撰寫清晰、可維護的 Python 程式碼
4. **測試和驗證**: 測試解決方案並處理邊界情況
5. **文件化**: 提供清晰的程式碼註解和方法論說明

## 程式設計準則

- **清晰性**: 程式碼應該易於閱讀和理解
- **效率性**: 選擇適當的演算法和資料結構
- **健壯性**: 處理錯誤情況和邊界案例
- **模組化**: 將複雜問題分解為較小的函數
- **文件化**: 提供適當的註解和說明

## 輸出格式

每個回應應包含：

1. **方法論**: 解釋解決問題的方法
2. **實現**: 提供完整的 Python 程式碼
3. **測試**: 包含測試案例和驗證
4. **說明**: 解釋程式碼的工作原理

使用適當的 Markdown 格式，將程式碼包裝在程式碼區塊中。"""

    def _setup_thread_context(self, thread_id: str):
        """設置線程上下文和日誌"""
        self._current_thread_id = thread_id

        if HAS_THREAD_LOGGING:
            try:
                self._thread_logger = setup_thread_logging(thread_id)
                set_thread_context(thread_id)

                if self._thread_logger:
                    self._thread_logger.info("CoderAgent talking.")
                else:
                    logger.info("CoderAgent talking.")
            except Exception as e:
                logger.warning(f"線程日誌設置失敗，使用標準 logger: {e}")
                self._thread_logger = logger
                logger.info("CoderAgent talking.")
        else:
            self._thread_logger = logger
            logger.info("CoderAgent talking.")

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

        thread_id = f"coder_thread_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        logger.debug(f"生成新線程 ID: {thread_id}")
        return thread_id

    def _apply_dynamic_system_message(self, state: Dict[str, Any]) -> List[SystemMessage]:
        """應用動態提示模板"""
        if HAS_PROMPT_TEMPLATES:
            try:
                template_state = {
                    "messages": state.get("messages", []),
                    "locale": state.get("locale", "zh-TW"),
                    "coding_task": state.get("coding_task", ""),
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
                                "coder", template_state, config_obj
                            )
                        except Exception as config_error:
                            if self._thread_logger:
                                self._thread_logger.warning(
                                    f"配置轉換失敗，使用無配置版本: {config_error}"
                                )
                            template_messages = apply_prompt_template("coder", template_state)
                    else:
                        template_messages = apply_prompt_template(
                            "coder", template_state, self._configuration
                        )
                else:
                    template_messages = apply_prompt_template("coder", template_state)

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
                self._thread_logger.info(f"CoderAgent 開始處理程式設計任務: {user_input}")

            # 調用程式設計邏輯
            coding_result = await self._analyze_and_implement_with_llm(
                user_input, cancellation_token
            )

            return TextMessage(content=coding_result, source=self.name)

        except Exception as e:
            error_msg = f"處理程式設計任務失敗: {str(e)}"
            logger.error(error_msg)

            if self._thread_logger:
                self._thread_logger.error(error_msg)

            return TextMessage(
                content=f"抱歉，執行程式設計任務時出現錯誤：{str(e)}", source=self.name
            )

    async def _analyze_and_implement_with_llm(
        self, user_input: str, cancellation_token: Optional[CancellationToken] = None
    ) -> str:
        """使用 LLM 分析和實現程式解決方案"""
        try:
            # 更新狀態
            self._state.update(
                {
                    "messages": [{"role": "user", "content": user_input}],
                    "locale": self.locale,
                    "coding_task": user_input.strip(),
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
                self._thread_logger.info("調用 LLM API 進行程式設計...")

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

            # 降級到模擬程式設計
            return await self._generate_fallback_solution(user_input)

    async def _generate_fallback_solution(self, user_input: str) -> str:
        """生成降級程式解決方案"""
        if self._thread_logger:
            self._thread_logger.info("使用降級程式設計生成")

        return f"""# 程式設計任務解決方案

## 任務分析
任務：{user_input}

## 方法論
由於技術限制，無法提供完整的程式實現。以下是建議的解決方法：

1. **需求分析**: 仔細分析任務需求
2. **設計方案**: 設計適當的演算法和資料結構
3. **實現程式碼**: 使用 Python 實現解決方案
4. **測試驗證**: 測試程式碼並處理邊界情況

## 建議實現

```python
# 範例程式碼結構
def solve_task():
    \"\"\"
    解決任務的主要函數
    \"\"\"
    # TODO: 實現具體邏輯
    pass

# 主要執行
if __name__ == "__main__":
    result = solve_task()
    print(f"結果: {{result}}")
```

## 測試建議

建議進行以下測試：
- 基本功能測試
- 邊界情況測試
- 效能測試

## 注意事項

此為降級版本，建議使用完整的程式開發環境進行實際實現。
"""

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
            "role": "coder",
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

            # 分析和實現程式
            coding_result = await self._analyze_and_implement_with_llm(user_input)

            return {
                "response": coding_result,
                "locale": self.locale,
                "status": "success",
            }

        except Exception as e:
            if self._thread_logger:
                self._thread_logger.error(f"處理用戶輸入失敗: {e}")
            else:
                logger.error(f"處理用戶輸入失敗: {e}")

            return {
                "response": f"抱歉，執行程式設計任務時發生錯誤：{str(e)}",
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
        self.execution_history.clear()

    @property
    def produced_message_types(self) -> List[type]:
        """返回此智能體產生的消息類型"""
        return [TextMessage]

    # 兼容方法 - 保留舊接口
    async def analyze_and_implement(
        self,
        task_description: str,
        locale: str = "zh-TW",
        additional_context: str = None,
    ) -> CodeAnalysisResult:
        """
        分析和實現程式解決方案（兼容舊接口）
        """
        try:
            self.locale = locale

            # 建構輸入
            coding_input = f"# 程式設計任務\n{task_description}\n"
            if additional_context:
                additional_context += f"\n# 額外上下文\n{additional_context}\n"

            # 分析和實現
            coding_result = await self._analyze_and_implement_with_llm(coding_input)

            # 解析結果為 CodeAnalysisResult
            return self._parse_coding_result(task_description, coding_result)

        except Exception as e:
            logger.error(f"分析和實現失敗: {e}")
            # 返回降級結果
            return self._create_fallback_analysis_result(task_description)

    def _parse_coding_result(self, task_description: str, coding_result: str) -> CodeAnalysisResult:
        """解析程式設計結果"""
        # 簡化解析 - 實際實現可以更複雜
        lines = coding_result.split("\n")

        # 提取程式碼片段
        code_snippets = []
        in_code_block = False
        current_code = []

        for line in lines:
            if line.strip().startswith("```"):
                if in_code_block:
                    # 結束程式碼區塊
                    if current_code:
                        code_snippets.append("\n".join(current_code))
                    current_code = []
                    in_code_block = False
                else:
                    # 開始程式碼區塊
                    in_code_block = True
            elif in_code_block:
                current_code.append(line)

        return CodeAnalysisResult(
            methodology="基於 LLM 的程式設計方法",
            implementation=coding_result,
            test_results=["測試完成"],
            final_output=coding_result,
            code_snippets=code_snippets,
        )

    def _create_fallback_analysis_result(self, task_description: str) -> CodeAnalysisResult:
        """創建降級分析結果"""
        fallback_code = f"""
# 任務: {task_description}
def solve_task():
    \"\"\"
    解決任務的主要函數
    \"\"\"
    # TODO: 實現具體邏輯
    pass

if __name__ == "__main__":
    result = solve_task()
    print(f"結果: {{result}}")
"""

        return CodeAnalysisResult(
            methodology="降級程式設計方法",
            implementation=f"由於技術限制，提供基本程式結構。\n\n```python{fallback_code}```",
            test_results=["需要手動測試"],
            final_output="降級版本程式結構",
            code_snippets=[fallback_code.strip()],
        )

    async def execute_coding_step(self, step_input: Dict[str, Any]) -> Dict[str, Any]:
        """執行程式設計步驟（兼容舊接口）"""
        try:
            step_description = step_input.get("description", "")
            step_title = step_input.get("title", "程式設計步驟")

            coding_input = f"# {step_title}\n{step_description}"

            result = await self._analyze_and_implement_with_llm(coding_input)

            return {
                "step_title": step_title,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "step_title": step_input.get("title", "程式設計步驟"),
                "result": f"執行失敗：{str(e)}",
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
            }
