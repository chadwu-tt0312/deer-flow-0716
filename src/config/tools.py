# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
import enum
# 移除 dotenv 導入以避免循環導入問題
# from dotenv import load_dotenv

# load_dotenv()


class SearchEngine(enum.Enum):
    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"
    BRAVE_SEARCH = "brave_search"
    ARXIV = "arxiv"
    GROUNDING_BING = "grounding_bing"


# Tool configuration
SELECTED_SEARCH_ENGINE = os.getenv("SEARCH_API", SearchEngine.TAVILY.value)


class RAGProvider(enum.Enum):
    RAGFLOW = "ragflow"
    VIKINGDB_KNOWLEDGE_BASE = "vikingdb_knowledge_base"


SELECTED_RAG_PROVIDER = os.getenv("RAG_PROVIDER")
