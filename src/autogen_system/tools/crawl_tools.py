# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 爬蟲工具

提供網頁內容爬取和處理功能。
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse, urljoin

from src.crawler import Crawler
from src.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CrawlResult:
    """爬蟲結果"""

    url: str
    title: str
    content: str
    markdown_content: str
    success: bool
    error: Optional[str]
    crawl_time: float
    timestamp: datetime
    content_length: int


class AutoGenCrawlTool:
    """
    AutoGen 爬蟲工具

    提供網頁內容爬取功能，支援多種格式輸出。
    """

    def __init__(self, timeout_seconds: int = 30, max_content_length: int = 10000):
        """
        初始化爬蟲工具

        Args:
            timeout_seconds: 爬蟲超時時間（秒）
            max_content_length: 最大內容長度
        """
        self.timeout_seconds = timeout_seconds
        self.max_content_length = max_content_length
        self.crawler = Crawler()
        self.crawl_history: List[CrawlResult] = []

        logger.info(
            f"AutoGen 爬蟲工具初始化完成，超時: {timeout_seconds}秒，最大長度: {max_content_length}"
        )

    async def crawl_url(self, url: str, format_type: str = "markdown") -> str:
        """
        爬取網頁內容

        Args:
            url: 要爬取的網址
            format_type: 輸出格式（markdown, text, json）

        Returns:
            str: 爬取結果
        """
        if not self._is_valid_url(url):
            error_msg = f"無效的網址: {url}"
            logger.error(error_msg)
            return self._format_error_result(url, error_msg)

        logger.info(f"開始爬取網址: {url}")
        start_time = asyncio.get_event_loop().time()

        try:
            # 在事件循環中執行爬蟲
            result = await asyncio.wait_for(self._crawl_async(url), timeout=self.timeout_seconds)

            crawl_time = asyncio.get_event_loop().time() - start_time

            # 處理內容長度限制
            if len(result.content) > self.max_content_length:
                result.content = result.content[: self.max_content_length] + "...[內容過長，已截斷]"
                result.markdown_content = (
                    result.markdown_content[: self.max_content_length] + "...[內容過長，已截斷]"
                )

            # 記錄爬蟲歷史
            crawl_result = CrawlResult(
                url=url,
                title=result.title or "無標題",
                content=result.content,
                markdown_content=result.markdown_content,
                success=True,
                error=None,
                crawl_time=crawl_time,
                timestamp=datetime.now(),
                content_length=len(result.content),
            )
            self.crawl_history.append(crawl_result)

            logger.info(f"網頁爬取成功: {url}，耗時: {crawl_time:.2f}秒")
            return self._format_success_result(crawl_result, format_type)

        except asyncio.TimeoutError:
            crawl_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"爬蟲超時（{self.timeout_seconds}秒）"
            logger.error(error_msg)
            return self._format_timeout_result(url, crawl_time)

        except Exception as e:
            crawl_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"爬蟲失敗: {str(e)}"
            logger.error(error_msg)

            # 記錄失敗歷史
            crawl_result = CrawlResult(
                url=url,
                title="",
                content="",
                markdown_content="",
                success=False,
                error=str(e),
                crawl_time=crawl_time,
                timestamp=datetime.now(),
                content_length=0,
            )
            self.crawl_history.append(crawl_result)

            return self._format_error_result(url, error_msg, crawl_time)

    async def _crawl_async(self, url: str) -> Any:
        """非同步爬取"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.crawler.crawl, url)

    def _is_valid_url(self, url: str) -> bool:
        """驗證網址格式"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _format_success_result(self, result: CrawlResult, format_type: str) -> str:
        """格式化成功結果"""
        if format_type == "json":
            return json.dumps(
                {
                    "url": result.url,
                    "title": result.title,
                    "content": result.content,
                    "markdown_content": result.markdown_content,
                    "success": True,
                    "crawl_time": result.crawl_time,
                    "timestamp": result.timestamp.isoformat(),
                    "content_length": result.content_length,
                },
                ensure_ascii=False,
                indent=2,
            )

        elif format_type == "text":
            return f"""網頁爬取成功

網址: {result.url}
標題: {result.title}
內容長度: {result.content_length} 字元
爬取時間: {result.crawl_time:.2f} 秒

內容:
{result.content}
"""

        else:  # markdown (預設)
            return f"""# 🕷️ 網頁爬取結果

**網址:** {result.url}
**標題:** {result.title}
**爬取時間:** {result.crawl_time:.2f} 秒
**內容長度:** {result.content_length} 字元
**時間戳:** {result.timestamp.strftime("%Y-%m-%d %H:%M:%S")}

## 📄 網頁內容

{result.markdown_content}
"""

    def _format_error_result(self, url: str, error_msg: str, crawl_time: float = 0) -> str:
        """格式化錯誤結果"""
        return f"""❌ 網頁爬取失敗

**網址:** {url}
**錯誤訊息:** {error_msg}
**爬取時間:** {crawl_time:.2f} 秒
**時間戳:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**可能的解決方案:**
1. 檢查網址是否正確
2. 確認網站是否可以訪問
3. 檢查網路連接是否正常
4. 嘗試使用其他爬蟲工具
"""

    def _format_timeout_result(self, url: str, crawl_time: float) -> str:
        """格式化超時結果"""
        return f"""⏰ 網頁爬取超時

**網址:** {url}
**設定超時:** {self.timeout_seconds} 秒
**實際耗時:** {crawl_time:.2f} 秒
**時間戳:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**建議:**
1. 增加超時時間設定
2. 檢查網站載入速度
3. 嘗試直接訪問網站
4. 使用其他爬蟲策略
"""

    async def crawl_multiple_urls(self, urls: List[str], format_type: str = "markdown") -> str:
        """
        批量爬取多個網址

        Args:
            urls: 網址列表
            format_type: 輸出格式

        Returns:
            str: 批量爬取結果
        """
        logger.info(f"開始批量爬取 {len(urls)} 個網址")

        results = []
        for i, url in enumerate(urls, 1):
            logger.info(f"爬取進度: {i}/{len(urls)} - {url}")
            result = await self.crawl_url(url, format_type)
            results.append(f"## 網址 {i}: {url}\n\n{result}\n\n---\n")

        combined_result = f"""# 🕷️ 批量網頁爬取結果

**總計網址數:** {len(urls)}
**完成時間:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{"".join(results)}

## 📊 批量爬取統計

{self._get_batch_stats(urls)}
"""

        logger.info(f"批量爬取完成，共處理 {len(urls)} 個網址")
        return combined_result

    def _get_batch_stats(self, urls: List[str]) -> str:
        """獲取批量爬取統計"""
        recent_results = (
            self.crawl_history[-len(urls) :]
            if len(self.crawl_history) >= len(urls)
            else self.crawl_history
        )

        successful = sum(1 for r in recent_results if r.success)
        total_time = sum(r.crawl_time for r in recent_results)
        total_content = sum(r.content_length for r in recent_results)

        return f"""- 成功爬取: {successful}/{len(urls)} ({successful / len(urls) * 100:.1f}%)
- 總耗時: {total_time:.2f} 秒
- 平均耗時: {total_time / len(urls):.2f} 秒/網址
- 總內容長度: {total_content:,} 字元
- 平均內容長度: {total_content // len(urls):,} 字元/網址"""

    def get_crawl_history(self) -> List[Dict[str, Any]]:
        """獲取爬蟲歷史"""
        return [
            {
                "url": result.url,
                "title": result.title,
                "success": result.success,
                "crawl_time": result.crawl_time,
                "content_length": result.content_length,
                "timestamp": result.timestamp.isoformat(),
                "has_error": result.error is not None,
            }
            for result in self.crawl_history
        ]

    def clear_history(self):
        """清除爬蟲歷史"""
        self.crawl_history.clear()
        logger.info("爬蟲歷史已清除")

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        if not self.crawl_history:
            return {
                "total_crawls": 0,
                "successful_crawls": 0,
                "failed_crawls": 0,
                "average_crawl_time": 0,
                "total_content_length": 0,
                "average_content_length": 0,
            }

        successful = sum(1 for r in self.crawl_history if r.success)
        total_time = sum(r.crawl_time for r in self.crawl_history)
        total_content = sum(r.content_length for r in self.crawl_history)

        return {
            "total_crawls": len(self.crawl_history),
            "successful_crawls": successful,
            "failed_crawls": len(self.crawl_history) - successful,
            "success_rate": successful / len(self.crawl_history) * 100,
            "average_crawl_time": total_time / len(self.crawl_history),
            "total_crawl_time": total_time,
            "total_content_length": total_content,
            "average_content_length": total_content / len(self.crawl_history)
            if self.crawl_history
            else 0,
        }


# 便利函數
async def crawl_url(url: str, format_type: str = "markdown") -> str:
    """爬取單一網址"""
    tool = AutoGenCrawlTool()
    return await tool.crawl_url(url, format_type)


async def crawl_multiple_urls(urls: List[str], format_type: str = "markdown") -> str:
    """批量爬取多個網址"""
    tool = AutoGenCrawlTool()
    return await tool.crawl_multiple_urls(urls, format_type)
