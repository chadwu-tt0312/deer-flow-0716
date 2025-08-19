# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Any, Dict
import os
import httpx

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_deepseek import ChatDeepSeek
from typing import get_args

from src.config import load_yaml_config
from src.config.agents import LLMType
from src.utils.network_config import network_config

# Cache for LLM instances
_llm_cache: dict[LLMType, BaseChatModel] = {}


def _user_agent_hook_sync(request):
    """Synchronous hook to inject User-Agent and User-ID headers into all requests."""
    headers = network_config._get_headers()
    if headers.get("User-Agent"):
        request.headers["User-Agent"] = headers["User-Agent"]
    if headers.get("X-User-ID"):
        request.headers["X-User-ID"] = headers["X-User-ID"]


async def _user_agent_hook_async(request):
    """Asynchronous hook to inject User-Agent and User-ID headers into all requests."""
    headers = network_config._get_headers()
    if headers.get("User-Agent"):
        request.headers["User-Agent"] = headers["User-Agent"]
    if headers.get("X-User-ID"):
        request.headers["X-User-ID"] = headers["X-User-ID"]


def _http_logging_hook_sync(request):
    """Synchronous hook to log HTTP requests."""
    from src.utils.http_logger import http_logger
    from src.logging.context import get_thread_context

    thread_id = get_thread_context()
    request_id = http_logger.log_request(
        method=request.method,
        url=str(request.url),
        headers=dict(request.headers),
        data=request.content,
        timeout=request.extensions.get("timeout"),
        thread_id=thread_id,
    )
    # 將 request_id 儲存到 request 物件中，以便在回應時使用
    request.extensions["request_id"] = request_id


async def _http_logging_hook_async(request):
    """Asynchronous hook to log HTTP requests."""
    from src.utils.http_logger import http_logger
    from src.logging.context import get_thread_context

    thread_id = get_thread_context()
    request_id = http_logger.log_request(
        method=request.method,
        url=str(request.url),
        headers=dict(request.headers),
        data=request.content,
        timeout=request.extensions.get("timeout"),
        thread_id=thread_id,
    )
    # 將 request_id 儲存到 request 物件中，以便在回應時使用
    request.extensions["request_id"] = request_id


def _http_response_hook_sync(response):
    """Synchronous hook to log HTTP responses."""
    from src.utils.http_logger import http_logger
    from src.logging.context import get_thread_context

    thread_id = get_thread_context()
    request_id = response.request.extensions.get("request_id", "")

    # 安全地取得回應內容
    try:
        content = response.content
    except Exception:
        # 如果是 streaming 回應，無法直接存取 content
        content = "[Streaming response - content not available]"

    http_logger.log_response(
        request_id=request_id,
        url=str(response.url),
        status_code=response.status_code,
        headers=dict(response.headers),
        content=content,
        response_time=None,  # httpx 不提供回應時間
        thread_id=thread_id,
    )


async def _http_response_hook_async(response):
    """Asynchronous hook to log HTTP responses."""
    from src.utils.http_logger import http_logger
    from src.logging.context import get_thread_context

    thread_id = get_thread_context()
    request_id = response.request.extensions.get("request_id", "")

    # 安全地取得回應內容
    try:
        content = response.content
    except Exception:
        # 如果是 streaming 回應，無法直接存取 content
        content = "[Streaming response - content not available]"

    http_logger.log_response(
        request_id=request_id,
        url=str(response.url),
        status_code=response.status_code,
        headers=dict(response.headers),
        content=content,
        response_time=None,  # httpx 不提供回應時間
        thread_id=thread_id,
    )


def _get_config_file_path() -> str:
    """Get the path to the configuration file."""
    return str((Path(__file__).parent.parent.parent / "conf.yaml").resolve())


def _get_llm_type_config_keys() -> dict[str, str]:
    """Get mapping of LLM types to their configuration keys."""
    return {
        "reasoning": "REASONING_MODEL",
        "basic": "BASIC_MODEL",
        "vision": "VISION_MODEL",
    }


def _get_env_llm_conf(llm_type: str) -> Dict[str, Any]:
    """
    Get LLM configuration from environment variables.
    Environment variables should follow the format: {LLM_TYPE}__{KEY}
    e.g., BASIC_MODEL__api_key, BASIC_MODEL__base_url
    """
    prefix = f"{llm_type.upper()}_MODEL__"
    conf = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            conf_key = key[len(prefix) :].lower()
            conf[conf_key] = value
    return conf


