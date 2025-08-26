# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
工具適配器

將 LangChain 工具適配到 AutoGen 系統，並提供統一的工具註冊機制。
"""

import inspect
import json
from typing import Any, Dict, List, Callable, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from langchain_core.tools import BaseTool as LangChainTool
# 注意：AutoGen 0.7.2 版本中已移除 Tool 類別
# from autogen_agentchat.base import Tool as AutoGenTool

from src.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ToolMetadata:
    """工具元資料"""

    name: str
    description: str
    parameters: Dict[str, Any]
    tool_type: str  # "langchain", "autogen", "native"
    source_module: str
    created_at: datetime
    last_used: Optional[datetime] = None
    usage_count: int = 0


class LangChainToolAdapter:
    """
    LangChain 工具適配器

    將 LangChain 的工具適配為 AutoGen 可用的工具格式。
    """

    def __init__(self):
        self.adapted_tools: Dict[str, Callable] = {}
        self.tool_metadata: Dict[str, ToolMetadata] = {}
        logger.info("LangChain 工具適配器初始化完成")

    def adapt_langchain_tool(self, langchain_tool: LangChainTool) -> Callable:
        """
        適配 LangChain 工具為 AutoGen 格式

        Args:
            langchain_tool: LangChain 工具實例

        Returns:
            Callable: AutoGen 相容的工具函數
        """
        tool_name = langchain_tool.name
        tool_description = langchain_tool.description

        # 提取工具參數信息
        parameters = self._extract_tool_parameters(langchain_tool)

        # 創建適配函數
        async def adapted_tool(**kwargs) -> str:
            """適配後的工具函數"""
            try:
                logger.info(f"執行適配工具: {tool_name}")

                # 更新使用統計
                if tool_name in self.tool_metadata:
                    metadata = self.tool_metadata[tool_name]
                    metadata.last_used = datetime.now()
                    metadata.usage_count += 1

                # 調用原始 LangChain 工具
                if hasattr(langchain_tool, "ainvoke"):
                    result = await langchain_tool.ainvoke(kwargs)
                else:
                    result = langchain_tool.invoke(kwargs)

                # 確保返回字串格式
                if isinstance(result, dict):
                    return json.dumps(result, ensure_ascii=False, indent=2)
                elif not isinstance(result, str):
                    return str(result)

                return result

            except Exception as e:
                error_msg = f"工具執行失敗 {tool_name}: {str(e)}"
                logger.error(error_msg)
                return error_msg

        # 設定函數屬性
        adapted_tool.__name__ = tool_name
        adapted_tool.__doc__ = tool_description

        # 保存適配工具和元資料
        self.adapted_tools[tool_name] = adapted_tool
        self.tool_metadata[tool_name] = ToolMetadata(
            name=tool_name,
            description=tool_description,
            parameters=parameters,
            tool_type="langchain",
            source_module=langchain_tool.__class__.__module__,
            created_at=datetime.now(),
        )

        logger.info(f"成功適配 LangChain 工具: {tool_name}")
        return adapted_tool

    def _extract_tool_parameters(self, tool: LangChainTool) -> Dict[str, Any]:
        """提取工具參數信息"""
        parameters = {}

        try:
            # 嘗試從 args_schema 獲取參數
            if hasattr(tool, "args_schema") and tool.args_schema:
                schema = tool.args_schema.model_json_schema()
                parameters = schema.get("properties", {})

            # 嘗試從函數簽名獲取參數
            elif hasattr(tool, "func"):
                sig = inspect.signature(tool.func)
                for param_name, param in sig.parameters.items():
                    param_info = {
                        "type": "string",  # 預設類型
                        "description": f"Parameter: {param_name}",
                    }

                    # 嘗試從註解獲取類型信息
                    if param.annotation != inspect.Parameter.empty:
                        if hasattr(param.annotation, "__name__"):
                            param_info["type"] = param.annotation.__name__

                    parameters[param_name] = param_info

        except Exception as e:
            logger.warning(f"無法提取工具參數 {tool.name}: {e}")

        return parameters

    def get_adapted_tool(self, tool_name: str) -> Optional[Callable]:
        """獲取適配後的工具"""
        return self.adapted_tools.get(tool_name)

    def list_adapted_tools(self) -> List[str]:
        """列出所有適配的工具"""
        return list(self.adapted_tools.keys())

    def get_tool_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """獲取工具元資料"""
        return self.tool_metadata.get(tool_name)


class AutoGenToolRegistry:
    """
    AutoGen 工具註冊中心

    統一管理所有類型的工具：LangChain 適配工具、AutoGen 原生工具、自定義工具。
    """

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_metadata: Dict[str, ToolMetadata] = {}
        self.tool_categories: Dict[str, List[str]] = {
            "search": [],
            "code": [],
            "crawl": [],
            "mcp": [],
            "analysis": [],
            "generation": [],
            "other": [],
        }

        self.langchain_adapter = LangChainToolAdapter()
        logger.info("AutoGen 工具註冊中心初始化完成")

    def register_langchain_tool(
        self, langchain_tool: LangChainTool, category: str = "other"
    ) -> str:
        """
        註冊 LangChain 工具

        Args:
            langchain_tool: LangChain 工具實例
            category: 工具類別

        Returns:
            str: 工具名稱
        """
        adapted_tool = self.langchain_adapter.adapt_langchain_tool(langchain_tool)
        tool_name = langchain_tool.name

        self.tools[tool_name] = adapted_tool
        self.tool_metadata[tool_name] = self.langchain_adapter.get_tool_metadata(tool_name)

        # 添加到類別
        if category in self.tool_categories:
            self.tool_categories[category].append(tool_name)
        else:
            self.tool_categories["other"].append(tool_name)

        logger.info(f"註冊 LangChain 工具: {tool_name} (類別: {category})")
        return tool_name

    def register_native_tool(
        self, tool_func: Callable, name: str, description: str, category: str = "other"
    ) -> str:
        """
        註冊原生工具

        Args:
            tool_func: 工具函數
            name: 工具名稱
            description: 工具描述
            category: 工具類別

        Returns:
            str: 工具名稱
        """
        # 提取參數信息
        parameters = {}
        try:
            sig = inspect.signature(tool_func)
            for param_name, param in sig.parameters.items():
                param_info = {"type": "string", "description": f"Parameter: {param_name}"}

                if param.annotation != inspect.Parameter.empty:
                    if hasattr(param.annotation, "__name__"):
                        param_info["type"] = param.annotation.__name__

                parameters[param_name] = param_info
        except Exception as e:
            logger.warning(f"無法提取工具參數 {name}: {e}")

        # 註冊工具
        self.tools[name] = tool_func
        self.tool_metadata[name] = ToolMetadata(
            name=name,
            description=description,
            parameters=parameters,
            tool_type="native",
            source_module=tool_func.__module__ if hasattr(tool_func, "__module__") else "unknown",
            created_at=datetime.now(),
        )

        # 添加到類別
        if category in self.tool_categories:
            self.tool_categories[category].append(name)
        else:
            self.tool_categories["other"].append(name)

        logger.info(f"註冊原生工具: {name} (類別: {category})")
        return name

    def get_tool(self, tool_name: str) -> Optional[Callable]:
        """獲取工具"""
        return self.tools.get(tool_name)

    def get_tools_by_category(self, category: str) -> List[Callable]:
        """按類別獲取工具"""
        tool_names = self.tool_categories.get(category, [])
        return [self.tools[name] for name in tool_names if name in self.tools]

    def list_tools(self) -> List[str]:
        """列出所有工具"""
        return list(self.tools.keys())

    def list_categories(self) -> List[str]:
        """列出所有工具類別"""
        return list(self.tool_categories.keys())

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """獲取工具完整信息"""
        if tool_name not in self.tools:
            return None

        metadata = self.tool_metadata.get(tool_name)
        if not metadata:
            return None

        return {
            "name": metadata.name,
            "description": metadata.description,
            "parameters": metadata.parameters,
            "tool_type": metadata.tool_type,
            "source_module": metadata.source_module,
            "created_at": metadata.created_at.isoformat(),
            "last_used": metadata.last_used.isoformat() if metadata.last_used else None,
            "usage_count": metadata.usage_count,
            "category": self._get_tool_category(tool_name),
        }

    def _get_tool_category(self, tool_name: str) -> str:
        """獲取工具類別"""
        for category, tools in self.tool_categories.items():
            if tool_name in tools:
                return category
        return "other"

    def get_registry_stats(self) -> Dict[str, Any]:
        """獲取註冊中心統計信息"""
        total_tools = len(self.tools)
        category_counts = {category: len(tools) for category, tools in self.tool_categories.items()}

        tool_type_counts = {}
        total_usage = 0

        for metadata in self.tool_metadata.values():
            tool_type = metadata.tool_type
            tool_type_counts[tool_type] = tool_type_counts.get(tool_type, 0) + 1
            total_usage += metadata.usage_count

        return {
            "total_tools": total_tools,
            "category_counts": category_counts,
            "tool_type_counts": tool_type_counts,
            "total_usage": total_usage,
            "last_updated": datetime.now().isoformat(),
        }

    def export_tool_definitions(self) -> Dict[str, Any]:
        """導出工具定義（用於配置或文檔生成）"""
        export_data = {"version": "1.0", "exported_at": datetime.now().isoformat(), "tools": {}}

        for tool_name, metadata in self.tool_metadata.items():
            export_data["tools"][tool_name] = {
                "name": metadata.name,
                "description": metadata.description,
                "parameters": metadata.parameters,
                "tool_type": metadata.tool_type,
                "category": self._get_tool_category(tool_name),
            }

        return export_data


# 全局工具註冊中心實例
global_tool_registry = AutoGenToolRegistry()
