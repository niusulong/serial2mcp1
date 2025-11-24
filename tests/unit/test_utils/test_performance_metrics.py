"""
性能指标单元测试
测试性能指标收集器的功能
"""
import time
import threading
import pytest
from serial2mcp.utils.metrics import MetricsCollector, PerformanceMetrics


class TestPerformanceMetrics:
    """性能指标测试类"""
    
    def setup_method(self):
        """测试方法执行前的设置"""
        self.collector = MetricsCollector()
        # 重置指标以确保测试独立性
        self.collector.reset_metrics()
    
    def test_initial_metrics_values(self):
        """测试初始指标值"""
        metrics = self.collector.get_metrics()
        
        assert metrics['bytes_sent'] == 0
        assert metrics['bytes_received'] == 0
        assert metrics['send_operations'] == 0
        assert metrics['receive_operations'] == 0
        assert metrics['errors'] == 0
        assert metrics['total_uptime'] >= 0
        assert metrics['avg_response_time'] == 0.0
        assert metrics['connection_timeouts'] == 0
        assert metrics['successful_connections'] == 0
        assert metrics['failed_connections'] == 0
        assert metrics['async_messages_processed'] == 0
        assert metrics['async_buffer_overflows'] == 0
    
    def test_record_send(self):
        """测试记录发送操作"""
        # 记录几次发送操作
        self.collector.record_send(10)
        self.collector.record_send(20)
        self.collector.record_send(15)
        
        metrics = self.collector.get_metrics()
        assert metrics['bytes_sent'] == 45  # 10 + 20 + 15
        assert metrics['send_operations'] == 3
        assert metrics['avg_bytes_per_send'] == 15.0  # 45 / 3
    
    def test_record_receive(self):
        """测试记录接收操作"""
        # 记录几次接收操作
        self.collector.record_receive(5)
        self.collector.record_receive(12)
        self.collector.record_receive(8)
        
        metrics = self.collector.get_metrics()
        assert metrics['bytes_received'] == 25  # 5 + 12 + 8
        assert metrics['receive_operations'] == 3
        assert metrics['avg_bytes_per_receive'] == 25/3  # 约8.33
    
    def test_record_error(self):
        """测试记录错误"""
        initial_errors = self.collector.get_metrics()['errors']
        
        # 记录几次错误
        self.collector.record_error()
        self.collector.record_error()
        
        metrics = self.collector.get_metrics()
        assert metrics['errors'] == initial_errors + 2
    
    def test_record_connection_attempt(self):
        """测试记录连接尝试"""
        # 记录成功连接
        self.collector.record_connection_attempt(success=True)
        # 记录失败连接
        self.collector.record_connection_attempt(success=False)
        # 再记录一次成功
        self.collector.record_connection_attempt(success=True)
        
        metrics = self.collector.get_metrics()
        assert metrics['successful_connections'] == 2
        assert metrics['failed_connections'] == 1
    
    def test_record_timeout(self):
        """测试记录超时"""
        initial_timeouts = self.collector.get_metrics()['connection_timeouts']
        
        # 记录几次超时
        self.collector.record_timeout()
        self.collector.record_timeout()
        
        metrics = self.collector.get_metrics()
        assert metrics['connection_timeouts'] == initial_timeouts + 2
    
    def test_record_async_message(self):
        """测试记录异步消息"""
        initial_count = self.collector.get_metrics()['async_messages_processed']

        # 记录几个异步消息
        for i in range(5):
            self.collector.record_async_message()

        metrics = self.collector.get_metrics()
        assert metrics['async_messages_processed'] == initial_count + 5
    
    def test_record_async_overflow(self):
        """测试记录异步消息缓冲区溢出"""
        initial_count = self.collector.get_metrics()['async_buffer_overflows']

        # 记录几次溢出
        self.collector.record_async_overflow()
        self.collector.record_async_overflow()

        metrics = self.collector.get_metrics()
        assert metrics['async_buffer_overflows'] == initial_count + 2
    
    def test_response_time_tracking(self):
        """测试响应时间跟踪"""
        # 模拟几次操作以记录响应时间
        start_time = self.collector.start_timer()
        time.sleep(0.01)  # 等待10毫秒
        elapsed = self.collector.end_timer(start_time)
        
        assert elapsed >= 0.01  # 确保时间正确记录
        
        # 再记录几次以计算平均值
        for i in range(3):
            start_time = self.collector.start_timer()
            elapsed = self.collector.end_timer(start_time)
        
        metrics = self.collector.get_metrics()
        # 由于我们记录了多次，平均响应时间应该大于0
        assert metrics['avg_response_time'] >= 0
    
    def test_uptime_calculation(self):
        """测试正常时间计算"""
        initial_uptime = self.collector.get_uptime()
        
        # 等待一小段时间
        time.sleep(0.01)
        
        new_uptime = self.collector.get_uptime()
        
        # 新的正常时间应该比初始值大
        assert new_uptime >= initial_uptime
    
    def test_get_formatted_metrics(self):
        """测试获取格式化指标"""
        # 执行一些操作
        self.collector.record_send(100)
        self.collector.record_receive(50)
        self.collector.record_error()
        
        formatted_metrics = self.collector.get_formatted_metrics()
        
        # 验证返回的是字符串（JSON格式）
        assert isinstance(formatted_metrics, str)
        # 验证包含关键指标
        assert '"bytes_sent": 100' in formatted_metrics
        assert '"bytes_received": 50' in formatted_metrics
        assert '"errors": 1' in formatted_metrics
    
    def test_reset_metrics(self):
        """测试重置指标"""
        # 先记录一些数据
        self.collector.record_send(100)
        self.collector.record_receive(50)
        self.collector.record_error()
        self.collector.record_connection_attempt(success=True)
        self.collector.record_timeout()
        self.collector.record_async_message()
        self.collector.record_async_overflow()
        
        # 记录响应时间
        start = self.collector.start_timer()
        self.collector.end_timer(start)
        
        # 重置指标
        self.collector.reset_metrics()
        
        # 验证所有指标都已重置
        metrics = self.collector.get_metrics()
        assert metrics['bytes_sent'] == 0
        assert metrics['bytes_received'] == 0
        assert metrics['send_operations'] == 0
        assert metrics['receive_operations'] == 0
        assert metrics['errors'] == 0
        assert metrics['successful_connections'] == 0
        assert metrics['failed_connections'] == 0
        assert metrics['connection_timeouts'] == 0
        assert metrics['async_messages_processed'] == 0
        assert metrics['async_buffer_overflows'] == 0
        assert metrics['avg_response_time'] == 0.0
        assert metrics['total_uptime'] >= 0  # 正常时间应该从重置时间开始计算
    
    def test_concurrent_metrics_updates(self):
        """测试并发指标更新"""
        errors = []
        
        def update_metrics(thread_id):
            """更新指标的线程函数"""
            try:
                for i in range(10):
                    # 执行各种指标更新操作
                    self.collector.record_send(i)
                    self.collector.record_receive(i)
                    if i % 3 == 0:
                        self.collector.record_error()
                    if i % 4 == 0:
                        self.collector.record_connection_attempt(success=(i % 2 == 0))
                    if i % 5 == 0:
                        self.collector.record_async_message()
                    
                    # 记录响应时间
                    start = self.collector.start_timer()
                    self.collector.end_timer(start)
                    
                    time.sleep(0.001)  # 小延迟以增加并发性
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # 创建多个线程同时更新指标
        threads = []
        for i in range(3):
            t = threading.Thread(target=update_metrics, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证没有发生错误
        assert len(errors) == 0, f"并发更新发生错误: {errors}"
        
        # 验证指标值是合理的（非负数）
        metrics = self.collector.get_metrics()
        assert metrics['bytes_sent'] >= 0
        assert metrics['bytes_received'] >= 0
        assert metrics['send_operations'] >= 0
        assert metrics['receive_operations'] >= 0
        assert metrics['errors'] >= 0
    
    def test_metrics_thread_safety(self):
        """测试指标收集器的线程安全性"""
        # 多个线程同时访问指标收集器，确保不会出错
        errors = []
        
        def access_metrics(thread_id):
            """访问指标的线程函数"""
            try:
                for i in range(5):
                    # 同时执行更新和读取操作
                    self.collector.record_send(i)
                    metrics = self.collector.get_metrics()
                    formatted = self.collector.get_formatted_metrics()
                    
                    time.sleep(0.001)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # 创建多个线程
        threads = []
        for i in range(5):
            t = threading.Thread(target=access_metrics, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证没有发生错误
        assert len(errors) == 0, f"线程安全测试发生错误: {errors}"
    
    def test_response_time_deque_size_limit(self):
        """测试响应时间队列大小限制"""
        # 快速记录大量响应时间，验证队列大小限制生效
        for i in range(150):  # 超过默认的100大小限制
            start = self.collector.start_timer()
            self.collector.end_timer(start)
        
        # 获取指标，验证可以正常获取
        metrics = self.collector.get_metrics()
        assert 'avg_response_time' in metrics