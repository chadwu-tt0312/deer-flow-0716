# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 系統工作流

包含各種專門的工作流程實現。
"""

from .research_workflow import ResearchWorkflowManager, run_simple_research, run_advanced_research
from .podcast_workflow import (
    PodcastWorkflowManager,
    create_podcast_workflow_manager,
    generate_podcast_with_autogen,
)
from .ppt_workflow import (
    PPTWorkflowManager,
    create_ppt_workflow_manager,
    generate_ppt_with_autogen,
)
from .prose_workflow import (
    ProseWorkflowManager,
    create_prose_workflow_manager,
    generate_prose_with_autogen,
    ProseOption,
    ProseRequest,
    ProseResult,
)
from .prompt_enhancer_workflow import (
    PromptEnhancerWorkflowManager,
    create_prompt_enhancer_workflow_manager,
    enhance_prompt_with_autogen,
    PromptEnhancementRequest,
    PromptEnhancementResult,
)

__all__ = [
    # 研究工作流
    "ResearchWorkflowManager",
    "run_simple_research",
    "run_advanced_research",
    # Podcast工作流
    "PodcastWorkflowManager",
    "create_podcast_workflow_manager",
    "generate_podcast_with_autogen",
    # PPT工作流
    "PPTWorkflowManager",
    "create_ppt_workflow_manager",
    "generate_ppt_with_autogen",
    # Prose工作流
    "ProseWorkflowManager",
    "create_prose_workflow_manager",
    "generate_prose_with_autogen",
    "ProseOption",
    "ProseRequest",
    "ProseResult",
    # PromptEnhancer工作流
    "PromptEnhancerWorkflowManager",
    "create_prompt_enhancer_workflow_manager",
    "enhance_prompt_with_autogen",
    "PromptEnhancementRequest",
    "PromptEnhancementResult",
]
