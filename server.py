# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Server script for running the DeerFlow API.
"""

import argparse
import logging
import os
import signal
import sys
import uvicorn
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import DeerFlow logging
from src.deerflow_logging import init_thread_logging, get_thread_logger, set_thread_context

# Initialize DeerFlow logging
init_thread_logging()

# 設定 thread context（使用固定的 thread_id 用於 server）
thread_id = "deerflow_server"
set_thread_context(thread_id)
logger = get_thread_logger()

# 額外控制 watchfiles 的日誌級別，減少檔案監控的日誌輸出
import logging

watchfiles_logger = logging.getLogger("watchfiles")
watchfiles_logger.setLevel(logging.WARNING)
watchfiles_logger.propagate = False


def get_server_config_from_env():
    """Extract host and port from NEXT_PUBLIC_API_URL environment variable."""
    api_url = os.getenv("NEXT_PUBLIC_API_URL")
    if api_url:
        try:
            parsed = urlparse(api_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 8000
            return host, port
        except Exception as e:
            logger.warning(f"Failed to parse NEXT_PUBLIC_API_URL: {e}")
    return None, None


def handle_shutdown(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT"""
    logger.info("Received shutdown signal. Starting graceful shutdown...")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

if __name__ == "__main__":
    # Get server config from environment first
    env_host, env_port = get_server_config_from_env()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the DeerFlow API server")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (default: True except on Windows)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=env_host or "localhost",
        help=f"Host to bind the server to (default: {env_host or 'localhost'}, from NEXT_PUBLIC_API_URL if set)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=env_port or 8000,
        help=f"Port to bind the server to (default: {env_port or 8000}, from NEXT_PUBLIC_API_URL if set)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level (default: info)",
    )

    args = parser.parse_args()

    # Determine reload setting
    reload = False
    if args.reload:
        reload = True

    try:
        if env_host or env_port:
            logger.info(
                f"Using server configuration from NEXT_PUBLIC_API_URL: {os.getenv('NEXT_PUBLIC_API_URL')}"
            )
        logger.info(f"Starting DeerFlow API server on {args.host}:{args.port}")
        uvicorn.run(
            "src.server:app",
            host=args.host,
            port=args.port,
            reload=reload,
            log_level=args.log_level,
            # 優化檔案監控設定，減少 watchfiles 日誌輸出
            reload_dirs=["src"],  # 只監控源碼目錄
            reload_excludes=["*.pyc", "*.log", "logs/*", "__pycache__/*"],  # 排除日誌檔案和快取
            reload_includes=["*.py"],  # 只監控 Python 檔案
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        sys.exit(1)
