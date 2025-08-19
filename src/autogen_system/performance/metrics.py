# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
性能指標收集器

收集和管理系統性能指標。
"""

import time
import psutil
import threading
import statistics
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from src.logging import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """指標類型"""

    LATENCY = "latency"  # 延遲
    THROUGHPUT = "throughput"  # 吞吐量
    MEMORY = "memory"  # 內存使用
    CPU = "cpu"  # CPU使用
    DISK_IO = "disk_io"  # 磁盤IO
    NETWORK_IO = "network_io"  # 網絡IO
    ERROR_RATE = "error_rate"  # 錯誤率
    CONCURRENCY = "concurrency"  # 並發數
    QUEUE_SIZE = "queue_size"  # 隊列大小


@dataclass
class MetricPoint:
    """指標數據點"""

    timestamp: float
    value: Union[float, int]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """性能指標集合"""

    metrics: Dict[str, List[MetricPoint]] = field(default_factory=lambda: defaultdict(list))
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    def add_metric(self, name: str, value: Union[float, int], metadata: Dict[str, Any] = None):
        """添加指標數據點"""
        point = MetricPoint(timestamp=time.time(), value=value, metadata=metadata or {})
        self.metrics[name].append(point)

    def get_latest(self, name: str) -> Optional[MetricPoint]:
        """獲取最新指標值"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        return self.metrics[name][-1]

    def get_average(self, name: str) -> Optional[float]:
        """獲取指標平均值"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        values = [point.value for point in self.metrics[name]]
        return statistics.mean(values)

    def get_percentile(self, name: str, percentile: float) -> Optional[float]:
        """獲取指標百分位數"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        values = sorted([point.value for point in self.metrics[name]])
        if not values:
            return None
        index = int((percentile / 100) * (len(values) - 1))
        return values[index]

    def get_summary(self, name: str) -> Dict[str, float]:
        """獲取指標摘要統計"""
        if name not in self.metrics or not self.metrics[name]:
            return {}

        values = [point.value for point in self.metrics[name]]
        if not values:
            return {}

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "p95": self.get_percentile(name, 95) or 0.0,
            "p99": self.get_percentile(name, 99) or 0.0,
        }


class MetricsCollector:
    """性能指標收集器"""

    def __init__(self, collection_interval: float = 1.0, max_points_per_metric: int = 1000):
        """
        初始化指標收集器

        Args:
            collection_interval: 收集間隔（秒）
            max_points_per_metric: 每個指標的最大數據點數
        """
        self.collection_interval = collection_interval
        self.max_points_per_metric = max_points_per_metric
        self.metrics = PerformanceMetrics()
        self.is_collecting = False
        self.collection_thread = None
        self._lock = threading.Lock()

        # 系統資源監控
        self.process = psutil.Process()

        # 自定義指標
        self.custom_counters = defaultdict(int)
        self.custom_timers = {}

    def start_collection(self):
        """開始收集系統指標"""
        if self.is_collecting:
            return

        self.is_collecting = True
        self.collection_thread = threading.Thread(target=self._collect_system_metrics)
        self.collection_thread.start()
        logger.info("性能指標收集已開始")

    def stop_collection(self):
        """停止收集系統指標"""
        if not self.is_collecting:
            return

        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join()

        self.metrics.end_time = time.time()
        logger.info("性能指標收集已停止")

    def _collect_system_metrics(self):
        """系統指標收集線程"""
        while self.is_collecting:
            try:
                # CPU使用率
                cpu_percent = self.process.cpu_percent()
                self.add_metric("cpu_usage", cpu_percent, {"type": MetricType.CPU.value})

                # 內存使用
                memory_info = self.process.memory_info()
                memory_percent = self.process.memory_percent()
                self.add_metric(
                    "memory_usage_mb",
                    memory_info.rss / 1024 / 1024,
                    {"type": MetricType.MEMORY.value},
                )
                self.add_metric("memory_percent", memory_percent, {"type": MetricType.MEMORY.value})

                # 線程數
                num_threads = self.process.num_threads()
                self.add_metric("thread_count", num_threads, {"type": MetricType.CONCURRENCY.value})

                # 文件描述符數量（如果支持）
                try:
                    num_fds = self.process.num_fds()
                    self.add_metric("file_descriptors", num_fds)
                except AttributeError:
                    # Windows上不支持
                    pass

                # IO統計
                try:
                    io_counters = self.process.io_counters()
                    self.add_metric(
                        "read_bytes", io_counters.read_bytes, {"type": MetricType.DISK_IO.value}
                    )
                    self.add_metric(
                        "write_bytes", io_counters.write_bytes, {"type": MetricType.DISK_IO.value}
                    )
                except AttributeError:
                    # 某些系統上不支持
                    pass

            except Exception as e:
                logger.warning(f"收集系統指標時出錯: {e}")

            time.sleep(self.collection_interval)

    def add_metric(self, name: str, value: Union[float, int], metadata: Dict[str, Any] = None):
        """添加自定義指標"""
        with self._lock:
            self.metrics.add_metric(name, value, metadata)

            # 限制數據點數量
            if len(self.metrics.metrics[name]) > self.max_points_per_metric:
                # 保留最新的數據點
                self.metrics.metrics[name] = self.metrics.metrics[name][
                    -self.max_points_per_metric :
                ]

    def increment_counter(self, name: str, increment: int = 1):
        """遞增計數器"""
        with self._lock:
            self.custom_counters[name] += increment
            self.add_metric(f"counter_{name}", self.custom_counters[name])

    def start_timer(self, name: str):
        """開始計時器"""
        self.custom_timers[name] = time.time()

    def end_timer(self, name: str) -> float:
        """結束計時器並記錄耗時"""
        if name not in self.custom_timers:
            logger.warning(f"計時器 {name} 未啟動")
            return 0.0

        start_time = self.custom_timers.pop(name)
        duration = time.time() - start_time
        self.add_metric(f"timer_{name}", duration, {"type": MetricType.LATENCY.value})
        return duration

    def measure_latency(self, operation_name: str):
        """上下文管理器用於測量延遲"""

        class LatencyMeasurer:
            def __init__(self, collector, name):
                self.collector = collector
                self.name = name
                self.start_time = None

            def __enter__(self):
                self.start_time = time.time()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.start_time:
                    duration = time.time() - self.start_time
                    self.collector.add_metric(
                        f"latency_{self.name}", duration, {"type": MetricType.LATENCY.value}
                    )

        return LatencyMeasurer(self, operation_name)

    def record_throughput(self, operation_name: str, count: int, duration: float):
        """記錄吞吐量"""
        if duration <= 0:
            return

        throughput = count / duration
        self.add_metric(
            f"throughput_{operation_name}",
            throughput,
            {"type": MetricType.THROUGHPUT.value, "count": count, "duration": duration},
        )

    def record_error(self, operation_name: str, error_type: str = "generic"):
        """記錄錯誤"""
        self.increment_counter(f"error_{operation_name}_{error_type}")
        self.add_metric(
            f"error_rate_{operation_name}",
            1,  # 錯誤發生
            {"type": MetricType.ERROR_RATE.value, "error_type": error_type},
        )

    def get_metrics(self) -> PerformanceMetrics:
        """獲取所有指標"""
        with self._lock:
            return self.metrics

    def get_summary_report(self) -> Dict[str, Any]:
        """獲取摘要報告"""
        with self._lock:
            report = {
                "collection_period": {
                    "start_time": self.metrics.start_time,
                    "end_time": self.metrics.end_time or time.time(),
                    "duration": (self.metrics.end_time or time.time()) - self.metrics.start_time,
                },
                "metrics": {},
            }

            for metric_name in self.metrics.metrics:
                summary = self.metrics.get_summary(metric_name)
                if summary:
                    report["metrics"][metric_name] = summary

            return report

    def export_metrics(self, format_type: str = "json") -> Union[str, Dict[str, Any]]:
        """導出指標數據"""
        report = self.get_summary_report()

        if format_type == "json":
            import json

            return json.dumps(report, indent=2)
        elif format_type == "dict":
            return report
        else:
            raise ValueError(f"不支持的導出格式: {format_type}")

    def clear_metrics(self):
        """清除所有指標數據"""
        with self._lock:
            self.metrics = PerformanceMetrics()
            self.custom_counters.clear()
            self.custom_timers.clear()
        logger.info("所有指標數據已清除")


