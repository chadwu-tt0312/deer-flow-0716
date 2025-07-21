# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.tools.grounding_bing_search.grounding_bing_search_api_wrapper import (
    GroundingBingSearchAPIWrapper,
    GroundingBingSearchConfig,
)
from src.tools.grounding_bing_search.grounding_bing_search_tool import (
    GroundingBingSearchTool,
)


class TestGroundingBingSearchConfig:
    def test_default_config(self):
        config = GroundingBingSearchConfig()
        assert config.base_url == "http://172.16.128.4:11009/api/projects/searchProject"
        assert config.api_version == "2025-05-15-preview"
        assert config.count == 10
        assert config.market == "zh-tw"
        assert config.set_lang == "zh-hant"

    def test_custom_config(self):
        config = GroundingBingSearchConfig(
            client_id="test_id",
            client_secret="test_secret",
            tenant_id="test_tenant",
            connection_id="test_connection",
            count=5,
            market="en-us",
            set_lang="en",
        )
        assert config.client_id == "test_id"
        assert config.client_secret == "test_secret"
        assert config.tenant_id == "test_tenant"
        assert config.connection_id == "test_connection"
        assert config.count == 5
        assert config.market == "en-us"
        assert config.set_lang == "en"


class TestGroundingBingSearchAPIWrapper:
    @patch("src.tools.grounding_bing_search.grounding_bing_search_api_wrapper.requests.post")
    def test_get_token(self, mock_post):
        # 模擬成功的權杖回應
        mock_response = Mock()
        mock_response.json.return_value = {"access_token": "test_token", "expires_in": 3600}
        mock_post.return_value = mock_response

        config = GroundingBingSearchConfig(
            client_id="test_id", client_secret="test_secret", tenant_id="test_tenant"
        )
        wrapper = GroundingBingSearchAPIWrapper(config)

        token = wrapper._get_token()
        assert token == "test_token"

    @patch("src.tools.grounding_bing_search.grounding_bing_search_api_wrapper.requests.post")
    def test_get_token_failure(self, mock_post):
        mock_post.side_effect = Exception("Token request failed")

        config = GroundingBingSearchConfig(
            client_id="test_id", client_secret="test_secret", tenant_id="test_tenant"
        )
        wrapper = GroundingBingSearchAPIWrapper(config)

        with pytest.raises(Exception, match="Token request failed"):
            wrapper._get_token()

    @patch.object(GroundingBingSearchAPIWrapper, "_get_token")
    @patch("src.tools.grounding_bing_search.grounding_bing_search_api_wrapper.requests.post")
    def test_api_request_post(self, mock_post, mock_get_token):
        mock_get_token.return_value = "test_token"
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        config = GroundingBingSearchConfig()
        wrapper = GroundingBingSearchAPIWrapper(config)

        result = wrapper._api_request("POST", "test/path", {"data": "test"})
        assert result == {"result": "success"}

    @patch.object(GroundingBingSearchAPIWrapper, "_get_token")
    @patch("src.tools.grounding_bing_search.grounding_bing_search_api_wrapper.requests.get")
    def test_api_request_get(self, mock_get, mock_get_token):
        mock_get_token.return_value = "test_token"
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success"}
        mock_get.return_value = mock_response

        config = GroundingBingSearchConfig()
        wrapper = GroundingBingSearchAPIWrapper(config)

        result = wrapper._api_request("GET", "test/path")
        assert result == {"result": "success"}

    @patch.object(GroundingBingSearchAPIWrapper, "_api_request")
    def test_search_success(self, mock_api_request):
        # 模擬 API 回應
        mock_api_request.side_effect = [
            {"id": "assistant_123"},  # create assistant
            {"id": "thread_123"},  # create thread
            {"id": "message_123"},  # add message
            {"id": "run_123"},  # run thread
            {"status": "completed"},  # check run status
            {  # get messages
                "data": [
                    {
                        "role": "assistant",
                        "id": "msg_123",
                        "created_at": "2024-01-01T00:00:00Z",
                        "content": [{"type": "text", "text": {"value": "搜尋結果內容"}}],
                    }
                ]
            },
        ]

        config = GroundingBingSearchConfig(
            client_id="test_id",
            client_secret="test_secret",
            tenant_id="test_tenant",
            connection_id="test_connection",
        )
        wrapper = GroundingBingSearchAPIWrapper(config)

        result = wrapper.search("測試查詢")

        assert result["query"] == "測試查詢"
        assert len(result["results"]) == 1
        assert result["results"][0]["type"] == "text"
        assert result["results"][0]["content"] == "搜尋結果內容"


class TestGroundingBingSearchTool:
    def test_tool_initialization(self):
        tool = GroundingBingSearchTool(max_results=5, market="en-us", set_lang="en")
        assert tool.name == "grounding_bing_search"
        assert tool.max_results == 5
        assert tool.market == "en-us"
        assert tool.set_lang == "en"

    def test_tool_description(self):
        tool = GroundingBingSearchTool()
        assert "Azure OpenAI" in tool.description
        assert "Bing Grounding" in tool.description

    @patch.object(GroundingBingSearchTool, "_run")
    def test_invoke_with_string(self, mock_run):
        mock_run.return_value = [{"title": "Test", "content": "Test content"}]
        tool = GroundingBingSearchTool()

        result = tool.invoke("測試查詢")
        mock_run.assert_called_once_with("測試查詢")

    @patch.object(GroundingBingSearchTool, "_run")
    def test_invoke_with_dict(self, mock_run):
        mock_run.return_value = [{"title": "Test", "content": "Test content"}]
        tool = GroundingBingSearchTool()

        result = tool.invoke({"query": "測試查詢"})
        mock_run.assert_called_once_with("測試查詢")

    def test_invoke_invalid_input(self):
        tool = GroundingBingSearchTool()

        with pytest.raises(ValueError, match="輸入必須是字串或包含 'query' 鍵的字典"):
            tool.invoke(123)

    @patch.object(GroundingBingSearchAPIWrapper, "search")
    def test_run_success(self, mock_search):
        mock_search.return_value = {
            "query": "測試查詢",
            "results": [{"type": "text", "content": "搜尋結果內容"}],
        }

        tool = GroundingBingSearchTool()
        result = tool._run("測試查詢")

        assert len(result) == 1
        assert result[0]["title"] == "Grounding Bing Search Result"
        assert result[0]["content"] == "搜尋結果內容"
        assert result[0]["source"] == "grounding_bing_search"

    @patch.object(GroundingBingSearchAPIWrapper, "search")
    def test_run_failure(self, mock_search):
        mock_search.side_effect = Exception("API 錯誤")

        tool = GroundingBingSearchTool()
        result = tool._run("測試查詢")

        assert "Grounding Bing Search 失敗" in result
