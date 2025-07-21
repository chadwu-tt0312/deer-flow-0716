# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
import pytest
from unittest.mock import patch

from src.utils.network_config import NetworkConfig


class TestNetworkConfig:
    """測試網路配置工具類別"""

    def setup_method(self):
        """每個測試方法前的設定"""
        self.network_config = NetworkConfig()
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

    def test_should_use_proxy_and_headers_https(self):
        """測試 HTTPS URL 是否需要代理和 headers"""
        url = "https://api.example.com/test"
        assert self.network_config._should_use_proxy_and_headers(url) is True

    def test_should_use_proxy_and_headers_http(self):
        """測試 HTTP URL 不需要代理和 headers"""
        url = "http://api.example.com/test"
        assert self.network_config._should_use_proxy_and_headers(url) is False

    def test_should_use_proxy_and_headers_azure_endpoint(self):
        """測試 Azure OpenAI 端點需要代理和 headers"""
        os.environ["AZURE_OPENAI_ENDPOINT"] = "https://my-resource.openai.azure.com/"
        url = "https://my-resource.openai.azure.com/openai/deployments/gpt-4"
        assert self.network_config._should_use_proxy_and_headers(url) is True

    def test_should_use_proxy_and_headers_basic_model_url(self):
        """測試基本模型 URL 需要代理和 headers"""
        os.environ["BASIC_MODEL__BASE_URL"] = "https://my-model-endpoint.com"
        url = "https://my-model-endpoint.com/v1/chat/completions"
        assert self.network_config._should_use_proxy_and_headers(url) is True

    def test_get_proxies_no_proxy(self):
        """測試沒有設定代理時返回 None"""
        proxies = self.network_config._get_proxies()
        assert proxies is None

    def test_get_proxies_with_http_proxy(self):
        """測試設定 HTTP 代理"""
        os.environ["HTTP_PROXY"] = "http://proxy.example.com:8080"
        proxies = self.network_config._get_proxies()
        assert proxies == {"http": "http://proxy.example.com:8080"}

    def test_get_proxies_with_https_proxy(self):
        """測試設定 HTTPS 代理"""
        os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"
        proxies = self.network_config._get_proxies()
        assert proxies == {"https": "http://proxy.example.com:8080"}

    def test_get_proxies_with_both_proxies(self):
        """測試同時設定 HTTP 和 HTTPS 代理"""
        os.environ["HTTP_PROXY"] = "http://proxy1.example.com:8080"
        os.environ["HTTPS_PROXY"] = "http://proxy2.example.com:8080"
        proxies = self.network_config._get_proxies()
        assert proxies == {
            "http": "http://proxy1.example.com:8080",
            "https": "http://proxy2.example.com:8080",
        }

    def test_get_headers_default_user_agent(self):
        """測試預設 User-Agent"""
        headers = self.network_config._get_headers()
        expected_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/135.0.3179.54"
        assert headers == {"User-Agent": expected_ua}

    def test_get_headers_custom_user_agent(self):
        """測試自訂 User-Agent"""
        custom_ua = "My Custom User Agent"
        os.environ["USER_AGENT"] = custom_ua
        headers = self.network_config._get_headers()
        assert headers == {"User-Agent": custom_ua}

    def test_get_request_config_https_url(self):
        """測試 HTTPS URL 的請求配置"""
        os.environ["HTTP_PROXY"] = "http://proxy.example.com:8080"
        os.environ["USER_AGENT"] = "Custom UA"

        url = "https://api.example.com/test"
        config = self.network_config.get_request_config(url)

        assert "proxies" in config
        assert "headers" in config
        assert config["proxies"] == {"http": "http://proxy.example.com:8080"}
        assert config["headers"] == {"User-Agent": "Custom UA"}

    def test_get_request_config_http_url(self):
        """測試 HTTP URL 的請求配置（不需要代理和 headers）"""
        os.environ["HTTP_PROXY"] = "http://proxy.example.com:8080"
        os.environ["USER_AGENT"] = "Custom UA"

        url = "http://api.example.com/test"
        config = self.network_config.get_request_config(url)

        assert config == {}

    def test_update_headers_existing_headers(self):
        """測試更新現有 headers"""
        os.environ["USER_AGENT"] = "Custom UA"

        existing_headers = {"Content-Type": "application/json"}
        updated_headers = self.network_config.update_headers(existing_headers)

        assert updated_headers == {"Content-Type": "application/json", "User-Agent": "Custom UA"}

    def test_update_headers_no_existing_headers(self):
        """測試沒有現有 headers 時的情況"""
        os.environ["USER_AGENT"] = "Custom UA"

        updated_headers = self.network_config.update_headers()

        assert updated_headers == {"User-Agent": "Custom UA"}

    def test_get_proxies_for_url_https(self):
        """測試為 HTTPS URL 取得代理設定"""
        os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"

        url = "https://api.example.com/test"
        proxies = self.network_config.get_proxies_for_url(url)

        assert proxies == {"https": "http://proxy.example.com:8080"}

    def test_get_proxies_for_url_http(self):
        """測試為 HTTP URL 取得代理設定（返回 None）"""
        os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"

        url = "http://api.example.com/test"
        proxies = self.network_config.get_proxies_for_url(url)

        assert proxies is None

    def test_url_parsing_error(self):
        """測試 URL 解析錯誤的處理"""
        url = "invalid://url"
        result = self.network_config._should_use_proxy_and_headers(url)
        # 應該優雅地處理錯誤並返回 False
        assert result is False

    def test_proxy_caching(self):
        """測試代理設定的快取機制"""
        os.environ["HTTP_PROXY"] = "http://proxy1.example.com:8080"

        # 第一次呼叫
        proxies1 = self.network_config._get_proxies()

        # 修改環境變數
        os.environ["HTTP_PROXY"] = "http://proxy2.example.com:8080"

        # 第二次呼叫應該返回快取的值
        proxies2 = self.network_config._get_proxies()

        assert proxies1 == proxies2
        assert proxies1 == {"http": "http://proxy1.example.com:8080"}

    def test_headers_caching(self):
        """測試 headers 的快取機制"""
        os.environ["USER_AGENT"] = "Custom UA 1"

        # 第一次呼叫
        headers1 = self.network_config._get_headers()

        # 修改環境變數
        os.environ["USER_AGENT"] = "Custom UA 2"

        # 第二次呼叫應該返回快取的值
        headers2 = self.network_config._get_headers()

        assert headers1 == headers2
        assert headers1 == {"User-Agent": "Custom UA 1"}