def _create_llm_use_conf(llm_type: LLMType, conf: Dict[str, Any]) -> BaseChatModel:
    """Create LLM instance using configuration."""
    import warnings

    # 過濾 api_version 警告
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*api_version.*")
        # warnings.filterwarnings("ignore", message=".*transferred to model_kwargs.*")

        llm_type_config_keys = _get_llm_type_config_keys()
        config_key = llm_type_config_keys.get(llm_type)

        if not config_key:
            raise ValueError(f"Unknown LLM type: {llm_type}")

        llm_conf = conf.get(config_key, {})
        if not isinstance(llm_conf, dict):
            raise ValueError(f"Invalid LLM configuration for {llm_type}: {llm_conf}")

        # Get configuration from environment variables
        env_conf = _get_env_llm_conf(llm_type)

        # Merge configurations, with environment variables taking precedence
        merged_conf = {**llm_conf, **env_conf}

        if not merged_conf:
            raise ValueError(f"No configuration found for LLM type: {llm_type}")

        # Add max_retries to handle rate limit errors
        if "max_retries" not in merged_conf:
            merged_conf["max_retries"] = 3

        if llm_type == "reasoning":
            # 保留 api_base，如果沒有則從 base_url 取得
            if "api_base" not in merged_conf and "base_url" in merged_conf:
                merged_conf["api_base"] = merged_conf.pop("base_url")

        # Handle SSL verification settings
        verify_ssl = merged_conf.pop("verify_ssl", True)

        # Get base URL for network configuration
        base_url = (
            merged_conf.get("base_url")
            or merged_conf.get("api_base")
            or os.getenv("AZURE_OPENAI_ENDPOINT")
        )

        # Create custom HTTP client with network configuration
        if base_url and network_config._should_use_proxy_and_headers(base_url):
            # Get network configuration
            request_config = network_config.get_request_config(base_url)

            # Prepare httpx client configuration
            httpx_config = {}
            if not verify_ssl:
                httpx_config["verify"] = False

                # Add proxy configuration if available
                if "proxies" in request_config:
                    proxies = request_config["proxies"]
                    # httpx 使用 transport 來設定代理
                    if "http" in proxies or "https" in proxies:
                        # 使用環境變數設定代理，httpx 會自動讀取
                        if "http" in proxies:
                            os.environ["HTTP_PROXY"] = proxies["http"]
                        if "https" in proxies:
                            os.environ["HTTPS_PROXY"] = proxies["https"]

            # Add headers configuration if available
            if "headers" in request_config:
                # httpx 不支援在 Client 層級設定預設 headers
                # 我們需要在每個請求中手動加入 headers
                # 這裡先記錄 headers，實際使用時需要另外處理
                pass

            # Create HTTP clients with network configuration and User-Agent hook
            http_client = httpx.Client(
                **httpx_config,
                event_hooks={
                    "request": [_user_agent_hook_sync, _http_logging_hook_sync],
                    "response": [_http_response_hook_sync],
                },
            )
            http_async_client = httpx.AsyncClient(
                **httpx_config,
                event_hooks={
                    "request": [_user_agent_hook_async, _http_logging_hook_async],
                    "response": [_http_response_hook_async],
                },
            )
            merged_conf["http_client"] = http_client
            merged_conf["http_async_client"] = http_async_client
        else:
            # Create HTTP clients with User-Agent hook for all cases
            httpx_config = {}
            if not verify_ssl:
                httpx_config["verify"] = False

            http_client = httpx.Client(
                **httpx_config,
                event_hooks={
                    "request": [_user_agent_hook_sync, _http_logging_hook_sync],
                    "response": [_http_response_hook_sync],
                },
            )
            http_async_client = httpx.AsyncClient(
                **httpx_config,
                event_hooks={
                    "request": [_user_agent_hook_async, _http_logging_hook_async],
                    "response": [_http_response_hook_async],
                },
            )
            merged_conf["http_client"] = http_client
            merged_conf["http_async_client"] = http_async_client

        if "azure_endpoint" in merged_conf or os.getenv("AZURE_OPENAI_ENDPOINT"):
            return AzureChatOpenAI(**merged_conf)
        if llm_type == "reasoning":
            api_base = merged_conf.get("api_base")
            if api_base and "deepseek" in api_base:
                return ChatDeepSeek(**merged_conf)
            else:
                return ChatOpenAI(**merged_conf)
        else:
            return ChatOpenAI(**merged_conf)


def get_llm_by_type(
    llm_type: LLMType,
) -> BaseChatModel:
    """
    Get LLM instance by type. Returns cached instance if available.
    """
    if llm_type in _llm_cache:
        return _llm_cache[llm_type]

    conf = load_yaml_config(_get_config_file_path())
    llm = _create_llm_use_conf(llm_type, conf)
    _llm_cache[llm_type] = llm
    # print(f"type = {llm_type}, llm = {llm.__class__.__name__}, conf = {conf}")
    return llm


def get_configured_llm_models() -> dict[str, list[str]]:
    """
    Get all configured LLM models grouped by type.

    Returns:
        Dictionary mapping LLM type to list of configured model names.
    """
    try:
        conf = load_yaml_config(_get_config_file_path())
        llm_type_config_keys = _get_llm_type_config_keys()

        configured_models: dict[str, list[str]] = {}

        for llm_type in get_args(LLMType):
            # Get configuration from YAML file
            config_key = llm_type_config_keys.get(llm_type, "")
            yaml_conf = conf.get(config_key, {}) if config_key else {}

            # Get configuration from environment variables
            env_conf = _get_env_llm_conf(llm_type)

            # Merge configurations, with environment variables taking precedence
            merged_conf = {**yaml_conf, **env_conf}

            # Check if model is configured
            model_name = merged_conf.get("model")
            if model_name:
                configured_models.setdefault(llm_type, []).append(model_name)

        return configured_models

    except Exception as e:
        # Log error and return empty dict to avoid breaking the application
        print(f"Warning: Failed to load LLM configuration: {e}")
        return {}


# In the future, we will use reasoning_llm and vl_llm for different purposes
# reasoning_llm = get_llm_by_type("reasoning")
# vl_llm = get_llm_by_type("vision")


def get_default_model_client():
    """
    獲取默認模型客戶端

    Returns:
        BaseChatModel: 默認的 LLM 實例
    """
    try:
        return get_llm_by_type("reasoning")
    except Exception as e:
        print(f"Warning: Failed to get default model client: {e}")
        # 返回一個模擬客戶端以避免錯誤
        from unittest.mock import Mock

        mock_client = Mock()
        mock_client.complete = Mock(return_value="Mock response")
        return mock_client
