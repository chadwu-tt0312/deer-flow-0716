# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
MCP 配置管理器

負責管理 MCP 伺服器的配置和連接資訊。
"""

import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from src.config import load_yaml_config
from src.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MCPServerConfig:
    """MCP 伺服器配置"""

    name: str
    transport: str  # "stdio" or "sse"
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    timeout_seconds: int = 30
    enabled: bool = True
    description: str = ""
    enabled_tools: Optional[List[str]] = None


class MCPConfigManager:
    """
    MCP 配置管理器

    負責載入、管理和驗證 MCP 伺服器配置。
    """

    def __init__(self, config_file: str = "conf.yaml"):
        """
        初始化 MCP 配置管理器

        Args:
            config_file: 配置檔案路徑
        """
        self.config_file = config_file
        self.mcp_servers: Dict[str, MCPServerConfig] = {}
        self._load_mcp_config()

        logger.info(f"MCP 配置管理器初始化完成，載入了 {len(self.mcp_servers)} 個伺服器配置")

    def _load_mcp_config(self):
        """載入 MCP 配置"""
        try:
            # 嘗試從主配置檔案載入
            config = load_yaml_config(self.config_file)
            mcp_config = config.get("MCP", {})

            if mcp_config:
                self._parse_mcp_config(mcp_config)
            else:
                logger.info("主配置檔案中未找到 MCP 配置")

            # 嘗試從 AutoGen 配置檔案載入
            self._load_autogen_mcp_config()

        except Exception as e:
            logger.error(f"載入 MCP 配置失敗: {e}")

    def _parse_mcp_config(self, mcp_config: Dict[str, Any]):
        """解析 MCP 配置"""
        for server_name, server_config in mcp_config.items():
            if isinstance(server_config, dict):
                try:
                    config = MCPServerConfig(
                        name=server_name,
                        transport=server_config.get("transport", "stdio"),
                        command=server_config.get("command"),
                        args=server_config.get("args", []),
                        url=server_config.get("url"),
                        env=server_config.get("env", {}),
                        timeout_seconds=server_config.get("timeout_seconds", 30),
                        enabled=server_config.get("enabled", True),
                        description=server_config.get("description", ""),
                        enabled_tools=server_config.get("enabled_tools"),
                    )

                    self.mcp_servers[server_name] = config
                    logger.info(f"載入 MCP 伺服器配置: {server_name}")

                except Exception as e:
                    logger.error(f"解析 MCP 伺服器配置失敗 {server_name}: {e}")

    def _load_autogen_mcp_config(self):
        """載入 AutoGen 配置檔案中的 MCP 設定"""
        try:
            autogen_config_file = "conf_autogen.yaml"
            if os.path.exists(autogen_config_file):
                autogen_config = load_yaml_config(autogen_config_file)
                tools_config = autogen_config.get("tools", {})
                mcp_servers_config = tools_config.get("mcp_servers", {})

                for server_name, server_config in mcp_servers_config.items():
                    if isinstance(server_config, dict) and server_name not in self.mcp_servers:
                        try:
                            config = MCPServerConfig(
                                name=server_name,
                                transport=server_config.get("transport", "stdio"),
                                command=server_config.get("command"),
                                args=server_config.get("args", []),
                                url=server_config.get("url"),
                                env=server_config.get("env", {}),
                                timeout_seconds=server_config.get("timeout_seconds", 30),
                                enabled=server_config.get("enabled", True),
                                description=server_config.get("description", ""),
                                enabled_tools=server_config.get("enabled_tools"),
                            )

                            self.mcp_servers[server_name] = config
                            logger.info(f"從 AutoGen 配置載入 MCP 伺服器: {server_name}")

                        except Exception as e:
                            logger.error(f"解析 AutoGen MCP 伺服器配置失敗 {server_name}: {e}")

        except Exception as e:
            logger.error(f"載入 AutoGen MCP 配置失敗: {e}")

    def get_server_config(self, server_name: str) -> Optional[MCPServerConfig]:
        """獲取伺服器配置"""
        return self.mcp_servers.get(server_name)

    def get_enabled_servers(self) -> Dict[str, MCPServerConfig]:
        """獲取所有啟用的伺服器配置"""
        return {name: config for name, config in self.mcp_servers.items() if config.enabled}

    def list_servers(self) -> List[str]:
        """列出所有伺服器名稱"""
        return list(self.mcp_servers.keys())

    def add_server_config(self, config: MCPServerConfig) -> bool:
        """添加伺服器配置"""
        try:
            self.mcp_servers[config.name] = config
            logger.info(f"添加 MCP 伺服器配置: {config.name}")
            return True
        except Exception as e:
            logger.error(f"添加 MCP 伺服器配置失敗: {e}")
            return False

    def remove_server_config(self, server_name: str) -> bool:
        """移除伺服器配置"""
        try:
            if server_name in self.mcp_servers:
                del self.mcp_servers[server_name]
                logger.info(f"移除 MCP 伺服器配置: {server_name}")
                return True
            else:
                logger.warning(f"MCP 伺服器配置不存在: {server_name}")
                return False
        except Exception as e:
            logger.error(f"移除 MCP 伺服器配置失敗: {e}")
            return False

    def enable_server(self, server_name: str) -> bool:
        """啟用伺服器"""
        if server_name in self.mcp_servers:
            self.mcp_servers[server_name].enabled = True
            logger.info(f"啟用 MCP 伺服器: {server_name}")
            return True
        return False

    def disable_server(self, server_name: str) -> bool:
        """停用伺服器"""
        if server_name in self.mcp_servers:
            self.mcp_servers[server_name].enabled = False
            logger.info(f"停用 MCP 伺服器: {server_name}")
            return True
        return False

    def validate_server_config(self, config: MCPServerConfig) -> List[str]:
        """驗證伺服器配置"""
        errors = []

        if not config.name:
            errors.append("伺服器名稱不能為空")

        if config.transport not in ["stdio", "sse"]:
            errors.append("傳輸方式必須是 'stdio' 或 'sse'")

        if config.transport == "stdio" and not config.command:
            errors.append("stdio 類型需要指定 command")

        if config.transport == "sse" and not config.url:
            errors.append("sse 類型需要指定 url")

        if config.timeout_seconds <= 0:
            errors.append("超時時間必須大於 0")

        return errors

    def save_config_to_file(self, output_file: str = "config/mcp_servers.json"):
        """將配置保存到檔案"""
        try:
            config_data = {name: asdict(config) for name, config in self.mcp_servers.items()}

            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            logger.info(f"MCP 配置已保存到: {output_file}")
            return True

        except Exception as e:
            logger.error(f"保存 MCP 配置失敗: {e}")
            return False

    def load_config_from_file(self, input_file: str = "config/mcp_servers.json"):
        """從檔案載入配置"""
        try:
            if not os.path.exists(input_file):
                logger.warning(f"MCP 配置檔案不存在: {input_file}")
                return False

            with open(input_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            for server_name, server_config in config_data.items():
                try:
                    config = MCPServerConfig(**server_config)
                    self.mcp_servers[server_name] = config
                    logger.info(f"從檔案載入 MCP 伺服器配置: {server_name}")
                except Exception as e:
                    logger.error(f"載入 MCP 伺服器配置失敗 {server_name}: {e}")

            return True

        except Exception as e:
            logger.error(f"載入 MCP 配置檔案失敗: {e}")
            return False

    def get_config_summary(self) -> Dict[str, Any]:
        """獲取配置摘要"""
        enabled_count = sum(1 for config in self.mcp_servers.values() if config.enabled)
        transport_types = {}

        for config in self.mcp_servers.values():
            transport = config.transport
            transport_types[transport] = transport_types.get(transport, 0) + 1

        return {
            "total_servers": len(self.mcp_servers),
            "enabled_servers": enabled_count,
            "disabled_servers": len(self.mcp_servers) - enabled_count,
            "transport_types": transport_types,
            "server_list": list(self.mcp_servers.keys()),
        }

    def create_default_configs(self) -> Dict[str, MCPServerConfig]:
        """創建預設的 MCP 伺服器配置範例"""
        default_configs = {
            "github_trending": MCPServerConfig(
                name="github_trending",
                transport="stdio",
                command="uvx",
                args=["mcp-github-trending"],
                description="GitHub 趨勢資料伺服器",
                enabled_tools=["get_github_trending_repositories"],
            ),
            "filesystem": MCPServerConfig(
                name="filesystem",
                transport="stdio",
                command="uvx",
                args=["mcp-server-filesystem", "--allowed-path", "./"],
                description="檔案系統操作伺服器",
                enabled_tools=["read_file", "write_file", "list_directory"],
            ),
            "brave_search": MCPServerConfig(
                name="brave_search",
                transport="stdio",
                command="uvx",
                args=["mcp-server-brave-search"],
                env={"BRAVE_API_KEY": "${BRAVE_API_KEY}"},
                description="Brave 搜尋伺服器",
            ),
        }

        return default_configs


# 全局 MCP 配置管理器實例
global_mcp_config_manager = MCPConfigManager()
