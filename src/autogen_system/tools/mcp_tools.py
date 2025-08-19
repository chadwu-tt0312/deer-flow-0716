# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen MCP 工具

提供 Model Context Protocol (MCP) 伺服器連接和工具執行功能。
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from mcp import ClientSession, StdioServerParameters, Tool as MCPTool
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

from .mcp_config import global_mcp_config_manager, MCPServerConfig
from src.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MCPToolExecution:
    """MCP 工具執行記錄"""

    server_name: str
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    success: bool
    error: Optional[str]
    execution_time: float
    timestamp: datetime


class AutoGenMCPConnector:
    """
    AutoGen MCP 連接器

    管理與 MCP 伺服器的連接，並提供工具執行功能。
    """

    def __init__(self):
        """初始化 MCP 連接器"""
        self.servers: Dict[str, MCPServerConfig] = {}
        self.available_tools: Dict[
            str, Dict[str, Any]
        ] = {}  # {server_name: {tool_name: tool_info}}
        self.execution_history: List[MCPToolExecution] = []

        # 載入配置管理器中的伺服器配置
        self._load_servers_from_config()

        logger.info(f"AutoGen MCP 連接器初始化完成，載入了 {len(self.servers)} 個伺服器配置")

    def _load_servers_from_config(self):
        """從配置管理器載入伺服器配置"""
        try:
            enabled_servers = global_mcp_config_manager.get_enabled_servers()
            for server_name, config in enabled_servers.items():
                self.servers[server_name] = config
                logger.info(f"從配置載入 MCP 伺服器: {server_name}")
        except Exception as e:
            logger.error(f"載入 MCP 伺服器配置失敗: {e}")

    async def register_mcp_server(
        self,
        server_name: str,
        server_type: str,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        url: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 30,
    ) -> bool:
        """
        註冊 MCP 伺服器

        Args:
            server_name: 伺服器名稱
            server_type: 伺服器類型（stdio 或 sse）
            command: 命令（stdio 類型）
            args: 命令參數（stdio 類型）
            url: 伺服器 URL（sse 類型）
            env: 環境變數
            timeout_seconds: 超時時間

        Returns:
            bool: 註冊是否成功
        """
        try:
            config = MCPServerConfig(
                name=server_name,
                transport=server_type,  # 使用 transport 而不是 server_type
                command=command,
                args=args or [],
                url=url,
                env=env or {},
                timeout_seconds=timeout_seconds,
                enabled=True,
            )

            # 測試連接並獲取可用工具
            tools = await self._load_server_tools(config)

            self.servers[server_name] = config
            self.available_tools[server_name] = {
                tool.name: {
                    "name": tool.name,
                    "description": tool.description,
                    "schema": tool.inputSchema,
                }
                for tool in tools
            }

            # 同時更新配置管理器
            global_mcp_config_manager.add_server_config(config)

            logger.info(f"MCP 伺服器註冊成功: {server_name}，可用工具: {len(tools)} 個")
            return True

        except Exception as e:
            logger.error(f"MCP 伺服器註冊失敗 {server_name}: {e}")
            return False

    async def _load_server_tools(self, config: MCPServerConfig) -> List[MCPTool]:
        """載入伺服器工具"""
        if config.transport == "stdio":
            if not config.command:
                raise ValueError("stdio 類型需要 command 參數")

            server_params = StdioServerParameters(
                command=config.command, args=config.args, env=config.env
            )

            return await self._get_tools_from_client(
                stdio_client(server_params), config.timeout_seconds
            )

        elif config.transport == "sse":
            if not config.url:
                raise ValueError("sse 類型需要 url 參數")

            return await self._get_tools_from_client(
                sse_client(url=config.url), config.timeout_seconds
            )

        else:
            raise ValueError(f"不支援的伺服器類型: {config.transport}")

    async def _get_tools_from_client(
        self, client_context_manager, timeout_seconds: int
    ) -> List[MCPTool]:
        """從客戶端獲取工具"""
        async with client_context_manager as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed_tools = await session.list_tools()
                return listed_tools.tools

    async def execute_mcp_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any] = None
    ) -> str:
        """
        執行 MCP 工具

        Args:
            server_name: 伺服器名稱
            tool_name: 工具名稱
            arguments: 工具參數

        Returns:
            str: 執行結果
        """
        if server_name not in self.servers:
            error_msg = f"未找到 MCP 伺服器: {server_name}"
            logger.error(error_msg)
            return self._format_error_result(server_name, tool_name, error_msg)

        if (
            server_name not in self.available_tools
            or tool_name not in self.available_tools[server_name]
        ):
            error_msg = f"未找到工具 {tool_name} 在伺服器 {server_name}"
            logger.error(error_msg)
            return self._format_error_result(server_name, tool_name, error_msg)

        logger.info(f"執行 MCP 工具: {server_name}.{tool_name}")
        start_time = asyncio.get_event_loop().time()
        arguments = arguments or {}

        try:
            config = self.servers[server_name]
            result = await asyncio.wait_for(
                self._execute_tool_on_server(config, tool_name, arguments),
                timeout=config.timeout_seconds,
            )

            execution_time = asyncio.get_event_loop().time() - start_time

            # 記錄執行歷史
            execution_record = MCPToolExecution(
                server_name=server_name,
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                success=True,
                error=None,
                execution_time=execution_time,
                timestamp=datetime.now(),
            )
            self.execution_history.append(execution_record)

            logger.info(
                f"MCP 工具執行成功: {server_name}.{tool_name}，耗時: {execution_time:.2f}秒"
            )
            return self._format_success_result(execution_record)

        except asyncio.TimeoutError:
            execution_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"MCP 工具執行超時（{config.timeout_seconds}秒）"
            logger.error(error_msg)
            return self._format_timeout_result(server_name, tool_name, execution_time)

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"MCP 工具執行失敗: {str(e)}"
            logger.error(error_msg)

            # 記錄失敗歷史
            execution_record = MCPToolExecution(
                server_name=server_name,
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                success=False,
                error=str(e),
                execution_time=execution_time,
                timestamp=datetime.now(),
            )
            self.execution_history.append(execution_record)

            return self._format_error_result(server_name, tool_name, error_msg, execution_time)

    async def _execute_tool_on_server(
        self, config: MCPServerConfig, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        """在伺服器上執行工具"""
        if config.transport == "stdio":
            server_params = StdioServerParameters(
                command=config.command, args=config.args, env=config.env
            )

            return await self._execute_with_client(
                stdio_client(server_params), tool_name, arguments
            )

        elif config.transport == "sse":
            return await self._execute_with_client(sse_client(url=config.url), tool_name, arguments)

    async def _execute_with_client(
        self, client_context_manager, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        """使用客戶端執行工具"""
        async with client_context_manager as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return result

    def _format_success_result(self, execution: MCPToolExecution) -> str:
        """格式化成功結果"""
        return f"""✅ MCP 工具執行成功

**伺服器:** {execution.server_name}
**工具:** {execution.tool_name}
**參數:** {json.dumps(execution.arguments, ensure_ascii=False, indent=2)}

**執行結果:**
```json
{json.dumps(execution.result, ensure_ascii=False, indent=2)}
```

**執行資訊:**
- 執行時間: {execution.execution_time:.2f} 秒
- 執行時間戳: {execution.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
"""

    def _format_error_result(
        self, server_name: str, tool_name: str, error_msg: str, execution_time: float = 0
    ) -> str:
        """格式化錯誤結果"""
        return f"""❌ MCP 工具執行失敗

**伺服器:** {server_name}
**工具:** {tool_name}
**錯誤訊息:** {error_msg}

**執行資訊:**
- 執行時間: {execution_time:.2f} 秒
- 執行時間戳: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**可用的 MCP 工具:**
{self._get_available_tools_summary()}
"""

    def _format_timeout_result(
        self, server_name: str, tool_name: str, execution_time: float
    ) -> str:
        """格式化超時結果"""
        config = self.servers[server_name]
        return f"""⏰ MCP 工具執行超時

**伺服器:** {server_name}
**工具:** {tool_name}
**設定超時:** {config.timeout_seconds} 秒
**實際執行時間:** {execution_time:.2f} 秒
**執行時間戳:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**建議:**
1. 增加超時時間設定
2. 檢查 MCP 伺服器狀態
3. 確認工具參數是否正確
4. 檢查網路連接
"""

    def list_servers(self) -> List[str]:
        """列出所有註冊的伺服器"""
        return list(self.servers.keys())

    def list_tools(self, server_name: str = None) -> Dict[str, List[str]]:
        """列出可用工具"""
        if server_name:
            if server_name in self.available_tools:
                return {server_name: list(self.available_tools[server_name].keys())}
            else:
                return {}

        return {server: list(tools.keys()) for server, tools in self.available_tools.items()}

    def get_tool_info(self, server_name: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """獲取工具詳細資訊"""
        if server_name in self.available_tools and tool_name in self.available_tools[server_name]:
            return self.available_tools[server_name][tool_name]
        return None

    def _get_available_tools_summary(self) -> str:
        """獲取可用工具摘要"""
        if not self.available_tools:
            return "目前沒有可用的 MCP 工具"

        summary_lines = []
        for server_name, tools in self.available_tools.items():
            tool_names = list(tools.keys())
            summary_lines.append(f"- **{server_name}**: {', '.join(tool_names)}")

        return "\n".join(summary_lines)

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """獲取執行歷史"""
        return [
            {
                "server_name": exec.server_name,
                "tool_name": exec.tool_name,
                "success": exec.success,
                "execution_time": exec.execution_time,
                "timestamp": exec.timestamp.isoformat(),
                "has_error": exec.error is not None,
            }
            for exec in self.execution_history
        ]

    def clear_history(self):
        """清除執行歷史"""
        self.execution_history.clear()
        logger.info("MCP 執行歷史已清除")

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        if not self.execution_history:
            return {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "average_execution_time": 0,
                "servers_count": len(self.servers),
                "tools_count": sum(len(tools) for tools in self.available_tools.values()),
            }

        successful = sum(1 for exec in self.execution_history if exec.success)
        total_time = sum(exec.execution_time for exec in self.execution_history)

        return {
            "total_executions": len(self.execution_history),
            "successful_executions": successful,
            "failed_executions": len(self.execution_history) - successful,
            "success_rate": successful / len(self.execution_history) * 100,
            "average_execution_time": total_time / len(self.execution_history),
            "total_execution_time": total_time,
            "servers_count": len(self.servers),
            "tools_count": sum(len(tools) for tools in self.available_tools.values()),
        }

    async def test_all_servers(self) -> Dict[str, bool]:
        """測試所有伺服器連接"""
        results = {}
        for server_name in self.servers:
            try:
                config = self.servers[server_name]
                await self._load_server_tools(config)
                results[server_name] = True
                logger.info(f"MCP 伺服器連接測試成功: {server_name}")
            except Exception as e:
                results[server_name] = False
                logger.error(f"MCP 伺服器連接測試失敗 {server_name}: {e}")

        return results


# 便利函數
async def execute_mcp_tool(
    server_name: str, tool_name: str, arguments: Dict[str, Any] = None
) -> str:
    """執行 MCP 工具"""
    connector = AutoGenMCPConnector()
    return await connector.execute_mcp_tool(server_name, tool_name, arguments)


async def list_mcp_tools(server_name: str = None) -> str:
    """列出 MCP 工具"""
    connector = AutoGenMCPConnector()
    tools = connector.list_tools(server_name)

    if not tools:
        return "目前沒有可用的 MCP 工具"

    result_lines = ["# 📋 可用的 MCP 工具\n"]
    for server, tool_list in tools.items():
        result_lines.append(f"## 伺服器: {server}")
        for tool in tool_list:
            result_lines.append(f"- `{tool}`")
        result_lines.append("")

    return "\n".join(result_lines)
