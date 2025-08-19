# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
MCP 管理器

提供 MCP 伺服器的高級管理功能。
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .mcp_config import global_mcp_config_manager, MCPServerConfig
from .mcp_tools import AutoGenMCPConnector
from src.logging import get_logger

logger = get_logger(__name__)


class MCPManager:
    """
    MCP 管理器

    提供 MCP 伺服器的高級管理功能，包括自動載入、健康檢查、工具管理等。
    """

    def __init__(self):
        """初始化 MCP 管理器"""
        self.connector = AutoGenMCPConnector()
        self.health_status: Dict[str, bool] = {}
        self.last_health_check: Optional[datetime] = None

        logger.info("MCP 管理器初始化完成")

    async def initialize_all_servers(self) -> Dict[str, bool]:
        """
        初始化所有配置的伺服器

        Returns:
            Dict[str, bool]: 伺服器名稱到初始化結果的映射
        """
        logger.info("開始初始化所有 MCP 伺服器")

        results = {}
        enabled_servers = global_mcp_config_manager.get_enabled_servers()

        for server_name, config in enabled_servers.items():
            try:
                logger.info(f"初始化 MCP 伺服器: {server_name}")

                # 註冊伺服器並測試連接
                success = await self.connector.register_mcp_server(
                    server_name=config.name,
                    server_type=config.transport,
                    command=config.command,
                    args=config.args,
                    url=config.url,
                    env=config.env,
                    timeout_seconds=config.timeout_seconds,
                )

                results[server_name] = success
                self.health_status[server_name] = success

                if success:
                    logger.info(f"MCP 伺服器初始化成功: {server_name}")
                else:
                    logger.error(f"MCP 伺服器初始化失敗: {server_name}")

            except Exception as e:
                logger.error(f"初始化 MCP 伺服器失敗 {server_name}: {e}")
                results[server_name] = False
                self.health_status[server_name] = False

        self.last_health_check = datetime.now()

        successful_count = sum(results.values())
        total_count = len(results)
        logger.info(f"MCP 伺服器初始化完成: {successful_count}/{total_count} 成功")

        return results

    async def health_check_all_servers(self, force: bool = False) -> Dict[str, bool]:
        """
        健康檢查所有伺服器

        Args:
            force: 是否強制執行檢查（忽略時間限制）

        Returns:
            Dict[str, bool]: 伺服器健康狀態
        """
        # 避免頻繁檢查（至少間隔5分鐘）
        if not force and self.last_health_check:
            time_since_last_check = (datetime.now() - self.last_health_check).total_seconds()
            if time_since_last_check < 300:  # 5分鐘
                logger.debug("跳過健康檢查，距離上次檢查時間太短")
                return self.health_status.copy()

        logger.info("開始 MCP 伺服器健康檢查")

        health_results = await self.connector.test_all_servers()
        self.health_status.update(health_results)
        self.last_health_check = datetime.now()

        healthy_count = sum(health_results.values())
        total_count = len(health_results)
        logger.info(f"健康檢查完成: {healthy_count}/{total_count} 伺服器正常")

        return health_results

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
        # 檢查伺服器健康狀態
        if server_name in self.health_status and not self.health_status[server_name]:
            logger.warning(f"伺服器 {server_name} 狀態不健康，嘗試重新初始化")

            # 嘗試重新初始化
            config = global_mcp_config_manager.get_server_config(server_name)
            if config:
                success = await self.connector.register_mcp_server(
                    server_name=config.name,
                    server_type=config.transport,
                    command=config.command,
                    args=config.args,
                    url=config.url,
                    env=config.env,
                    timeout_seconds=config.timeout_seconds,
                )
                self.health_status[server_name] = success

                if not success:
                    return f"❌ 伺服器 {server_name} 無法連接"

        # 執行工具
        return await self.connector.execute_mcp_tool(server_name, tool_name, arguments)

    def get_available_tools(self, server_name: str = None) -> Dict[str, Any]:
        """
        獲取可用工具

        Args:
            server_name: 伺服器名稱（可選）

        Returns:
            Dict[str, Any]: 可用工具資訊
        """
        if server_name:
            return self.connector.list_tools(server_name)
        else:
            return self.connector.list_tools()

    def get_server_status(self, server_name: str = None) -> Dict[str, Any]:
        """
        獲取伺服器狀態

        Args:
            server_name: 伺服器名稱（可選）

        Returns:
            Dict[str, Any]: 伺服器狀態資訊
        """
        if server_name:
            if server_name not in self.health_status:
                return {"error": f"伺服器 {server_name} 未找到"}

            config = global_mcp_config_manager.get_server_config(server_name)
            tools = self.get_available_tools(server_name)

            return {
                "server_name": server_name,
                "healthy": self.health_status.get(server_name, False),
                "config": {
                    "transport": config.transport if config else "unknown",
                    "enabled": config.enabled if config else False,
                    "description": config.description if config else "",
                }
                if config
                else {},
                "tools": tools,
                "last_health_check": self.last_health_check.isoformat()
                if self.last_health_check
                else None,
            }
        else:
            # 返回所有伺服器狀態
            all_status = {}
            for server in self.health_status:
                all_status[server] = self.get_server_status(server)

            return {
                "total_servers": len(self.health_status),
                "healthy_servers": sum(self.health_status.values()),
                "last_health_check": self.last_health_check.isoformat()
                if self.last_health_check
                else None,
                "servers": all_status,
            }

    async def add_server(
        self,
        server_name: str,
        transport: str,
        command: str = None,
        args: List[str] = None,
        url: str = None,
        env: Dict[str, str] = None,
        description: str = "",
        enabled: bool = True,
    ) -> bool:
        """
        添加新的 MCP 伺服器

        Args:
            server_name: 伺服器名稱
            transport: 傳輸方式（stdio 或 sse）
            command: 命令（stdio 類型）
            args: 命令參數
            url: URL（sse 類型）
            env: 環境變數
            description: 描述
            enabled: 是否啟用

        Returns:
            bool: 添加是否成功
        """
        try:
            # 創建配置
            config = MCPServerConfig(
                name=server_name,
                transport=transport,
                command=command,
                args=args or [],
                url=url,
                env=env or {},
                description=description,
                enabled=enabled,
            )

            # 驗證配置
            errors = global_mcp_config_manager.validate_server_config(config)
            if errors:
                logger.error(f"伺服器配置驗證失敗: {errors}")
                return False

            # 添加到配置管理器
            success = global_mcp_config_manager.add_server_config(config)
            if not success:
                return False

            # 如果啟用，嘗試註冊並測試連接
            if enabled:
                register_success = await self.connector.register_mcp_server(
                    server_name=server_name,
                    server_type=transport,
                    command=command,
                    args=args,
                    url=url,
                    env=env,
                )
                self.health_status[server_name] = register_success

                if register_success:
                    logger.info(f"MCP 伺服器添加並註冊成功: {server_name}")
                else:
                    logger.warning(f"MCP 伺服器添加成功但註冊失敗: {server_name}")

                return register_success
            else:
                logger.info(f"MCP 伺服器添加成功（未啟用）: {server_name}")
                return True

        except Exception as e:
            logger.error(f"添加 MCP 伺服器失敗 {server_name}: {e}")
            return False

    def remove_server(self, server_name: str) -> bool:
        """
        移除 MCP 伺服器

        Args:
            server_name: 伺服器名稱

        Returns:
            bool: 移除是否成功
        """
        try:
            # 從配置管理器移除
            config_success = global_mcp_config_manager.remove_server_config(server_name)

            # 從連接器移除（如果存在）
            if server_name in self.connector.servers:
                del self.connector.servers[server_name]

            if server_name in self.connector.available_tools:
                del self.connector.available_tools[server_name]

            # 從健康狀態移除
            if server_name in self.health_status:
                del self.health_status[server_name]

            logger.info(f"MCP 伺服器移除成功: {server_name}")
            return config_success

        except Exception as e:
            logger.error(f"移除 MCP 伺服器失敗 {server_name}: {e}")
            return False

    def enable_server(self, server_name: str) -> bool:
        """啟用伺服器"""
        return global_mcp_config_manager.enable_server(server_name)

    def disable_server(self, server_name: str) -> bool:
        """停用伺服器"""
        success = global_mcp_config_manager.disable_server(server_name)
        if success and server_name in self.health_status:
            self.health_status[server_name] = False
        return success

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """獲取執行歷史"""
        return self.connector.get_execution_history()

    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        connector_stats = self.connector.get_stats()
        config_stats = global_mcp_config_manager.get_config_summary()

        return {
            "connector_stats": connector_stats,
            "config_stats": config_stats,
            "health_status": self.health_status.copy(),
            "last_health_check": self.last_health_check.isoformat()
            if self.last_health_check
            else None,
        }

    async def create_default_setup(self) -> bool:
        """創建預設的 MCP 設定"""
        try:
            default_configs = global_mcp_config_manager.create_default_configs()

            for server_name, config in default_configs.items():
                if server_name not in global_mcp_config_manager.mcp_servers:
                    success = await self.add_server(
                        server_name=config.name,
                        transport=config.transport,
                        command=config.command,
                        args=config.args,
                        url=config.url,
                        env=config.env,
                        description=config.description,
                        enabled=False,  # 預設不啟用，需要手動啟用
                    )

                    if success:
                        logger.info(f"創建預設 MCP 伺服器配置: {server_name}")
                    else:
                        logger.warning(f"創建預設 MCP 伺服器配置失敗: {server_name}")

            return True

        except Exception as e:
            logger.error(f"創建預設 MCP 設定失敗: {e}")
            return False


# 全局 MCP 管理器實例
global_mcp_manager = MCPManager()


# 便利函數
async def initialize_mcp_system() -> Dict[str, bool]:
    """初始化 MCP 系統"""
    return await global_mcp_manager.initialize_all_servers()


async def execute_mcp_tool(
    server_name: str, tool_name: str, arguments: Dict[str, Any] = None
) -> str:
    """執行 MCP 工具"""
    return await global_mcp_manager.execute_mcp_tool(server_name, tool_name, arguments)


def get_mcp_tools(server_name: str = None) -> Dict[str, Any]:
    """獲取 MCP 工具"""
    return global_mcp_manager.get_available_tools(server_name)


def get_mcp_status(server_name: str = None) -> Dict[str, Any]:
    """獲取 MCP 狀態"""
    return global_mcp_manager.get_server_status(server_name)
