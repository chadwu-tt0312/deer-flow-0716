# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
性能分析器

提供詳細的性能分析和瓶頸識別。
"""

import cProfile
import pstats
import io
import time
import functools
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from pathlib import Path

from src.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FunctionProfile:
    """函數性能分析結果"""

    name: str
    calls: int
    total_time: float
    cumulative_time: float
    avg_time: float
    percentage: float


@dataclass
class ProfileResult:
    """性能分析結果"""

    total_time: float
    total_calls: int
    top_functions: List[FunctionProfile] = field(default_factory=list)
    hotspots: List[str] = field(default_factory=list)
    stats_text: str = ""
    raw_stats: Optional[pstats.Stats] = None


class PerformanceProfiler:
    """性能分析器"""

    def __init__(self, enable_profiling: bool = True, sort_by: str = "cumulative", top_n: int = 20):
        """
        初始化性能分析器

        Args:
            enable_profiling: 是否啟用性能分析
            sort_by: 排序方式 ('cumulative', 'time', 'calls')
            top_n: 顯示前N個函數
        """
        self.enable_profiling = enable_profiling
        self.sort_by = sort_by
        self.top_n = top_n
        self.profiler = None
        self.is_profiling = False
        self._lock = threading.Lock()

    def start_profiling(self):
        """開始性能分析"""
        if not self.enable_profiling:
            return

        with self._lock:
            if self.is_profiling:
                logger.warning("性能分析已在運行中")
                return

            self.profiler = cProfile.Profile()
            self.profiler.enable()
            self.is_profiling = True
            logger.info("性能分析已開始")

    def stop_profiling(self) -> Optional[ProfileResult]:
        """停止性能分析並返回結果"""
        if not self.enable_profiling or not self.is_profiling:
            return None

        with self._lock:
            if not self.profiler:
                return None

            self.profiler.disable()
            self.is_profiling = False

            # 分析結果
            result = self._analyze_profile()
            logger.info("性能分析已完成")

            return result

    def _analyze_profile(self) -> ProfileResult:
        """分析性能數據"""
        if not self.profiler:
            return ProfileResult(0.0, 0)

        # 創建統計對象
        stats = pstats.Stats(self.profiler)
        stats.sort_stats(self.sort_by)

        # 獲取統計文本
        stats_text = self._get_stats_text(stats)

        # 分析頂級函數
        top_functions = self._extract_top_functions(stats)

        # 識別熱點
        hotspots = self._identify_hotspots(stats)

        # 總體統計
        total_time = stats.total_tt
        total_calls = stats.total_calls

        return ProfileResult(
            total_time=total_time,
            total_calls=total_calls,
            top_functions=top_functions,
            hotspots=hotspots,
            stats_text=stats_text,
            raw_stats=stats,
        )

    def _get_stats_text(self, stats: pstats.Stats) -> str:
        """獲取統計文本"""
        stream = io.StringIO()
        stats.print_stats(self.top_n, file=stream)
        return stream.getvalue()

    def _extract_top_functions(self, stats: pstats.Stats) -> List[FunctionProfile]:
        """提取頂級函數信息"""
        functions = []

        # 獲取統計數據
        stats_dict = stats.stats

        # 按累積時間排序
        sorted_items = sorted(
            stats_dict.items(),
            key=lambda x: x[1][3],  # 累積時間
            reverse=True,
        )

        for i, ((file, line, func), (cc, nc, tt, ct)) in enumerate(sorted_items[: self.top_n]):
            function_name = f"{file}:{line}({func})"

            # 計算百分比
            percentage = (ct / stats.total_tt * 100) if stats.total_tt > 0 else 0

            # 計算平均時間
            avg_time = tt / cc if cc > 0 else 0

            function_profile = FunctionProfile(
                name=function_name,
                calls=cc,
                total_time=tt,
                cumulative_time=ct,
                avg_time=avg_time,
                percentage=percentage,
            )

            functions.append(function_profile)

        return functions

    def _identify_hotspots(self, stats: pstats.Stats) -> List[str]:
        """識別性能熱點"""
        hotspots = []

        # 查找耗時超過5%的函數
        for func_profile in self._extract_top_functions(stats):
            if func_profile.percentage > 5.0:
                hotspots.append(
                    f"{func_profile.name}: {func_profile.percentage:.1f}% "
                    f"({func_profile.cumulative_time:.3f}s)"
                )

        return hotspots

    def profile_function(self, func: Callable) -> Callable:
        """函數裝飾器用於性能分析"""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.enable_profiling:
                return func(*args, **kwargs)

            profiler = cProfile.Profile()
            profiler.enable()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                profiler.disable()

                # 分析結果
                stats = pstats.Stats(profiler)
                stats.sort_stats(self.sort_by)

                # 記錄分析結果
                logger.info(f"函數 {func.__name__} 性能分析:")
                logger.info(f"總時間: {stats.total_tt:.3f}s")
                logger.info(f"總調用: {stats.total_calls}")

                # 輸出詳細統計
                stream = io.StringIO()
                stats.print_stats(10, file=stream)
                logger.debug(stream.getvalue())

        return wrapper

    def profile_method(self, method_name: str = None):
        """方法裝飾器用於性能分析"""

        def decorator(func: Callable) -> Callable:
            name = method_name or func.__name__

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.enable_profiling:
                    return await func(*args, **kwargs)

                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    duration = end_time - start_time
                    logger.info(f"方法 {name} 執行時間: {duration:.3f}s")

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.enable_profiling:
                    return func(*args, **kwargs)

                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    duration = end_time - start_time
                    logger.info(f"方法 {name} 執行時間: {duration:.3f}s")

            # 檢查是否為異步函數
            import asyncio

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def save_profile(self, filepath: Union[str, Path]):
        """保存性能分析結果到文件"""
        if not self.profiler:
            logger.warning("沒有可保存的性能分析數據")
            return

        filepath = Path(filepath)

        # 保存原始分析數據
        self.profiler.dump_stats(str(filepath.with_suffix(".prof")))

        # 保存文本報告
        stats = pstats.Stats(self.profiler)
        stats.sort_stats(self.sort_by)

        with open(filepath.with_suffix(".txt"), "w") as f:
            stats.print_stats(file=f)

        logger.info(f"性能分析結果已保存到 {filepath}")

    def generate_report(self, result: ProfileResult) -> str:
        """生成性能分析報告"""
        if not result:
            return "無性能分析數據"

        lines = []
        lines.append("# 性能分析報告")
        lines.append(f"\n## 總體統計")
        lines.append(f"- **總執行時間**: {result.total_time:.3f}s")
        lines.append(f"- **總函數調用**: {result.total_calls:,}")
        lines.append(
            f"- **平均調用時間**: {result.total_time / result.total_calls * 1000:.3f}ms"
            if result.total_calls > 0
            else "- **平均調用時間**: N/A"
        )

        # 熱點分析
        if result.hotspots:
            lines.append(f"\n## 🔥 性能熱點")
            for hotspot in result.hotspots:
                lines.append(f"- {hotspot}")

        # 頂級函數
        if result.top_functions:
            lines.append(f"\n## 📊 頂級函數 (前{len(result.top_functions)}個)")
            lines.append("| 函數 | 調用次數 | 總時間(s) | 累積時間(s) | 平均時間(ms) | 佔比(%) |")
            lines.append("|------|----------|-----------|-------------|-------------|---------|")

            for func in result.top_functions[:10]:  # 只顯示前10個
                lines.append(
                    f"| {func.name[:50]}... | {func.calls} | "
                    f"{func.total_time:.3f} | {func.cumulative_time:.3f} | "
                    f"{func.avg_time * 1000:.3f} | {func.percentage:.1f} |"
                )

        # 優化建議
        lines.append(f"\n## 💡 優化建議")
        if result.hotspots:
            lines.append("- 重點關注上述性能熱點函數的優化")

        if result.top_functions and result.top_functions[0].percentage > 20:
            lines.append("- 存在明顯的性能瓶頸，建議優先優化耗時最長的函數")

        if result.total_calls > 1000000:
            lines.append("- 函數調用次數較多，考慮減少不必要的函數調用")

        avg_call_time = result.total_time / result.total_calls if result.total_calls > 0 else 0
        if avg_call_time > 0.001:  # 大於1ms
            lines.append("- 平均函數調用時間較長，考慮優化算法複雜度")

        return "\n".join(lines)


class AsyncProfiler:
    """異步性能分析器"""

    def __init__(self):
        self.call_times = {}
        self.call_counts = {}
        self._lock = threading.Lock()

    def measure_async(self, operation_name: str):
        """異步操作性能測量裝飾器"""

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    duration = end_time - start_time

                    with self._lock:
                        if operation_name not in self.call_times:
                            self.call_times[operation_name] = []
                            self.call_counts[operation_name] = 0

                        self.call_times[operation_name].append(duration)
                        self.call_counts[operation_name] += 1

            return wrapper

        return decorator

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """獲取異步操作統計"""
        stats = {}

        with self._lock:
            for operation, times in self.call_times.items():
                if times:
                    import statistics

                    stats[operation] = {
                        "count": self.call_counts[operation],
                        "total_time": sum(times),
                        "avg_time": statistics.mean(times),
                        "min_time": min(times),
                        "max_time": max(times),
                        "median_time": statistics.median(times),
                    }

        return stats


def create_profiler(
    enable_profiling: bool = True, sort_by: str = "cumulative", top_n: int = 20
) -> PerformanceProfiler:
    """
    創建性能分析器實例

    Args:
        enable_profiling: 是否啟用性能分析
        sort_by: 排序方式
        top_n: 顯示前N個函數

    Returns:
        PerformanceProfiler: 性能分析器實例
    """
    return PerformanceProfiler(enable_profiling, sort_by, top_n)
