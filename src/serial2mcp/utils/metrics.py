"""
性能指标收集器
监控和收集系统性能相关指标
"""
import time
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    # 串口相关指标
    bytes_sent: int = 0
    bytes_received: int = 0
    send_operations: int = 0
    receive_operations: int = 0
    errors: int = 0

    # 时间相关指标
    total_uptime: float = 0.0
    avg_response_time: float = 0.0

    # 连接相关指标
    connection_timeouts: int = 0
    successful_connections: int = 0
    failed_connections: int = 0

    # 异步消息相关指标
    async_messages_processed: int = 0
    async_buffer_overflows: int = 0

    # 延迟相关指标 (用于监控)
    last_update_time: float = 0.0


class MetricsCollector:
    """性能指标收集器"""

    def __init__(self):
        """初始化性能指标收集器"""
        self.metrics = PerformanceMetrics()
        self.start_time = time.time()
        self.response_times = deque(maxlen=100)  # 最近100次响应时间
        self.lock = threading.Lock()
        self._init_time = time.time()

    def start_timer(self) -> float:
        """
        开始计时

        Returns:
            开始时间戳
        """
        return time.time()

    def end_timer(self, start_time: float) -> float:
        """
        结束计时并记录响应时间

        Args:
            start_time: 开始时间戳

        Returns:
            经过的时间（秒）
        """
        elapsed = time.time() - start_time
        with self.lock:
            self.response_times.append(elapsed)
            # 更新平均响应时间
            if self.response_times:
                self.metrics.avg_response_time = sum(self.response_times) / len(self.response_times)
        return elapsed

    def record_send(self, bytes_count: int) -> None:
        """
        记录发送数据

        Args:
            bytes_count: 发送的字节数
        """
        with self.lock:
            self.metrics.bytes_sent += bytes_count
            self.metrics.send_operations += 1
            self.metrics.last_update_time = time.time()

    def record_receive(self, bytes_count: int) -> None:
        """
        记录接收数据

        Args:
            bytes_count: 接收的字节数
        """
        with self.lock:
            self.metrics.bytes_received += bytes_count
            self.metrics.receive_operations += 1
            self.metrics.last_update_time = time.time()

    def record_error(self) -> None:
        """记录错误"""
        with self.lock:
            self.metrics.errors += 1
            self.metrics.last_update_time = time.time()

    def record_connection_attempt(self, success: bool) -> None:
        """
        记录连接尝试

        Args:
            success: 连接是否成功
        """
        with self.lock:
            if success:
                self.metrics.successful_connections += 1
            else:
                self.metrics.failed_connections += 1
            self.metrics.last_update_time = time.time()

    def record_timeout(self) -> None:
        """记录超时"""
        with self.lock:
            self.metrics.connection_timeouts += 1
            self.metrics.last_update_time = time.time()

    def record_async_message(self) -> None:
        """记录异步消息处理"""
        with self.lock:
            self.metrics.async_messages_processed += 1
            self.metrics.last_update_time = time.time()

    def record_async_overflow(self) -> None:
        """记录异步消息缓冲区溢出"""
        with self.lock:
            self.metrics.async_buffer_overflows += 1
            self.metrics.last_update_time = time.time()

    def get_uptime(self) -> float:
        """
        获取系统运行时间

        Returns:
            系统运行时间（秒）
        """
        return time.time() - self.start_time

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取当前所有性能指标

        Returns:
            性能指标字典
        """
        with self.lock:
            # 更新运行时间
            self.metrics.total_uptime = self.get_uptime()
            metrics_dict = asdict(self.metrics)
            # 添加额外的计算指标
            metrics_dict['current_time'] = time.time()
            if self.metrics.send_operations > 0:
                metrics_dict['avg_bytes_per_send'] = self.metrics.bytes_sent / self.metrics.send_operations
            else:
                metrics_dict['avg_bytes_per_send'] = 0

            if self.metrics.receive_operations > 0:
                metrics_dict['avg_bytes_per_receive'] = self.metrics.bytes_received / self.metrics.receive_operations
            else:
                metrics_dict['avg_bytes_per_receive'] = 0

            return metrics_dict

    def reset_metrics(self) -> None:
        """重置所有指标"""
        with self.lock:
            self.metrics = PerformanceMetrics()
            self.response_times.clear()
            self.start_time = time.time()
            self.metrics.last_update_time = time.time()

    def get_formatted_metrics(self) -> str:
        """
        获取格式化的性能指标字符串

        Returns:
            格式化的性能指标字符串
        """
        metrics = self.get_metrics()
        return json.dumps(metrics, indent=2, ensure_ascii=False)


# 全局性能指标收集器实例
metrics_collector = MetricsCollector()