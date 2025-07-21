# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
import pytest
from unittest.mock import patch, MagicMock

from src.llms.llm import _create_llm_use_conf


class TestLLMNetworkConfig:
    """測試 LLM 網路配置功能"""

    def setup_method(self):
        """每個測試方法前的設定"""
        # 清除環境變數
        for var in [
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "USER_AGENT",
            "AZURE_OPENAI_ENDPOINT",
            "BASIC_MODEL__BASE_URL",
        ]:
            if var in os.environ:
                del os.environ[var]

    def test_create_llm_with_network_config_https_url(self):
        """測試使用 HTTPS URL 建立 LLM 時的網路配置"""
        # 設定環境變數
        os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"
        os.environ["USER_AGENT"] = "Custom UA"

        # 模擬配置
        conf = {
            "BASIC_MODEL": {
                "base_url": "https://api.openai.com/v1",
                "api_key": "test_key",
                "model": "gpt-4",
            }
        }

        with patch("src.llms.llm.ChatOpenAI") as mock_chat_openai:
            result = _create_llm_use_conf("basic", conf)

            # 檢查是否呼叫了 ChatOpenAI
            mock_chat_openai.assert_called_once()

            # 檢查傳入的參數
            call_args = mock_chat_openai.call_args[1]

            # 應該包含 http_client 和 http_async_client
            assert "http_client" in call_args
            assert "http_async_client" in call_args

            # 檢查是否設定了 HTTP 客戶端
            http_client = call_args["http_client"]
            assert http_client is not None

            # 檢查是否設定了 HTTP 異步客戶端
            http_async_client = call_args["http_async_client"]
            assert http_async_client is not None

    def test_create_llm_with_network_config_azure_endpoint(self):
        """測試使用 Azure 端點建立 LLM 時的網路配置"""
        # 設定環境變數
        os.environ["AZURE_OPENAI_ENDPOINT"] = "https://my-resource.openai.azure.com/"
        os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"
        os.environ["USER_AGENT"] = "Custom UA"

        # 模擬配置
        conf = {"BASIC_MODEL": {"api_key": "test_key", "model": "gpt-4"}}

        with patch("src.llms.llm.AzureChatOpenAI") as mock_azure_chat_openai:
            result = _create_llm_use_conf("basic", conf)

            # 檢查是否呼叫了 AzureChatOpenAI
            mock_azure_chat_openai.assert_called_once()

            # 檢查傳入的參數
            call_args = mock_azure_chat_openai.call_args[1]

            # 應該包含 http_client 和 http_async_client
            assert "http_client" in call_args
            assert "http_async_client" in call_args

    def test_create_llm_without_network_config_http_url(self):
        """測試使用 HTTP URL 建立 LLM 時仍然建立 HTTP 客戶端（但沒有代理配置）"""
        # 設定環境變數
        os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"
        os.environ["USER_AGENT"] = "Custom UA"

        # 模擬配置（使用 HTTP URL）
        conf = {
            "BASIC_MODEL": {
                "base_url": "http://api.example.com/v1",
                "api_key": "test_key",
                "model": "gpt-4",
            }
        }

        with patch("src.llms.llm.ChatOpenAI") as mock_chat_openai:
            result = _create_llm_use_conf("basic", conf)

            # 檢查是否呼叫了 ChatOpenAI
            mock_chat_openai.assert_called_once()

            # 檢查傳入的參數
            call_args = mock_chat_openai.call_args[1]

            # 現在即使沒有網路配置，也會包含 http_client 和 http_async_client（因為我們總是建立它們）
            assert "http_client" in call_args
            assert "http_async_client" in call_args

            # 檢查 HTTP 客戶端是否有 event_hooks（User-Agent hook）
            http_client = call_args["http_client"]
            assert hasattr(http_client, "_event_hooks")
            assert "request" in http_client._event_hooks

    def test_create_llm_with_ssl_verification_disabled(self):
        """測試 SSL 驗證被禁用時的網路配置"""
        # 設定環境變數
        os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"
        os.environ["USER_AGENT"] = "Custom UA"

        # 模擬配置
        conf = {
            "BASIC_MODEL": {
                "base_url": "https://api.openai.com/v1",
                "api_key": "test_key",
                "model": "gpt-4",
                "verify_ssl": False,
            }
        }

        with patch("src.llms.llm.ChatOpenAI") as mock_chat_openai:
            result = _create_llm_use_conf("basic", conf)

            # 檢查是否呼叫了 ChatOpenAI
            mock_chat_openai.assert_called_once()

            # 檢查傳入的參數
            call_args = mock_chat_openai.call_args[1]

            # 應該包含 http_client 和 http_async_client
            assert "http_client" in call_args
            assert "http_async_client" in call_args

            # 檢查是否設定了 HTTP 客戶端
            http_client = call_args["http_client"]
            assert http_client is not None

    def test_create_llm_without_base_url(self):
        """測試沒有 base_url 時的網路配置"""
        # 設定環境變數
        os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"
        os.environ["USER_AGENT"] = "Custom UA"

        # 模擬配置（沒有 base_url）
        conf = {"BASIC_MODEL": {"api_key": "test_key", "model": "gpt-4"}}

        with patch("src.llms.llm.ChatOpenAI") as mock_chat_openai:
            result = _create_llm_use_conf("basic", conf)

            # 檢查是否呼叫了 ChatOpenAI
            mock_chat_openai.assert_called_once()

            # 檢查傳入的參數
            call_args = mock_chat_openai.call_args[1]

            # 現在即使沒有 base_url，也會包含 http_client 和 http_async_client（因為我們總是建立它們）
            assert "http_client" in call_args
            assert "http_async_client" in call_args

            # 檢查 HTTP 客戶端是否有 event_hooks（User-Agent hook）
            http_client = call_args["http_client"]
            assert hasattr(http_client, "_event_hooks")
            assert "request" in http_client._event_hooks

    def test_create_llm_with_azure_endpoint_env_var(self):
        """測試使用環境變數中的 Azure 端點"""
        # 設定環境變數
        os.environ["AZURE_OPENAI_ENDPOINT"] = "https://my-resource.openai.azure.com/"
        os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"
        os.environ["USER_AGENT"] = "Custom UA"

        # 模擬配置（沒有 base_url 或 api_base）
        conf = {"BASIC_MODEL": {"api_key": "test_key", "model": "gpt-4"}}

        with patch("src.llms.llm.AzureChatOpenAI") as mock_azure_chat_openai:
            result = _create_llm_use_conf("basic", conf)

            # 檢查是否呼叫了 AzureChatOpenAI
            mock_azure_chat_openai.assert_called_once()

            # 檢查傳入的參數
            call_args = mock_azure_chat_openai.call_args[1]

            # 應該包含 http_client 和 http_async_client
            assert "http_client" in call_args
            assert "http_async_client" in call_args

    def test_create_llm_with_reasoning_type(self):
        """測試 reasoning 類型的 LLM 配置"""
        # 設定環境變數
        os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"
        os.environ["USER_AGENT"] = "Custom UA"

        # 模擬配置
        conf = {
            "REASONING_MODEL": {
                "api_base": "https://api.openai.com/v1",
                "api_key": "test_key",
                "model": "gpt-4",
            }
        }

        with patch("src.llms.llm.ChatOpenAI") as mock_chat_openai:
            result = _create_llm_use_conf("reasoning", conf)

            # 檢查是否呼叫了 ChatOpenAI
            mock_chat_openai.assert_called_once()

            # 檢查傳入的參數
            call_args = mock_chat_openai.call_args[1]

            # 應該包含 http_client 和 http_async_client
            assert "http_client" in call_args
            assert "http_async_client" in call_args

            # 檢查 api_base 是否正確設定
            assert call_args["api_base"] == "https://api.openai.com/v1"

    def test_create_llm_with_deepseek_api(self):
        """測試 DeepSeek API 的配置"""
        # 設定環境變數
        os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"
        os.environ["USER_AGENT"] = "Custom UA"

        # 模擬配置
        conf = {
            "REASONING_MODEL": {
                "api_base": "https://api.deepseek.com/v1",
                "api_key": "test_key",
                "model": "deepseek-chat",
            }
        }

        with patch("src.llms.llm.ChatDeepSeek") as mock_chat_deepseek:
            result = _create_llm_use_conf("reasoning", conf)

            # 檢查是否呼叫了 ChatDeepSeek
            mock_chat_deepseek.assert_called_once()

            # 檢查傳入的參數
            call_args = mock_chat_deepseek.call_args[1]

            # 應該包含 http_client 和 http_async_client
            assert "http_client" in call_args
            assert "http_async_client" in call_args

    def test_user_agent_hook_injection(self):
        """測試 User-Agent hook 是否正確注入到 HTTP 客戶端"""
        # 設定環境變數
        os.environ["USER_AGENT"] = "Custom Test User Agent"

        # 模擬配置
        conf = {
            "BASIC_MODEL": {
                "base_url": "https://api.openai.com/v1",
                "api_key": "test_key",
                "model": "gpt-4",
            }
        }

        with patch("src.llms.llm.ChatOpenAI") as mock_chat_openai:
            result = _create_llm_use_conf("basic", conf)

            # 檢查是否呼叫了 ChatOpenAI
            mock_chat_openai.assert_called_once()

            # 檢查傳入的參數
            call_args = mock_chat_openai.call_args[1]

            # 應該包含 http_client 和 http_async_client
            assert "http_client" in call_args
            assert "http_async_client" in call_args

            # 檢查 HTTP 客戶端是否有 event_hooks
            http_client = call_args["http_client"]
            assert hasattr(http_client, "_event_hooks")
            assert "request" in http_client._event_hooks
            assert len(http_client._event_hooks["request"]) > 0

            # 檢查 HTTP 異步客戶端是否有 event_hooks
            http_async_client = call_args["http_async_client"]
            assert hasattr(http_async_client, "_event_hooks")
            assert "request" in http_async_client._event_hooks
            assert len(http_async_client._event_hooks["request"]) > 0

    def test_user_agent_hook_without_network_config(self):
        """測試沒有網路配置時是否仍然注入 User-Agent hook"""
        # 設定環境變數
        os.environ["USER_AGENT"] = "Custom Test User Agent"

        # 模擬配置（使用 HTTP URL，不應該套用網路配置）
        conf = {
            "BASIC_MODEL": {
                "base_url": "http://api.example.com/v1",
                "api_key": "test_key",
                "model": "gpt-4",
            }
        }

        with patch("src.llms.llm.ChatOpenAI") as mock_chat_openai:
            result = _create_llm_use_conf("basic", conf)

            # 檢查是否呼叫了 ChatOpenAI
            mock_chat_openai.assert_called_once()

            # 檢查傳入的參數
            call_args = mock_chat_openai.call_args[1]

            # 即使沒有網路配置，也應該包含 http_client 和 http_async_client（因為我們現在總是建立它們）
            assert "http_client" in call_args
            assert "http_async_client" in call_args

            # 檢查 HTTP 客戶端是否有 event_hooks
            http_client = call_args["http_client"]
            assert hasattr(http_client, "_event_hooks")
            assert "request" in http_client._event_hooks
            assert len(http_client._event_hooks["request"]) > 0
