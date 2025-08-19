# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
性能分析器

綜合分析系統性能並提供深度洞察。
"""

import time
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.logging import get_logger
from .metrics import PerformanceMetrics, MetricsCollector
from .profiler import ProfileResult

logger = get_logger(__name__)


class BottleneckType(Enum):
    """瓶頸類型"""

    CPU_BOUND = "cpu_bound"  # CPU密集型瓶頸
    IO_BOUND = "io_bound"  # IO密集型瓶頸
    MEMORY_BOUND = "memory_bound"  # 內存瓶頸
    NETWORK_BOUND = "network_bound"  # 網絡瓶頸
    LOCK_CONTENTION = "lock_contention"  # 鎖競爭
    ALGORITHM = "algorithm"  # 算法瓶頸


@dataclass
class Bottleneck:
    """瓶頸信息"""

    type: BottleneckType
    severity: float  # 0-1, 1是最嚴重
    description: str
    location: str  # 瓶頸位置
    impact: float  # 對整體性能的影響百分比
    evidence: List[str] = field(default_factory=list)  # 證據
    recommendations: List[str] = field(default_factory=list)  # 建議


@dataclass
class PerformanceTrend:
    """性能趨勢"""

    metric_name: str
    trend_direction: str  # "improving", "degrading", "stable"
    change_rate: float  # 變化率 (%/時間單位)
    confidence: float  # 置信度 0-1
    data_points: int  # 數據點數量


@dataclass
class AnalysisResult:
    """分析結果"""

    bottlenecks: List[Bottleneck] = field(default_factory=list)
    trends: List[PerformanceTrend] = field(default_factory=list)
    overall_score: float = 0.0  # 總體性能分數 0-100
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    analysis_timestamp: float = field(default_factory=time.time)


class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self):
        """初始化性能分析器"""
        self.historical_data = []
        self.analysis_history = []

    def analyze_performance(
        self, metrics: PerformanceMetrics, profiler_result: ProfileResult = None
    ) -> AnalysisResult:
        """
        綜合分析性能

        Args:
            metrics: 性能指標
            profiler_result: 性能分析結果

        Returns:
            AnalysisResult: 分析結果
        """
        logger.info("開始綜合性能分析")

        # 識別瓶頸
        bottlenecks = self._identify_bottlenecks(metrics, profiler_result)

        # 分析趨勢
        trends = self._analyze_trends(metrics)

        # 計算總體分數
        overall_score = self._calculate_overall_score(metrics, bottlenecks)

        # 生成洞察
        insights = self._generate_insights(metrics, bottlenecks, trends)

        # 生成建議
        recommendations = self._generate_recommendations(bottlenecks, trends)

        result = AnalysisResult(
            bottlenecks=bottlenecks,
            trends=trends,
            overall_score=overall_score,
            insights=insights,
            recommendations=recommendations,
        )

        # 保存到歷史
        self.analysis_history.append(result)

        logger.info(f"性能分析完成，總體分數: {overall_score:.1f}")
        return result

    def _identify_bottlenecks(
        self, metrics: PerformanceMetrics, profiler_result: ProfileResult = None
    ) -> List[Bottleneck]:
        """識別性能瓶頸"""
        bottlenecks = []

        # 內存瓶頸檢測
        memory_usage = metrics.get_average("memory_usage_mb")
        memory_percent = metrics.get_average("memory_percent")

        if memory_percent and memory_percent > 85:
            severity = min(1.0, (memory_percent - 85) / 15)  # 85-100% 映射到 0-1
            bottlenecks.append(
                Bottleneck(
                    type=BottleneckType.MEMORY_BOUND,
                    severity=severity,
                    description=f"內存使用率達到 {memory_percent:.1f}%",
                    location="系統內存",
                    impact=severity * 30,  # 最多影響30%性能
                    evidence=[
                        f"內存使用率: {memory_percent:.1f}%",
                        f"內存使用量: {memory_usage:.1f}MB" if memory_usage else "",
                    ],
                    recommendations=[
                        "優化內存使用",
                        "檢查內存洩漏",
                        "實施內存緩存策略",
                        "增加系統內存",
                    ],
                )
            )

        # CPU瓶頸檢測
        cpu_usage = metrics.get_average("cpu_usage")
        if cpu_usage and cpu_usage > 80:
            severity = min(1.0, (cpu_usage - 80) / 20)  # 80-100% 映射到 0-1
            bottlenecks.append(
                Bottleneck(
                    type=BottleneckType.CPU_BOUND,
                    severity=severity,
                    description=f"CPU使用率達到 {cpu_usage:.1f}%",
                    location="系統CPU",
                    impact=severity * 40,  # 最多影響40%性能
                    evidence=[f"CPU使用率: {cpu_usage:.1f}%"],
                    recommendations=[
                        "優化計算密集型操作",
                        "使用並行處理",
                        "優化算法複雜度",
                        "考慮CPU升級",
                    ],
                )
            )

        # IO瓶頸檢測（基於延遲）
        io_bottlenecks = self._detect_io_bottlenecks(metrics)
        bottlenecks.extend(io_bottlenecks)

        # 算法瓶頸檢測（基於性能分析結果）
        if profiler_result:
            algo_bottlenecks = self._detect_algorithm_bottlenecks(profiler_result)
            bottlenecks.extend(algo_bottlenecks)

        return bottlenecks

    def _detect_io_bottlenecks(self, metrics: PerformanceMetrics) -> List[Bottleneck]:
        """檢測IO瓶頸"""
        bottlenecks = []

        # 檢查高延遲操作
        high_latency_threshold = 2.0  # 2秒

        for metric_name in metrics.metrics:
            if "latency_" in metric_name:
                avg_latency = metrics.get_average(metric_name)
                p95_latency = metrics.get_percentile(metric_name, 95)

                if avg_latency and avg_latency > high_latency_threshold:
                    operation = metric_name.replace("latency_", "")
                    severity = min(1.0, avg_latency / 10.0)  # 10秒對應最高嚴重性

                    bottlenecks.append(
                        Bottleneck(
                            type=BottleneckType.IO_BOUND,
                            severity=severity,
                            description=f"操作 {operation} 延遲過高",
                            location=f"操作: {operation}",
                            impact=severity * 25,
                            evidence=[
                                f"平均延遲: {avg_latency:.2f}s",
                                f"P95延遲: {p95_latency:.2f}s" if p95_latency else "",
                            ],
                            recommendations=[
                                "優化IO操作",
                                "使用異步處理",
                                "實施操作緩存",
                                "檢查網絡連接",
                            ],
                        )
                    )

        return bottlenecks

    def _detect_algorithm_bottlenecks(self, profiler_result: ProfileResult) -> List[Bottleneck]:
        """檢測算法瓶頸"""
        bottlenecks = []

        if not profiler_result.top_functions:
            return bottlenecks

        # 檢查佔用時間最多的函數
        for func in profiler_result.top_functions[:3]:  # 前3個函數
            if func.percentage > 25:  # 佔用超過25%時間
                severity = func.percentage / 100

                bottlenecks.append(
                    Bottleneck(
                        type=BottleneckType.ALGORITHM,
                        severity=severity,
                        description=f"函數 {func.name} 佔用過多CPU時間",
                        location=func.name,
                        impact=func.percentage,
                        evidence=[
                            f"佔用時間比例: {func.percentage:.1f}%",
                            f"總調用次數: {func.calls}",
                            f"累積時間: {func.cumulative_time:.3f}s",
                        ],
                        recommendations=[
                            "優化算法實現",
                            "減少函數調用次數",
                            "使用更高效的數據結構",
                            "考慮緩存計算結果",
                        ],
                    )
                )

        return bottlenecks

    def _analyze_trends(self, metrics: PerformanceMetrics) -> List[PerformanceTrend]:
        """分析性能趨勢"""
        trends = []

        # 分析關鍵指標的趨勢
        key_metrics = ["memory_usage_mb", "cpu_usage", "thread_count"]

        for metric_name in key_metrics:
            if metric_name in metrics.metrics and len(metrics.metrics[metric_name]) >= 5:
                trend = self._calculate_trend(metric_name, metrics.metrics[metric_name])
                if trend:
                    trends.append(trend)

        # 分析延遲趨勢
        latency_metrics = [name for name in metrics.metrics.keys() if "latency_" in name]
        for metric_name in latency_metrics:
            if len(metrics.metrics[metric_name]) >= 5:
                trend = self._calculate_trend(metric_name, metrics.metrics[metric_name])
                if trend:
                    trends.append(trend)

        return trends

    def _calculate_trend(self, metric_name: str, data_points: List) -> Optional[PerformanceTrend]:
        """計算單個指標的趨勢"""
        if len(data_points) < 5:
            return None

        # 取最近的數據點
        recent_values = [point.value for point in data_points[-10:]]
        timestamps = [point.timestamp for point in data_points[-10:]]

        if len(recent_values) < 3:
            return None

        # 計算線性趨勢
        try:
            # 簡單的線性回歸
            n = len(recent_values)
            x_mean = statistics.mean(range(n))
            y_mean = statistics.mean(recent_values)

            numerator = sum((i - x_mean) * (recent_values[i] - y_mean) for i in range(n))
            denominator = sum((i - x_mean) ** 2 for i in range(n))

            if denominator == 0:
                slope = 0
            else:
                slope = numerator / denominator

            # 計算變化率（每小時）
            time_span = (timestamps[-1] - timestamps[0]) / 3600  # 轉換為小時
            if time_span > 0:
                change_rate = (slope * len(recent_values)) / time_span
            else:
                change_rate = 0

            # 確定趨勢方向
            if abs(change_rate) < 0.01:  # 變化很小
                direction = "stable"
            elif change_rate > 0:
                direction = (
                    "degrading"
                    if "latency" in metric_name or "usage" in metric_name
                    else "improving"
                )
            else:
                direction = (
                    "improving"
                    if "latency" in metric_name or "usage" in metric_name
                    else "degrading"
                )

            # 計算置信度（基於數據點數量和變化一致性）
            confidence = min(1.0, len(recent_values) / 10.0)

            return PerformanceTrend(
                metric_name=metric_name,
                trend_direction=direction,
                change_rate=change_rate,
                confidence=confidence,
                data_points=len(recent_values),
            )

        except Exception as e:
            logger.warning(f"計算趨勢時出錯 {metric_name}: {e}")
            return None

    def _calculate_overall_score(
        self, metrics: PerformanceMetrics, bottlenecks: List[Bottleneck]
    ) -> float:
        """計算總體性能分數"""
        base_score = 100.0

        # 根據瓶頸扣分
        for bottleneck in bottlenecks:
            penalty = bottleneck.severity * bottleneck.impact
            base_score -= penalty

        # 根據系統指標調整
        memory_percent = metrics.get_average("memory_percent")
        if memory_percent:
            if memory_percent > 90:
                base_score -= 20
            elif memory_percent > 80:
                base_score -= 10

        cpu_usage = metrics.get_average("cpu_usage")
        if cpu_usage:
            if cpu_usage > 90:
                base_score -= 15
            elif cpu_usage > 80:
                base_score -= 8

        # 確保分數在0-100範圍內
        return max(0.0, min(100.0, base_score))

    def _generate_insights(
        self,
        metrics: PerformanceMetrics,
        bottlenecks: List[Bottleneck],
        trends: List[PerformanceTrend],
    ) -> List[str]:
        """生成性能洞察"""
        insights = []

        # 瓶頸洞察
        if bottlenecks:
            severe_bottlenecks = [b for b in bottlenecks if b.severity > 0.7]
            if severe_bottlenecks:
                insights.append(f"發現 {len(severe_bottlenecks)} 個嚴重性能瓶頸，需要立即關注")

            bottleneck_types = set(b.type for b in bottlenecks)
            if len(bottleneck_types) > 2:
                insights.append("系統存在多種類型的性能問題，建議系統性優化")
        else:
            insights.append("未發現明顯的性能瓶頸，系統運行良好")

        # 趨勢洞察
        degrading_trends = [
            t for t in trends if t.trend_direction == "degrading" and t.confidence > 0.6
        ]
        if degrading_trends:
            insights.append(f"檢測到 {len(degrading_trends)} 個性能指標呈惡化趨勢")

        improving_trends = [
            t for t in trends if t.trend_direction == "improving" and t.confidence > 0.6
        ]
        if improving_trends:
            insights.append(f"檢測到 {len(improving_trends)} 個性能指標呈改善趨勢")

        # 資源使用洞察
        memory_usage = metrics.get_average("memory_usage_mb")
        if memory_usage:
            if memory_usage > 1000:
                insights.append("內存使用量較高，建議監控內存洩漏")
            elif memory_usage < 100:
                insights.append("內存使用效率良好")

        return insights

    def _generate_recommendations(
        self, bottlenecks: List[Bottleneck], trends: List[PerformanceTrend]
    ) -> List[str]:
        """生成優化建議"""
        recommendations = []

        # 基於瓶頸的建議
        if bottlenecks:
            # 按嚴重性排序
            bottlenecks.sort(key=lambda x: x.severity, reverse=True)

            # 添加最嚴重瓶頸的建議
            most_severe = bottlenecks[0]
            recommendations.extend(most_severe.recommendations[:2])  # 取前2個建議

            # 如果有多個嚴重瓶頸，給出系統性建議
            severe_count = len([b for b in bottlenecks if b.severity > 0.6])
            if severe_count > 2:
                recommendations.append("考慮進行系統架構重構以解決多個性能問題")

        # 基於趨勢的建議
        degrading_trends = [t for t in trends if t.trend_direction == "degrading"]
        if degrading_trends:
            recommendations.append("密切監控性能惡化的指標，及時介入")

        # 通用建議
        if not recommendations:
            recommendations.extend(
                ["維持當前的性能監控", "定期進行性能基準測試", "建立性能警報機制"]
            )

        return recommendations

    def generate_analysis_report(self, result: AnalysisResult) -> str:
        """生成分析報告"""
        lines = []
        lines.append("# 性能分析報告")
        lines.append(
            f"\n**分析時間**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result.analysis_timestamp))}"
        )
        lines.append(f"**總體性能分數**: {result.overall_score:.1f}/100")

        # 性能等級
        if result.overall_score >= 90:
            grade = "優秀 🟢"
        elif result.overall_score >= 75:
            grade = "良好 🟡"
        elif result.overall_score >= 60:
            grade = "一般 🟠"
        else:
            grade = "需要改進 🔴"

        lines.append(f"**性能等級**: {grade}")

        # 瓶頸分析
        if result.bottlenecks:
            lines.append(f"\n## 🔍 瓶頸分析")
            lines.append(f"發現 {len(result.bottlenecks)} 個性能瓶頸：")

            for i, bottleneck in enumerate(result.bottlenecks, 1):
                severity_icon = (
                    "🔴"
                    if bottleneck.severity > 0.7
                    else "🟡"
                    if bottleneck.severity > 0.4
                    else "🟢"
                )
                lines.append(f"\n**{i}. {bottleneck.description}** {severity_icon}")
                lines.append(f"- **類型**: {bottleneck.type.value}")
                lines.append(f"- **嚴重程度**: {bottleneck.severity:.1f}")
                lines.append(f"- **性能影響**: {bottleneck.impact:.1f}%")
                lines.append(f"- **位置**: {bottleneck.location}")

                if bottleneck.evidence:
                    lines.append("- **證據**:")
                    for evidence in bottleneck.evidence:
                        if evidence:  # 過濾空字符串
                            lines.append(f"  - {evidence}")
        else:
            lines.append(f"\n## ✅ 瓶頸分析")
            lines.append("未發現明顯的性能瓶頸")

        # 趨勢分析
        if result.trends:
            lines.append(f"\n## 📈 趨勢分析")

            improving = [t for t in result.trends if t.trend_direction == "improving"]
            degrading = [t for t in result.trends if t.trend_direction == "degrading"]
            stable = [t for t in result.trends if t.trend_direction == "stable"]

            if improving:
                lines.append(f"\n**改善趨勢** 🟢:")
                for trend in improving:
                    lines.append(f"- {trend.metric_name}: {trend.change_rate:+.2f}%/小時")

            if degrading:
                lines.append(f"\n**惡化趨勢** 🔴:")
                for trend in degrading:
                    lines.append(f"- {trend.metric_name}: {trend.change_rate:+.2f}%/小時")

            if stable:
                lines.append(f"\n**穩定趨勢** 🟡:")
                for trend in stable:
                    lines.append(f"- {trend.metric_name}")

        # 洞察
        if result.insights:
            lines.append(f"\n## 💡 關鍵洞察")
            for insight in result.insights:
                lines.append(f"- {insight}")

        # 建議
        if result.recommendations:
            lines.append(f"\n## 🎯 優化建議")
            for i, recommendation in enumerate(result.recommendations, 1):
                lines.append(f"{i}. {recommendation}")

        return "\n".join(lines)


def create_analyzer() -> PerformanceAnalyzer:
    """
    創建性能分析器實例

    Returns:
        PerformanceAnalyzer: 性能分析器實例
    """
    return PerformanceAnalyzer()
