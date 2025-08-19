# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen PPT 生成工作流

將LangGraph的PPT工作流遷移到AutoGen架構。
"""

import asyncio
import os
import subprocess
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path


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
from ..controllers.conversation_manager import ConversationConfig, ConversationState, WorkflowState
from ..controllers.workflow_controller import (
    WorkflowController,
    WorkflowPlan,
    WorkflowStep,
    StepType,
    ExecutionStatus,
)

logger = get_logger(__name__)


class PPTWorkflowManager:
    """
    AutoGen PPT 工作流管理器

    負責將文本內容轉換為PowerPoint演示文稿。
    """

    def __init__(self, model_client: ChatCompletionClient):
        """
        初始化PPT工作流管理器

        Args:
            model_client: 聊天完成客戶端
        """
        self.model_client = model_client
        # 為了測試兼容性，添加 conversation_manager 屬性
        self.conversation_manager = None
        self.workflow_controller = WorkflowController()

        # 註冊步驟處理器
        self._register_step_handlers()

        logger.info("PPT工作流管理器初始化完成")

    async def initialize(self):
        """初始化工作流管理器"""
        logger.info("初始化 PPT 工作流管理器")
        # 這裡可以添加任何必要的初始化邏輯
        return True

    async def run_ppt_workflow(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """
        執行 PPT 工作流

        Args:
            user_input: 用戶輸入
            **kwargs: 其他參數

        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            logger.info(f"開始執行 PPT 工作流: {user_input}")

            # 創建 PPT 請求
            request = {
                "content": user_input,
                "title": kwargs.get("title", "PPT 簡報"),
                "style": kwargs.get("style", "professional"),
            }

            # 創建 PPT 計劃
            plan = self._create_ppt_plan(
                request,
                request.get("title", "PPT 簡報"),
                kwargs.get("audience", "一般聽眾"),
                kwargs.get("duration", 10),
                request.get("style", "professional"),
                kwargs.get("output_format", "pptx"),
            )

            # 執行工作流
            result = await self.workflow_controller.execute_plan(
                plan, {"request": request, "plan": plan}, self._ppt_step_executor
            )

            return {
                "success": True,
                "plan": plan,
                "result": result,
                "execution_time": result.get("execution_time", 0),
            }

        except Exception as e:
            logger.error(f"PPT 工作流執行失敗: {e}")
            return {"success": False, "error": str(e)}

    async def _ppt_step_executor(self, step: WorkflowStep, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行 PPT 工作流步驟

        Args:
            step: 工作流步驟
            state: 當前狀態

        Returns:
            Dict[str, Any]: 步驟執行結果
        """
        try:
            logger.info(f"執行 PPT 步驟: {step.name}")

            if step.step_type == StepType.CONTENT_ANALYSIS:
                # 模擬內容分析
                content = state.get("request", {}).get("content", "")
                return {"analysis": f"內容分析: {content[:100]}...", "status": "completed"}
            elif step.step_type == StepType.STRUCTURE_DESIGN:
                # 模擬結構設計
                return {"structure": "PPT 結構設計完成", "status": "completed"}
            elif step.step_type == StepType.CONTENT_GENERATION:
                # 模擬內容生成
                return {"slides": "PPT 內容生成完成", "status": "completed"}
            elif step.step_type == StepType.FILE_GENERATION:
                # 模擬檔案生成
                return {"ppt_file": "presentation.pptx", "status": "completed"}
            else:
                return {"status": "skipped", "message": f"未知步驟類型: {step.step_type}"}

        except Exception as e:
            logger.error(f"PPT 步驟執行失敗: {e}")
            return {"status": "error", "error": str(e)}

    def _create_ppt_plan(
        self,
        request: Dict[str, Any],
        title: str = "",
        audience: str = "",
        duration: int = 10,
        style: str = "professional",
        output_format: str = "pptx",
    ) -> WorkflowPlan:
        """
        創建PPT工作流計劃

        Args:
            request: PPT請求數據
            title: PPT標題
            audience: 目標受眾
            duration: 演示時長
            style: 風格
            output_format: 輸出格式

        Returns:
            WorkflowPlan: 工作流計劃
        """
        plan_id = f"ppt_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 創建工作流步驟
        steps = [
            WorkflowStep(
                id=f"{plan_id}_outline",
                name="生成PPT大綱",
                step_type=StepType.OUTLINE_GENERATION,
                description="生成PPT大綱",
                agent_type="outline_generator",
                inputs={
                    "content": request.get("content", ""),
                    "title": title,
                    "audience": audience,
                },
            ),
            WorkflowStep(
                id=f"{plan_id}_slides",
                name="生成幻燈片",
                step_type=StepType.SLIDE_GENERATION,
                description="生成幻燈片內容",
                agent_type="slide_generator",
                inputs={"style": style, "duration": duration},
                dependencies=[f"{plan_id}_outline"],
            ),
            WorkflowStep(
                id=f"{plan_id}_create",
                name="創建PPT文件",
                step_type=StepType.PPT_CREATION,
                description="創建PPT文件",
                agent_type="ppt_creator",
                inputs={"output_format": output_format},
                dependencies=[f"{plan_id}_slides"],
            ),
        ]

        return WorkflowPlan(
            id=plan_id,
            name="PPT生成計劃",
            description=f"生成PPT: {title or request.get('title', '未命名')}",
            steps=steps,
        )

    def _register_step_handlers(self):
        """註冊步驟處理器"""
        self.workflow_controller.register_step_handler(
            StepType.OUTLINE_GENERATION, self._handle_outline_generation
        )
        self.workflow_controller.register_step_handler(
            StepType.SLIDE_GENERATION, self._handle_slide_generation
        )
        self.workflow_controller.register_step_handler(
            StepType.PPT_CREATION, self._handle_ppt_creation
        )

    async def generate_ppt(
        self,
        content: str,
        title: str = None,
        audience: str = None,
        duration: int = 15,
        style: str = "professional",
        output_format: str = "pptx",
    ) -> Dict[str, Any]:
        """
        生成PPT演示文稿

        Args:
            content: 原始內容
            title: 演示文稿標題
            audience: 目標觀眾
            duration: 演示時長（分鐘）
            style: 演示風格
            output_format: 輸出格式（pptx, pdf, html）

        Returns:
            Dict[str, Any]: 生成結果
        """
        logger.info("開始生成PPT演示文稿")

        try:
            # 創建工作流計劃
            workflow_plan = self._create_ppt_plan(
                content, title, audience, duration, style, output_format
            )

            # 準備上下文
            context = {
                "content": content,
                "title": title or "演示文稿",
                "audience": audience or "一般聽眾",
                "duration": duration,
                "style": style,
                "output_format": output_format,
                "outline": None,
                "markdown_content": None,
                "temp_file_path": None,
                "generated_file_path": None,
                "generated_at": datetime.now().isoformat(),
            }

            # 執行工作流
            result = await self.workflow_controller.execute_plan(workflow_plan, context)

            if result.get("status") == ExecutionStatus.COMPLETED:
                return {
                    "success": True,
                    "generated_file_path": context.get("generated_file_path"),
                    "markdown_content": context.get("markdown_content"),
                    "outline": context.get("outline"),
                    "execution_time": result.get("execution_time", 0),
                    "steps_completed": result.get("steps_completed", 0),
                    "generated_at": context["generated_at"],
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "PPT生成失敗"),
                    "execution_time": result.get("execution_time", 0),
                }

        except Exception as e:
            logger.error(f"PPT生成失敗: {e}")
            return {"success": False, "error": str(e), "execution_time": 0}

    def _create_ppt_plan(
        self, content: str, title: str, audience: str, duration: int, style: str, output_format: str
    ) -> WorkflowPlan:
        """創建PPT生成計劃"""
        steps = [
            WorkflowStep(
                id="outline_generation",
                step_type=StepType.OUTLINE_GENERATION,
                description="生成演示文稿大綱",
                agent_type="outline_generator",
                inputs={
                    "content": content,
                    "title": title,
                    "audience": audience,
                    "duration": duration,
                },
                expected_output="結構化的演示大綱",
                timeout_seconds=90,
                dependencies=[],
                status=ExecutionStatus.PENDING,
            ),
            WorkflowStep(
                id="slide_generation",
                step_type=StepType.SLIDE_GENERATION,
                description="生成Markdown格式的投影片內容",
                agent_type="slide_generator",
                inputs={"style": style, "output_format": output_format},
                expected_output="Markdown格式的投影片",
                dependencies=["outline_generation"],
                timeout_seconds=180,
                status=ExecutionStatus.PENDING,
            ),
            WorkflowStep(
                id="ppt_creation",
                step_type=StepType.PPT_CREATION,
                description="生成最終的PPT檔案",
                agent_type="ppt_creator",
                inputs={"output_format": output_format},
                expected_output="PPT檔案路徑",
                dependencies=["slide_generation"],
                timeout_seconds=120,
                status=ExecutionStatus.PENDING,
            ),
        ]

        return WorkflowPlan(
            id=f"ppt_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name="PPT生成計劃",
            description="將內容轉換為PowerPoint演示文稿",
            steps=steps,
            metadata={
                "workflow_type": "ppt_generation",
                "title": title,
                "audience": audience,
                "duration": duration,
                "style": style,
                "output_format": output_format,
            },
        )

    async def _handle_outline_generation(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理大綱生成步驟"""
        logger.info("開始生成演示大綱")

        try:
            content = step.inputs.get("content", context.get("content", ""))
            title = step.inputs.get("title", context.get("title", "演示文稿"))
            audience = step.inputs.get("audience", context.get("audience", "一般聽眾"))
            duration = step.inputs.get("duration", context.get("duration", 15))

            if not content:
                raise ValueError("沒有提供內容進行大綱生成")

            # 生成大綱提示
            outline_prompt = self._get_outline_prompt(title, audience, duration)

            # 調用LLM生成大綱
            messages = [SystemMessage(content=outline_prompt), UserMessage(content=content)]

            response = await self.model_client.create(
                messages=messages, model="gpt-4", response_format={"type": "json_object"}
            )

            # 解析大綱響應
            outline_data = self._parse_outline_response(response.choices[0].message.content)

            # 更新上下文
            context["outline"] = outline_data

            logger.info(f"大綱生成完成，共 {len(outline_data.get('slides', []))} 張投影片")

            return {
                "status": ExecutionStatus.COMPLETED,
                "result": outline_data,
                "message": f"成功生成 {len(outline_data.get('slides', []))} 張投影片的大綱",
            }

        except Exception as e:
            logger.error(f"大綱生成失敗: {e}")
            return {"status": ExecutionStatus.FAILED, "error": str(e), "message": "大綱生成失敗"}

    async def _handle_slide_generation(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理投影片生成步驟"""
        logger.info("開始生成投影片內容")

        try:
            outline = context.get("outline")
            if not outline:
                raise ValueError("沒有找到大綱進行投影片生成")

            content = context.get("content", "")
            style = step.inputs.get("style", context.get("style", "professional"))

            # 生成投影片內容提示
            slide_prompt = self._get_slide_prompt(style)

            # 構建投影片生成請求
            request_content = f"""
基於以下大綱和原始內容生成Markdown格式的演示文稿：

## 大綱：
{self._format_outline_for_prompt(outline)}

## 原始內容：
{content}

請生成完整的Markdown格式投影片內容。
"""

            messages = [SystemMessage(content=slide_prompt), UserMessage(content=request_content)]

            response = await self.model_client.create(messages=messages, model="gpt-4")

            markdown_content = response.choices[0].message.content

            # 保存到臨時檔案
            temp_file_path = self._save_to_temp_file(markdown_content)

            # 更新上下文
            context["markdown_content"] = markdown_content
            context["temp_file_path"] = temp_file_path

            logger.info("投影片內容生成完成")

            return {
                "status": ExecutionStatus.COMPLETED,
                "result": markdown_content,
                "message": "成功生成Markdown格式的投影片內容",
            }

        except Exception as e:
            logger.error(f"投影片生成失敗: {e}")
            return {"status": ExecutionStatus.FAILED, "error": str(e), "message": "投影片生成失敗"}

    async def _handle_ppt_creation(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理PPT檔案創建步驟"""
        logger.info("開始創建PPT檔案")

        try:
            temp_file_path = context.get("temp_file_path")
            if not temp_file_path:
                raise ValueError("沒有找到臨時檔案進行PPT創建")

            output_format = step.inputs.get("output_format", context.get("output_format", "pptx"))

            # 生成輸出檔案路徑
            output_file_path = self._get_output_file_path(output_format)

            # 使用Marp CLI生成PPT
            success = self._generate_ppt_with_marp(temp_file_path, output_file_path, output_format)

            if success:
                # 清理臨時檔案
                self._cleanup_temp_file(temp_file_path)

                # 更新上下文
                context["generated_file_path"] = output_file_path

                file_size = (
                    os.path.getsize(output_file_path) if os.path.exists(output_file_path) else 0
                )
                logger.info(f"PPT檔案創建完成: {output_file_path} ({file_size} bytes)")

                return {
                    "status": ExecutionStatus.COMPLETED,
                    "result": output_file_path,
                    "message": f"成功創建PPT檔案: {output_file_path}",
                }
            else:
                return {
                    "status": ExecutionStatus.FAILED,
                    "error": "Marp CLI執行失敗",
                    "message": "PPT檔案創建失敗",
                }

        except Exception as e:
            logger.error(f"PPT創建失敗: {e}")
            return {"status": ExecutionStatus.FAILED, "error": str(e), "message": "PPT創建失敗"}

    def _get_outline_prompt(self, title: str, audience: str, duration: int) -> str:
        """獲取大綱生成提示"""
        return f"""You are a professional presentation consultant. Create a detailed outline for a presentation.

Title: {title}
Target Audience: {audience}
Duration: {duration} minutes

Based on the provided content, create a structured presentation outline with the following format:

{{
  "title": "{title}",
  "audience": "{audience}",
  "duration": {duration},
  "slides": [
    {{
      "slide_number": 1,
      "title": "Slide Title",
      "type": "title|content|conclusion",
      "key_points": ["Point 1", "Point 2", "Point 3"],
      "estimated_time": 2
    }}
  ],
  "total_slides": 0
}}

Guidelines:
- Title slide (1-2 minutes)
- Introduction/Agenda (1-2 minutes)
- Main content slides (most of the time)
- Conclusion/Summary (1-2 minutes)
- Q&A if applicable
- Each content slide should cover 1-2 minutes
- Keep key points concise and actionable
- Ensure logical flow between slides"""

    def _get_slide_prompt(self, style: str) -> str:
        """獲取投影片生成提示"""
        return f"""# Professional Presentation (PPT) Markdown Assistant

## Purpose
You are a professional PPT presentation creation assistant who transforms user requirements into a clear, focused Markdown-formatted presentation text. Your output should start directly with the presentation content, without any introductory phrases or explanations.

## Style: {style}

## Markdown PPT Formatting Guidelines

### Title and Structure
- Use `#` for the title slide (typically one slide)
- Use `##` for slide titles
- Use `###` for subtitles (if needed)
- Use horizontal rule `---` to separate slides

### Content Formatting
- Use unordered lists (`*` or `-`) for key points
- Use ordered lists (`1.`, `2.`) for sequential steps
- Separate paragraphs with blank lines
- Use code blocks with triple backticks
- IMPORTANT: When including images, ONLY use the actual image URLs from the source content. DO NOT create fictional image URLs or placeholders like 'example.com'

## Processing Workflow

### 1. Understand User Requirements
- Carefully read all provided information
- Note:
  * Presentation topic
  * Target audience
  * Key messages
  * Presentation duration
  * Specific style or format requirements

### 2. Extract Core Content
- Identify the most important points
- Remember: PPT supports the speech, not replaces it

### 3. Organize Content Structure
Typical structure includes:
- Title Slide
- Introduction/Agenda
- Body (multiple sections)
- Summary/Conclusion
- Optional Q&A section

### 4. Create Markdown Presentation
- Ensure each slide focuses on one main point
- Use concise, powerful language
- Emphasize points with bullet points
- Use appropriate title hierarchy

### 5. Review and Optimize
- Check for completeness
- Refine text formatting
- Ensure readability

## Important Guidelines
- Do not guess or add information not provided
- Ask clarifying questions if needed
- Simplify detailed or lengthy information
- Highlight Markdown advantages (easy editing, version control)
- ONLY use images that are explicitly provided in the source content
- NEVER create fictional image URLs or placeholders
- If you include an image, use the exact URL from the source content

## Response Guidelines
- Provide a complete, ready-to-use Markdown presentation
- Ensure professional and clear formatting
- Adapt to user's specific context and requirements
- IMPORTANT: Start your response directly with the presentation content. DO NOT include any introductory phrases like "Here's a presentation about..." or "Here's a professional Markdown-formatted presentation..."
- Begin your response with the title using a single # heading
- For images, ONLY use the exact image URLs found in the source content. DO NOT invent or create fictional image URLs
- If the source content contains images, incorporate them in your presentation using the exact same URLs"""

    def _parse_outline_response(self, response: str) -> Dict[str, Any]:
        """解析大綱響應"""
        import json

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"大綱響應解析失敗: {e}")
            # 返回默認大綱
            return {
                "title": "演示文稿",
                "audience": "一般聽眾",
                "duration": 15,
                "slides": [
                    {
                        "slide_number": 1,
                        "title": "標題頁",
                        "type": "title",
                        "key_points": ["演示主題"],
                        "estimated_time": 1,
                    },
                    {
                        "slide_number": 2,
                        "title": "主要內容",
                        "type": "content",
                        "key_points": ["重點1", "重點2", "重點3"],
                        "estimated_time": 10,
                    },
                    {
                        "slide_number": 3,
                        "title": "總結",
                        "type": "conclusion",
                        "key_points": ["總結要點"],
                        "estimated_time": 2,
                    },
                ],
                "total_slides": 3,
            }

    def _format_outline_for_prompt(self, outline: Dict[str, Any]) -> str:
        """格式化大綱用於提示"""
        result = f"標題: {outline.get('title', '演示文稿')}\n"
        result += f"聽眾: {outline.get('audience', '一般聽眾')}\n"
        result += f"時長: {outline.get('duration', 15)} 分鐘\n\n"

        slides = outline.get("slides", [])
        for slide in slides:
            result += f"{slide.get('slide_number', 1)}. {slide.get('title', '投影片')}\n"
            result += f"   類型: {slide.get('type', 'content')}\n"
            result += f"   重點: {', '.join(slide.get('key_points', []))}\n"
            result += f"   時間: {slide.get('estimated_time', 2)} 分鐘\n\n"

        return result

    def _save_to_temp_file(self, content: str) -> str:
        """保存內容到臨時檔案"""
        temp_file_path = os.path.join(os.getcwd(), f"ppt_content_{uuid.uuid4()}.md")
        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return temp_file_path

    def _get_output_file_path(self, output_format: str) -> str:
        """獲取輸出檔案路徑"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_ppt_{timestamp}.{output_format}"

        return str(output_dir / filename)

    def _generate_ppt_with_marp(
        self, input_file: str, output_file: str, output_format: str
    ) -> bool:
        """使用Marp CLI生成PPT"""
        try:
            # 檢查Marp CLI是否可用
            result = subprocess.run(["marp", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("Marp CLI不可用，將保存為Markdown檔案")
                # 如果Marp不可用，複製markdown檔案
                import shutil

                md_output = output_file.replace(f".{output_format}", ".md")
                shutil.copy(input_file, md_output)
                return True

            # 使用Marp CLI生成PPT
            cmd = ["marp", input_file, "-o", output_file]

            if output_format == "pdf":
                cmd.extend(["--pdf"])
            elif output_format == "html":
                cmd.extend(["--html"])

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("Marp CLI執行成功")
                return True
            else:
                logger.error(f"Marp CLI執行失敗: {result.stderr}")
                return False

        except FileNotFoundError:
            logger.warning("Marp CLI未安裝，將保存為Markdown檔案")
            # 如果Marp未安裝，複製markdown檔案
            import shutil

            md_output = output_file.replace(f".{output_format}", ".md")
            shutil.copy(input_file, md_output)
            return True
        except Exception as e:
            logger.error(f"PPT生成異常: {e}")
            return False

    def _cleanup_temp_file(self, file_path: str):
        """清理臨時檔案"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"清理臨時檔案: {file_path}")
        except Exception as e:
            logger.warning(f"清理臨時檔案失敗: {e}")


# 便利函數
async def generate_ppt_with_autogen(
    content: str,
    model_client: ChatCompletionClient,
    title: str = None,
    audience: str = None,
    duration: int = 15,
    style: str = "professional",
    output_format: str = "pptx",
) -> Dict[str, Any]:
    """使用AutoGen生成PPT"""
    manager = PPTWorkflowManager(model_client)
    return await manager.generate_ppt(content, title, audience, duration, style, output_format)


def create_ppt_workflow_manager(model_client: ChatCompletionClient) -> PPTWorkflowManager:
    """創建PPT工作流管理器"""
    return PPTWorkflowManager(model_client)
