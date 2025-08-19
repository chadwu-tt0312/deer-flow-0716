# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
系統優化器

自動分析和優化系統性能。
"""

import asyncio
import gc
import threading
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.logging import get_logger
from .metrics import MetricsCollector, PerformanceMetrics
from .profiler import PerformanceProfiler, ProfileResult

logger = get_logger(__name__)


class OptimizationType(Enum):
    """優化類型"""

    MEMORY = "memory"  # 內存優化
    CPU = "cpu"  # CPU優化
    IO = "io"  # IO優化
    CONCURRENCY = "concurrency"  # 並發優化
    CACHING = "caching"  # 緩存優化
    ALGORITHM = "algorithm"  # 算法優化


@dataclass
class OptimizationSuggestion:
    """優化建議"""

    type: OptimizationType
    priority: int  # 1-10, 10是最高優先級
    description: str
    estimated_improvement: float  # 預期改進百分比
    implementation_effort: str  # "low", "medium", "high"
    code_changes_required: List[str] = field(default_factory=list)


@dataclass
class OptimizationResult:
    """優化結果"""

    suggestions: List[OptimizationSuggestion] = field(default_factory=list)
    performance_baseline: Dict[str, float] = field(default_factory=dict)
    optimization_applied: List[str] = field(default_factory=list)
    improvement_achieved: Dict[str, float] = field(default_factory=dict)
    summary: str = ""


class SystemOptimizer:
    """系統優化器"""

    def __init__(self, metrics_collector: MetricsCollector = None):
        """
        初始化系統優化器

        Args:
            metrics_collector: 指標收集器
        """
        self.metrics_collector = metrics_collector
        self.optimization_history = []
        self.cache_optimization_enabled = True
        self.memory_optimization_enabled = True
        self.concurrency_optimization_enabled = True

    async def analyze_performance(
        self, profiler_result: ProfileResult = None, metrics: PerformanceMetrics = None
    ) -> OptimizationResult:
        """
        分析性能並提供優化建議

        Args:
            profiler_result: 性能分析結果
            metrics: 性能指標

        Returns:
            OptimizationResult: 優化結果
        """
        logger.info("開始性能分析和優化建議生成")

        suggestions = []
        baseline = {}

        # 分析內存使用
        if metrics:
            memory_suggestions = self._analyze_memory_usage(metrics)
            suggestions.extend(memory_suggestions)

            # 分析CPU使用
            cpu_suggestions = self._analyze_cpu_usage(metrics)
            suggestions.extend(cpu_suggestions)

            # 分析並發性能
            concurrency_suggestions = self._analyze_concurrency(metrics)
            suggestions.extend(concurrency_suggestions)

            # 建立基準線
            baseline = self._extract_baseline_metrics(metrics)

        # 分析函數性能
        if profiler_result:
            function_suggestions = self._analyze_function_performance(profiler_result)
            suggestions.extend(function_suggestions)

        # 排序建議按優先級
        suggestions.sort(key=lambda x: x.priority, reverse=True)

        # 生成摘要
        summary = self._generate_optimization_summary(suggestions)

        result = OptimizationResult(
            suggestions=suggestions, performance_baseline=baseline, summary=summary
        )

        logger.info(f"生成了 {len(suggestions)} 個優化建議")
        return result

    def _analyze_memory_usage(self, metrics: PerformanceMetrics) -> List[OptimizationSuggestion]:
        """分析內存使用"""
        suggestions = []

        # 獲取內存指標
        memory_usage = metrics.get_average("memory_usage_mb")
        memory_percent = metrics.get_average("memory_percent")

        if memory_usage and memory_usage > 500:  # 大於500MB
            suggestions.append(
                OptimizationSuggestion(
                    type=OptimizationType.MEMORY,
                    priority=8,
                    description="內存使用量較高，建議優化數據結構和對象生命週期",
                    estimated_improvement=15.0,
                    implementation_effort="medium",
                    code_changes_required=[
                        "檢查大型對象的生命週期",
                        "使用更高效的數據結構",
                        "實現對象池或緩存機制",
                        "增加垃圾回收頻率",
                    ],
                )
            )

        if memory_percent and memory_percent > 80:
            suggestions.append(
                OptimizationSuggestion(
                    type=OptimizationType.MEMORY,
                    priority=9,
                    description="內存使用百分比過高，存在內存洩漏風險",
                    estimated_improvement=25.0,
                    implementation_effort="high",
                    code_changes_required=[
                        "檢查內存洩漏",
                        "優化緩存策略",
                        "實現內存監控和清理機制",
                    ],
                )
            )

        return suggestions

    def _analyze_cpu_usage(self, metrics: PerformanceMetrics) -> List[OptimizationSuggestion]:
        """分析CPU使用"""
        suggestions = []

        cpu_usage = metrics.get_average("cpu_usage")

        if cpu_usage and cpu_usage > 70:  # CPU使用率超過70%
            suggestions.append(
                OptimizationSuggestion(
                    type=OptimizationType.CPU,
                    priority=7,
                    description="CPU使用率較高，建議優化算法和計算邏輯",
                    estimated_improvement=20.0,
                    implementation_effort="medium",
                    code_changes_required=[
                        "優化計算密集型操作",
                        "使用更高效的算法",
                        "實現計算結果緩存",
                        "考慮並行處理",
                    ],
                )
            )

        return suggestions

    def _analyze_concurrency(self, metrics: PerformanceMetrics) -> List[OptimizationSuggestion]:
        """分析並發性能"""
        suggestions = []

        thread_count = metrics.get_average("thread_count")

        if thread_count and thread_count > 50:
            suggestions.append(
                OptimizationSuggestion(
                    type=OptimizationType.CONCURRENCY,
                    priority=6,
                    description="線程數量較多，建議優化並發策略",
                    estimated_improvement=12.0,
                    implementation_effort="medium",
                    code_changes_required=[
                        "使用線程池管理",
                        "減少不必要的線程創建",
                        "使用異步IO替代同步IO",
                        "優化鎖定策略",
                    ],
                )
            )

        # 檢查延遲指標
        latency_metrics = [name for name in metrics.metrics.keys() if "latency_" in name]
        high_latency_operations = []

        for metric_name in latency_metrics:
            avg_latency = metrics.get_average(metric_name)
            if avg_latency and avg_latency > 1.0:  # 大於1秒
                operation_name = metric_name.replace("latency_", "")
                high_latency_operations.append(operation_name)

        if high_latency_operations:
            suggestions.append(
                OptimizationSuggestion(
                    type=OptimizationType.CONCURRENCY,
                    priority=8,
                    description=f"以下操作延遲較高: {', '.join(high_latency_operations)}",
                    estimated_improvement=30.0,
                    implementation_effort="medium",
                    code_changes_required=[
                        "優化高延遲操作",
                        "實現異步處理",
                        "添加操作緩存",
                        "並行化可並行的操作",
                    ],
                )
            )

        return suggestions

    def _analyze_function_performance(
        self, profiler_result: ProfileResult
    ) -> List[OptimizationSuggestion]:
        """分析函數性能"""
        suggestions = []

        if not profiler_result.top_functions:
            return suggestions

        # 分析耗時最長的函數
        top_function = profiler_result.top_functions[0]

        if top_function.percentage > 30:  # 單個函數佔用超過30%時間
            suggestions.append(
                OptimizationSuggestion(
                    type=OptimizationType.ALGORITHM,
                    priority=9,
                    description=f"函數 {top_function.name} 佔用 {top_function.percentage:.1f}% 執行時間",
                    estimated_improvement=top_function.percentage,
                    implementation_effort="high",
                    code_changes_required=[
                        f"優化函數 {top_function.name}",
                        "檢查算法複雜度",
                        "考慮緩存結果",
                        "分解複雜操作",
                    ],
                )
            )

        # 分析高頻調用函數
        high_call_functions = [f for f in profiler_result.top_functions if f.calls > 10000]

        if high_call_functions:
            suggestions.append(
                OptimizationSuggestion(
                    type=OptimizationType.ALGORITHM,
                    priority=7,
                    description=f"發現 {len(high_call_functions)} 個高頻調用函數",
                    estimated_improvement=15.0,
                    implementation_effort="medium",
                    code_changes_required=[
                        "優化高頻調用函數",
                        "減少不必要的函數調用",
                        "內聯簡單函數",
                        "批量處理多個調用",
                    ],
                )
            )

        return suggestions

    def _extract_baseline_metrics(self, metrics: PerformanceMetrics) -> Dict[str, float]:
        """提取基準指標"""
        baseline = {}

        important_metrics = ["memory_usage_mb", "memory_percent", "cpu_usage", "thread_count"]

        for metric_name in important_metrics:
            avg_value = metrics.get_average(metric_name)
            if avg_value is not None:
                baseline[metric_name] = avg_value

        # 添加延遲指標
        latency_metrics = [name for name in metrics.metrics.keys() if "latency_" in name]
        for metric_name in latency_metrics:
            avg_value = metrics.get_average(metric_name)
            if avg_value is not None:
                baseline[metric_name] = avg_value

        return baseline

    def _generate_optimization_summary(self, suggestions: List[OptimizationSuggestion]) -> str:
        """生成優化摘要"""
        if not suggestions:
            return "系統性能良好，暫無優化建議"

        high_priority = [s for s in suggestions if s.priority >= 8]
        medium_priority = [s for s in suggestions if 5 <= s.priority < 8]
        low_priority = [s for s in suggestions if s.priority < 5]

        summary_lines = []
        summary_lines.append(f"總計發現 {len(suggestions)} 個優化機會：")

        if high_priority:
            summary_lines.append(f"- 🔴 高優先級: {len(high_priority)} 項（建議立即處理）")

        if medium_priority:
            summary_lines.append(f"- 🟡 中優先級: {len(medium_priority)} 項（建議近期處理）")

        if low_priority:
            summary_lines.append(f"- 🟢 低優先級: {len(low_priority)} 項（可考慮處理）")

        # 計算預期總改進
        total_improvement = sum(s.estimated_improvement for s in high_priority[:3])  # 前3個高優先級
        if total_improvement > 0:
            summary_lines.append(f"預期性能改進: {total_improvement:.1f}%")

        return "\n".join(summary_lines)

    async def apply_automatic_optimizations(self) -> List[str]:
        """應用自動優化"""
        applied_optimizations = []

        try:
            # 1. 垃圾回收優化
            if self.memory_optimization_enabled:
                await self._optimize_garbage_collection()
                applied_optimizations.append("垃圾回收優化")

            # 2. 緩存優化
            if self.cache_optimization_enabled:
                await self._optimize_caching()
                applied_optimizations.append("緩存策略優化")

            # 3. 並發優化
            if self.concurrency_optimization_enabled:
                await self._optimize_concurrency()
                applied_optimizations.append("並發設置優化")

            logger.info(f"已應用 {len(applied_optimizations)} 項自動優化")

        except Exception as e:
            logger.error(f"應用自動優化時出錯: {e}")

        return applied_optimizations

    async def _optimize_garbage_collection(self):
        """優化垃圾回收"""
        # 強制垃圾回收
        collected = gc.collect()
        logger.info(f"垃圾回收釋放了 {collected} 個對象")

        # 調整垃圾回收閾值
        thresholds = gc.get_threshold()
        new_thresholds = (thresholds[0] // 2, thresholds[1] // 2, thresholds[2] // 2)
        gc.set_threshold(*new_thresholds)
        logger.info(f"調整垃圾回收閾值: {thresholds} -> {new_thresholds}")

    async def _optimize_caching(self):
        """優化緩存策略"""
        # 這裡可以實現緩存清理、大小調整等
        logger.info("執行緩存優化策略")

    async def _optimize_concurrency(self):
        """優化並發設置"""
        # 檢查和優化線程池設置
        try:
            import concurrent.futures

            # 獲取當前系統的CPU核心數
            import os

            cpu_count = os.cpu_count()

            # 建議的線程池大小
            optimal_workers = min(cpu_count * 2, 20)
            logger.info(f"建議線程池大小: {optimal_workers} (CPU核心數: {cpu_count})")

        except Exception as e:
            logger.warning(f"優化並發設置時出錯: {e}")

    def measure_optimization_impact(
        self, before_metrics: PerformanceMetrics, after_metrics: PerformanceMetrics
    ) -> Dict[str, float]:
        """測量優化影響"""
        impact = {}

        # 比較關鍵指標
        key_metrics = ["memory_usage_mb", "cpu_usage", "thread_count"]

        for metric_name in key_metrics:
            before_value = before_metrics.get_average(metric_name)
            after_value = after_metrics.get_average(metric_name)

            if before_value and after_value:
                improvement = ((before_value - after_value) / before_value) * 100
                impact[metric_name] = improvement

        return impact

    def generate_optimization_report(self, result: OptimizationResult) -> str:
        """生成優化報告"""
        lines = []
        lines.append("# 系統優化報告")
        lines.append(f"\n## 🎯 優化摘要")
        lines.append(result.summary)

        if result.suggestions:
            lines.append(f"\n## 📋 詳細建議")

            # 按優先級分組
            high_priority = [s for s in result.suggestions if s.priority >= 8]
            medium_priority = [s for s in result.suggestions if 5 <= s.priority < 8]
            low_priority = [s for s in result.suggestions if s.priority < 5]

            if high_priority:
                lines.append(f"\n### 🔴 高優先級建議")
                for i, suggestion in enumerate(high_priority, 1):
                    lines.append(f"\n**{i}. {suggestion.description}**")
                    lines.append(f"- **預期改進**: {suggestion.estimated_improvement:.1f}%")
                    lines.append(f"- **實施難度**: {suggestion.implementation_effort}")
                    if suggestion.code_changes_required:
                        lines.append("- **代碼變更**:")
                        for change in suggestion.code_changes_required:
                            lines.append(f"  - {change}")

            if medium_priority:
                lines.append(f"\n### 🟡 中優先級建議")
                for i, suggestion in enumerate(medium_priority, 1):
                    lines.append(f"\n**{i}. {suggestion.description}**")
                    lines.append(f"- **預期改進**: {suggestion.estimated_improvement:.1f}%")
                    lines.append(f"- **實施難度**: {suggestion.implementation_effort}")

        # 如果有應用的優化
        if result.optimization_applied:
            lines.append(f"\n## ✅ 已應用優化")
            for optimization in result.optimization_applied:
                lines.append(f"- {optimization}")

        # 如果有改進結果
        if result.improvement_achieved:
            lines.append(f"\n## 📈 優化效果")
            for metric, improvement in result.improvement_achieved.items():
                lines.append(f"- **{metric}**: {improvement:+.1f}%")

        return "\n".join(lines)


def create_optimizer(metrics_collector: MetricsCollector = None) -> SystemOptimizer:
    """
    創建系統優化器實例

    Args:
        metrics_collector: 指標收集器

    Returns:
        SystemOptimizer: 系統優化器實例
    """
    return SystemOptimizer(metrics_collector)
