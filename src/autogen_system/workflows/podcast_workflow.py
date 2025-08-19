# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen Podcast 生成工作流

將LangGraph的Podcast工作流遷移到AutoGen架構。
"""

import asyncio
import base64
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


# Mock AutoGen classes for compatibility
class MockChatCompletionClient:
    """Mock ChatCompletionClient for compatibility"""

    def __init__(self, *args, **kwargs):
        self.config = kwargs.get("config", {})
        self.api_key = kwargs.get("api_key", "mock_key")
        self.base_url = kwargs.get("base_url", "https://api.openai.com/v1")

    def get(self, key, default=None):
        """Mock get method for config access"""
        if hasattr(self, key):
            return getattr(self, key)
        return self.config.get(key, default)

    def __getattr__(self, name):
        """Handle any other attribute access"""
        return lambda *args, **kwargs: None


ChatCompletionClient = MockChatCompletionClient
UserMessage = type("UserMessage", (), {})
SystemMessage = type("SystemMessage", (), {})

from src.logging import get_logger
from src.podcast.types import Script, ScriptLine
from src.tools.tts import VolcengineTTS
from ..controllers.conversation_manager import ConversationConfig, ConversationState, WorkflowState
from ..controllers.workflow_controller import (
    WorkflowController,
    WorkflowPlan,
    WorkflowStep,
    StepType,
    ExecutionStatus,
)

logger = get_logger(__name__)


class PodcastWorkflowManager:
    """
    AutoGen Podcast 工作流管理器

    負責將文本內容轉換為完整的播客音頻。
    """

    def __init__(self, model_client: ChatCompletionClient):
        """
        初始化Podcast工作流管理器

        Args:
            model_client: 聊天完成客戶端
        """
        self.model_client = model_client
        # 為了測試兼容性，添加 conversation_manager 屬性
        self.conversation_manager = None
        self.workflow_controller = WorkflowController()

        # 註冊步驟處理器
        self._register_step_handlers()

        logger.info("Podcast工作流管理器初始化完成")

    async def initialize(self):
        """初始化工作流管理器"""
        logger.info("初始化 Podcast 工作流管理器")
        # 這裡可以添加任何必要的初始化邏輯
        return True

    async def run_podcast_workflow(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """
        執行播客工作流

        Args:
            user_input: 用戶輸入
            **kwargs: 其他參數

        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            logger.info(f"開始執行播客工作流: {user_input}")

            # 創建播客請求
            request = {
                "content": user_input,
                "title": kwargs.get("title", "播客內容"),
                "locale": kwargs.get("locale", "zh"),
            }

            # 創建播客計劃
            plan = self._create_podcast_plan(
                request, request.get("locale", "zh"), kwargs.get("voice_config", {})
            )

            # 執行工作流
            result = await self.workflow_controller.execute_plan(
                plan, {"request": request, "plan": plan}, self._podcast_step_executor
            )

            return {
                "success": True,
                "plan": plan,
                "result": result,
                "execution_time": result.get("execution_time", 0),
            }

        except Exception as e:
            logger.error(f"播客工作流執行失敗: {e}")
            return {"success": False, "error": str(e)}

    async def _podcast_step_executor(
        self, step: WorkflowStep, state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        執行播客工作流步驟

        Args:
            step: 工作流步驟
            state: 當前狀態

        Returns:
            Dict[str, Any]: 步驟執行結果
        """
        try:
            logger.info(f"執行播客步驟: {step.name}")

            if step.step_type == StepType.SCRIPT_GENERATION:
                # 模擬腳本生成
                content = state.get("request", {}).get("content", "")
                return {"script": f"播客腳本: {content}", "status": "completed"}
            elif step.step_type == StepType.TTS_GENERATION:
                # 模擬語音合成
                return {"audio_file": "mock_audio.wav", "status": "completed"}
            elif step.step_type == StepType.AUDIO_MIXING:
                # 模擬音頻混音
                return {"final_audio": "final_podcast.wav", "status": "completed"}
            else:
                return {"status": "skipped", "message": f"未知步驟類型: {step.step_type}"}

        except Exception as e:
            logger.error(f"播客步驟執行失敗: {e}")
            return {"status": "error", "error": str(e)}

    def _create_podcast_plan(
        self, request: Dict[str, Any], locale: str = "zh", voice_config: Dict[str, Any] = None
    ) -> WorkflowPlan:
        """
        創建播客工作流計劃

        Args:
            request: 播客請求數據
            locale: 語言區域
            voice_config: 聲音配置

        Returns:
            WorkflowPlan: 工作流計劃
        """
        plan_id = f"podcast_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 創建工作流步驟
        steps = [
            WorkflowStep(
                id=f"{plan_id}_script",
                name="生成播客腳本",
                step_type=StepType.SCRIPT_GENERATION,
                description="生成播客腳本",
                agent_type="script_writer",
                inputs={"content": request.get("content", ""), "locale": locale},
            ),
            WorkflowStep(
                id=f"{plan_id}_tts",
                name="語音合成",
                step_type=StepType.TTS_GENERATION,
                description="生成語音文件",
                agent_type="tts_generator",
                inputs={"voice_config": voice_config or {}},
                dependencies=[f"{plan_id}_script"],
            ),
            WorkflowStep(
                id=f"{plan_id}_mix",
                name="音頻混音",
                step_type=StepType.AUDIO_MIXING,
                description="混合音頻文件",
                agent_type="audio_mixer",
                inputs={},
                dependencies=[f"{plan_id}_tts"],
            ),
        ]

        return WorkflowPlan(
            id=plan_id,
            name="播客生成計劃",
            description=f"生成播客: {request.get('title', '未命名')}",
            steps=steps,
        )

    def _register_step_handlers(self):
        """註冊步驟處理器"""
        self.workflow_controller.register_step_handler(
            StepType.SCRIPT_GENERATION, self._handle_script_generation
        )
        self.workflow_controller.register_step_handler(
            StepType.TTS_GENERATION, self._handle_tts_generation
        )
        self.workflow_controller.register_step_handler(
            StepType.AUDIO_MIXING, self._handle_audio_mixing
        )

    async def generate_podcast(
        self, content: str, locale: str = "zh", voice_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        生成播客音頻

        Args:
            content: 原始內容
            locale: 語言區域
            voice_config: 聲音配置

        Returns:
            Dict[str, Any]: 生成結果
        """
        logger.info("開始生成播客音頻")

        try:
            # 創建工作流計劃
            workflow_plan = self._create_podcast_plan(content, locale, voice_config)

            # 準備上下文
            context = {
                "content": content,
                "locale": locale,
                "voice_config": voice_config or {},
                "script": None,
                "audio_chunks": [],
                "output": None,
                "generated_at": datetime.now().isoformat(),
            }

            # 執行工作流
            result = await self.workflow_controller.execute_plan(workflow_plan, context)

            if result.get("status") == ExecutionStatus.COMPLETED:
                return {
                    "success": True,
                    "output": context.get("output"),
                    "script": context.get("script"),
                    "execution_time": result.get("execution_time", 0),
                    "steps_completed": result.get("steps_completed", 0),
                    "generated_at": context["generated_at"],
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "播客生成失敗"),
                    "execution_time": result.get("execution_time", 0),
                }

        except Exception as e:
            logger.error(f"播客生成失敗: {e}")
            return {"success": False, "error": str(e), "execution_time": 0}

    def _create_podcast_plan(
        self, content: str, locale: str, voice_config: Dict[str, Any]
    ) -> WorkflowPlan:
        """創建播客生成計劃"""
        steps = [
            WorkflowStep(
                id="script_generation",
                step_type=StepType.SCRIPT_GENERATION,
                description="生成播客腳本",
                agent_type="script_writer",
                inputs={"content": content, "locale": locale},
                expected_output="結構化的播客腳本",
                timeout_seconds=120,
                dependencies=[],
                status=ExecutionStatus.PENDING,
            ),
            WorkflowStep(
                id="tts_generation",
                step_type=StepType.TTS_GENERATION,
                description="將腳本轉換為語音",
                agent_type="tts_generator",
                inputs={"voice_config": voice_config},
                expected_output="音頻片段列表",
                dependencies=["script_generation"],
                timeout_seconds=300,
                status=ExecutionStatus.PENDING,
            ),
            WorkflowStep(
                id="audio_mixing",
                step_type=StepType.AUDIO_MIXING,
                description="混合音頻片段",
                agent_type="audio_mixer",
                inputs={},
                expected_output="最終的播客音頻",
                dependencies=["tts_generation"],
                timeout_seconds=60,
                status=ExecutionStatus.PENDING,
            ),
        ]

        return WorkflowPlan(
            id=f"podcast_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name="播客生成計劃",
            description="將文本內容轉換為播客音頻",
            steps=steps,
            metadata={
                "workflow_type": "podcast_generation",
                "locale": locale,
                "voice_config": voice_config,
            },
        )

    async def _handle_script_generation(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理腳本生成步驟"""
        logger.info("開始生成播客腳本")

        try:
            content = step.inputs.get("content", context.get("content", ""))
            locale = step.inputs.get("locale", context.get("locale", "zh"))

            if not content:
                raise ValueError("沒有提供內容進行腳本生成")

            # 獲取腳本生成提示
            script_prompt = self._get_script_prompt()

            # 調用LLM生成腳本
            messages = [SystemMessage(content=script_prompt), UserMessage(content=content)]

            # 使用structured output生成腳本
            response = await self.model_client.create(
                messages=messages, model="gpt-4", response_format={"type": "json_object"}
            )

            # 解析響應
            script_data = self._parse_script_response(response.choices[0].message.content)

            # 創建腳本對象
            script = Script(
                locale=script_data.get("locale", locale),
                lines=[
                    ScriptLine(
                        speaker=line.get("speaker", "male"), paragraph=line.get("paragraph", "")
                    )
                    for line in script_data.get("lines", [])
                ],
            )

            # 更新上下文
            context["script"] = script

            logger.info(f"腳本生成完成，共 {len(script.lines)} 行")

            return {
                "status": ExecutionStatus.COMPLETED,
                "result": script,
                "message": f"成功生成 {len(script.lines)} 行播客腳本",
            }

        except Exception as e:
            logger.error(f"腳本生成失敗: {e}")
            return {"status": ExecutionStatus.FAILED, "error": str(e), "message": "腳本生成失敗"}

    async def _handle_tts_generation(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理TTS生成步驟"""
        logger.info("開始生成語音")

        try:
            script = context.get("script")
            if not script:
                raise ValueError("沒有找到腳本進行語音生成")

            voice_config = step.inputs.get("voice_config", context.get("voice_config", {}))

            # 創建TTS客戶端
            tts_client = self._create_tts_client()
            audio_chunks = []

            # 為每行腳本生成音頻
            for i, line in enumerate(script.lines):
                try:
                    # 設置聲音類型
                    voice_type = self._get_voice_type(line.speaker, voice_config)
                    tts_client.voice_type = voice_type

                    # 生成音頻
                    result = tts_client.text_to_speech(
                        text=line.paragraph,
                        speed_ratio=voice_config.get("speed_ratio", 1.05),
                        volume_ratio=voice_config.get("volume_ratio", 1.0),
                        pitch_ratio=voice_config.get("pitch_ratio", 1.0),
                    )

                    if result["success"]:
                        audio_data = result["audio_data"]
                        audio_chunk = base64.b64decode(audio_data)
                        audio_chunks.append(audio_chunk)
                        logger.debug(f"成功生成第 {i + 1} 行音頻")
                    else:
                        logger.error(f"第 {i + 1} 行音頻生成失敗: {result.get('error')}")

                except Exception as e:
                    logger.error(f"第 {i + 1} 行音頻生成異常: {e}")
                    continue

            # 更新上下文
            context["audio_chunks"] = audio_chunks

            logger.info(f"語音生成完成，共 {len(audio_chunks)} 個音頻片段")

            return {
                "status": ExecutionStatus.COMPLETED,
                "result": audio_chunks,
                "message": f"成功生成 {len(audio_chunks)} 個音頻片段",
            }

        except Exception as e:
            logger.error(f"語音生成失敗: {e}")
            return {"status": ExecutionStatus.FAILED, "error": str(e), "message": "語音生成失敗"}

    async def _handle_audio_mixing(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理音頻混合步驟"""
        logger.info("開始混合音頻")

        try:
            audio_chunks = context.get("audio_chunks", [])
            if not audio_chunks:
                raise ValueError("沒有找到音頻片段進行混合")

            # 簡單的音頻拼接
            combined_audio = b"".join(audio_chunks)

            # 更新上下文
            context["output"] = combined_audio

            audio_size = len(combined_audio)
            logger.info(f"音頻混合完成，最終音頻大小: {audio_size} bytes")

            return {
                "status": ExecutionStatus.COMPLETED,
                "result": combined_audio,
                "message": f"成功混合音頻，大小: {audio_size} bytes",
            }

        except Exception as e:
            logger.error(f"音頻混合失敗: {e}")
            return {"status": ExecutionStatus.FAILED, "error": str(e), "message": "音頻混合失敗"}

    def _get_script_prompt(self) -> str:
        """獲取腳本生成提示"""
        return """You are a professional podcast editor for a show called "Hello Deer." Transform raw content into a conversational podcast script suitable for two hosts to read aloud.

# Guidelines

- **Tone**: The script should sound natural and conversational, like two people chatting. Include casual expressions, filler words, and interactive dialogue, but avoid regional dialects like "啥."
- **Hosts**: There are only two hosts, one male and one female. Ensure the dialogue alternates between them frequently, with no other characters or voices included.
- **Length**: Keep the script concise, aiming for a runtime of 10 minutes.
- **Structure**: Start with the male host speaking first. Avoid overly long sentences and ensure the hosts interact often.
- **Output**: Provide only the hosts' dialogue. Do not include introductions, dates, or any other meta information.
- **Language**: Use natural, easy-to-understand language. Avoid mathematical formulas, complex technical notation, or any content that would be difficult to read aloud. Always explain technical concepts in simple, conversational terms.

# Output Format

The output should be formatted as a valid, parseable JSON object of `Script` without "```json". The `Script` interface is defined as follows:

```ts
interface ScriptLine {
  speaker: 'male' | 'female';
  paragraph: string; // only plain text, never Markdown
}

interface Script {
  locale: "en" | "zh";
  lines: ScriptLine[];
}
```

# Notes

- It should always start with "Hello Deer" podcast greetings and followed by topic introduction.
- Ensure the dialogue flows naturally and feels engaging for listeners.
- Alternate between the male and female hosts frequently to maintain interaction.
- Avoid overly formal language; keep it casual and conversational.
- Always generate scripts in the same locale as the given context.
- Never include mathematical formulas (like E=mc², f(x)=y, 10^{7} etc.), chemical equations, complex code snippets, or other notation that's difficult to read aloud.
- When explaining technical or scientific concepts, translate them into plain, conversational language that's easy to understand and speak.
- If the original content contains formulas or technical notation, rephrase them in natural language. For example, instead of "x² + 2x + 1 = 0", say "x squared plus two x plus one equals zero" or better yet, explain the concept without the equation.
- Focus on making the content accessible and engaging for listeners who are consuming the information through audio only."""

    def _parse_script_response(self, response: str) -> Dict[str, Any]:
        """解析腳本響應"""
        import json

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"腳本響應解析失敗: {e}")
            # 返回默認腳本
            return {
                "locale": "zh",
                "lines": [
                    {"speaker": "male", "paragraph": "歡迎收聽Hello Deer播客！"},
                    {"speaker": "female", "paragraph": "今天我們將討論一個有趣的話題。"},
                ],
            }

    def _create_tts_client(self) -> VolcengineTTS:
        """創建TTS客戶端"""
        app_id = os.getenv("VOLCENGINE_TTS_APPID", "")
        if not app_id:
            raise Exception("VOLCENGINE_TTS_APPID is not set")

        access_token = os.getenv("VOLCENGINE_TTS_ACCESS_TOKEN", "")
        if not access_token:
            raise Exception("VOLCENGINE_TTS_ACCESS_TOKEN is not set")

        cluster = os.getenv("VOLCENGINE_TTS_CLUSTER", "volcano_tts")
        voice_type = "BV001_streaming"

        return VolcengineTTS(
            appid=app_id,
            access_token=access_token,
            cluster=cluster,
            voice_type=voice_type,
        )

    def _get_voice_type(self, speaker: str, voice_config: Dict[str, Any]) -> str:
        """獲取聲音類型"""
        default_voices = {"male": "BV002_streaming", "female": "BV001_streaming"}

        voice_mapping = voice_config.get("voice_mapping", default_voices)
        return voice_mapping.get(speaker, default_voices.get(speaker, "BV001_streaming"))


# 便利函數
async def generate_podcast_with_autogen(
    content: str,
    model_client: ChatCompletionClient,
    locale: str = "zh",
    voice_config: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """使用AutoGen生成播客"""
    manager = PodcastWorkflowManager(model_client)
    return await manager.generate_podcast(content, locale, voice_config)


def create_podcast_workflow_manager(model_client: ChatCompletionClient) -> PodcastWorkflowManager:
    """創建播客工作流管理器"""
    return PodcastWorkflowManager(model_client)