class WorkflowMetricsCollector(MetricsCollector):
    """工作流專用指標收集器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workflow_metrics = defaultdict(lambda: defaultdict(list))

    def record_workflow_start(self, workflow_id: str, workflow_type: str):
        """記錄工作流開始"""
        self.add_metric(
            f"workflow_start_{workflow_type}",
            1,
            {"workflow_id": workflow_id, "workflow_type": workflow_type},
        )
        self.start_timer(f"workflow_{workflow_id}")

    def record_workflow_end(self, workflow_id: str, workflow_type: str, success: bool = True):
        """記錄工作流結束"""
        duration = self.end_timer(f"workflow_{workflow_id}")

        status = "success" if success else "failure"
        self.add_metric(
            f"workflow_end_{workflow_type}_{status}",
            1,
            {"workflow_id": workflow_id, "workflow_type": workflow_type, "duration": duration},
        )

        # 記錄工作流專用指標
        self.workflow_metrics[workflow_type]["durations"].append(duration)
        self.workflow_metrics[workflow_type]["success_count" if success else "failure_count"] += 1

    def record_step_execution(
        self, workflow_id: str, step_id: str, duration: float, success: bool = True
    ):
        """記錄步驟執行"""
        status = "success" if success else "failure"
        self.add_metric(
            f"step_execution_{status}",
            duration,
            {"workflow_id": workflow_id, "step_id": step_id, "type": MetricType.LATENCY.value},
        )

    def record_agent_interaction(self, agent_type: str, operation: str, duration: float):
        """記錄代理交互"""
        self.add_metric(
            f"agent_{agent_type}_{operation}",
            duration,
            {"agent_type": agent_type, "operation": operation, "type": MetricType.LATENCY.value},
        )

    def get_workflow_summary(self) -> Dict[str, Any]:
        """獲取工作流摘要"""
        summary = {}

        for workflow_type, metrics in self.workflow_metrics.items():
            durations = metrics.get("durations", [])
            success_count = metrics.get("success_count", 0)
            failure_count = metrics.get("failure_count", 0)
            total_count = success_count + failure_count

            if durations:
                summary[workflow_type] = {
                    "total_executions": total_count,
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "success_rate": success_count / total_count if total_count > 0 else 0,
                    "avg_duration": statistics.mean(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "median_duration": statistics.median(durations),
                }

        return summary


def create_metrics_collector(
    collection_interval: float = 1.0,
    max_points_per_metric: int = 1000,
    workflow_specific: bool = False,
) -> MetricsCollector:
    """
    創建指標收集器實例

    Args:
        collection_interval: 收集間隔（秒）
        max_points_per_metric: 每個指標的最大數據點數
        workflow_specific: 是否使用工作流專用收集器

    Returns:
        MetricsCollector: 指標收集器實例
    """
    if workflow_specific:
        return WorkflowMetricsCollector(collection_interval, max_points_per_metric)
    else:
        return MetricsCollector(collection_interval, max_points_per_metric)
