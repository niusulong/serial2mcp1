"""
串口驱动并发安全性单元测试
测试串口驱动在多线程环境下的安全性
"""
import pytest
import threading
import time
import queue
from unittest.mock import Mock, patch
from serial2mcp.driver.serial_driver import SerialDriver
from serial2mcp.driver.reader import BackgroundReader
from serial2mcp.utils.exceptions import SerialConnectionError


class TestSerialDriverConcurrency:
    """串口驱动并发安全性测试类"""
    
    def setup_method(self):
        """测试方法执行前的设置"""
        # 创建串口驱动实例并模拟依赖组件
        with patch('serial2mcp.driver.connection_manager.ConnectionManager') as mock_conn_manager, \
             patch('serial2mcp.driver.reader.BackgroundReader') as mock_reader, \
             patch('serial2mcp.driver.processor.DataProcessor') as mock_processor:
            self.driver = SerialDriver()
            self.driver.initialize()

            # 保存模拟对象以便测试使用
            self.driver.connection_manager = mock_conn_manager
            self.driver.reader = mock_reader
            self.driver.processor = mock_processor

        # 模拟连接状态
        self.driver._is_connected = True
        self.driver.connection_manager.is_connected.return_value = True
    
    def test_sync_mode_thread_safety(self):
        """测试同步模式标志的线程安全性"""
        results = []
        errors = []
        
        def toggle_sync_mode(thread_id):
            """在多个线程中切换同步模式"""
            try:
                for i in range(10):
                    if i % 2 == 0:
                        self.driver.enter_sync_mode()
                        results.append((thread_id, 'enter', self.driver._sync_mode.is_set()))
                        time.sleep(0.001)  # 短暂延迟以增加竞争条件
                    else:
                        self.driver.exit_sync_mode()
                        results.append((thread_id, 'exit', self.driver._sync_mode.is_set()))
                        time.sleep(0.001)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # 创建多个线程同时操作同步模式
        threads = []
        for i in range(5):
            t = threading.Thread(target=toggle_sync_mode, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 检查没有发生错误
        assert len(errors) == 0, f"线程操作发生错误: {errors}"
        
        # 验证同步模式标志是线程安全的（虽然状态可能不确定，但不会崩溃）
        assert isinstance(self.driver._sync_mode.is_set(), bool)
    
    def test_queue_thread_safety(self):
        """测试队列操作的线程安全性"""
        errors = []
        
        def producer(queue_type, data_prefix):
            """生产者线程：向队列添加数据"""
            try:
                for i in range(10):
                    data = f"{data_prefix}_{i}".encode()
                    if queue_type == "sync":
                        self.driver._sync_response_queue.put(data)
                    else:  # urc
                        self.driver._urc_queue.put(data)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"生产者错误: {str(e)}")
        
        def consumer(queue_type):
            """消费者线程：从队列获取数据"""
            try:
                for i in range(10):
                    try:
                        if queue_type == "sync":
                            data = self.driver._sync_response_queue.get(timeout=0.1)
                        else:  # urc
                            data = self.driver._urc_queue.get(timeout=0.1)
                    except queue.Empty:
                        pass
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"消费者错误: {str(e)}")
        
        # 创建生产者和消费者线程
        threads = []
        threads.append(threading.Thread(target=producer, args=("sync", "sync_data")))
        threads.append(threading.Thread(target=producer, args=("urc", "urc_data")))
        threads.append(threading.Thread(target=consumer, args=("sync",)))
        threads.append(threading.Thread(target=consumer, args=("urc",)))
        
        # 启动所有线程
        for t in threads:
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 检查没有发生错误
        assert len(errors) == 0, f"队列操作发生错误: {errors}"
    
    def test_concurrent_send_operations(self):
        """测试并发发送操作的安全性"""
        self.driver.connection_manager.write = Mock(return_value=5)
        errors = []
        
        def send_data(thread_id):
            """发送数据的线程函数"""
            try:
                for i in range(5):
                    data = f"thread_{thread_id}_msg_{i}".encode()
                    self.driver.send_data(data)
                    time.sleep(0.001)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # 创建多个线程同时发送数据
        threads = []
        for i in range(3):
            t = threading.Thread(target=send_data, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 检查没有发生错误
        assert len(errors) == 0, f"并发发送操作发生错误: {errors}"
        
        # 验证write方法被正确调用多次
        assert self.driver.connection_manager.write.call_count == 15  # 3线程 * 5次发送
    
    def test_concurrent_sync_mode_operations(self):
        """测试并发同步模式操作"""
        errors = []
        
        def sync_operation(thread_id):
            """执行同步模式操作的线程函数"""
            try:
                for i in range(10):
                    # 进入同步模式
                    self.driver.enter_sync_mode()
                    
                    # 模拟发送和接收操作
                    test_data = f"thread_{thread_id}_data_{i}".encode()
                    self.driver._sync_response_queue.put(test_data)
                    
                    # 尝试接收数据
                    try:
                        # 简单检查队列状态而不实际接收
                        if not self.driver._sync_response_queue.empty():
                            self.driver._sync_response_queue.get_nowait()
                    except queue.Empty:
                        pass
                    
                    # 退出同步模式
                    self.driver.exit_sync_mode()
                    
                    time.sleep(0.001)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # 创建多个线程执行同步操作
        threads = []
        for i in range(3):
            t = threading.Thread(target=sync_operation, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 检查没有发生错误
        assert len(errors) == 0, f"并发同步操作发生错误: {errors}"
    
    def test_background_reader_thread_safety(self):
        """测试后台接收线程与主驱动的交互安全性"""
        errors = []
        
        # 模拟连接管理器
        mock_connection_manager = Mock()
        mock_connection_manager.is_connected.return_value = True
        mock_serial_port = Mock()
        mock_serial_port.in_waiting = 0  # 初始无数据待读
        mock_connection_manager.serial_port = mock_serial_port
        self.driver.connection_manager = mock_connection_manager
        
        # 初始化后台接收器
        background_reader = BackgroundReader()
        background_reader.initialize(
            connection_manager=mock_connection_manager,
            sync_mode_event=self.driver._sync_mode,
            sync_response_queue=self.driver._sync_response_queue,
            urc_queue=self.driver._urc_queue
        )
        
        def simulate_data_arrival():
            """模拟数据到达"""
            try:
                for i in range(5):
                    # 模拟串口有数据可读
                    mock_connection_manager.serial_port.in_waiting = 5
                    mock_connection_manager.read.return_value = f"data_{i}".encode()
                    
                    time.sleep(0.01)  # 模拟时间间隔
                    
                    # 重置为无数据
                    mock_connection_manager.serial_port.in_waiting = 0
            except Exception as e:
                errors.append(f"数据模拟错误: {str(e)}")
        
        def driver_operations():
            """驱动操作线程"""
            try:
                for i in range(5):
                    # 切换同步模式
                    if i % 2 == 0:
                        self.driver.enter_sync_mode()
                    else:
                        self.driver.exit_sync_mode()
                    
                    # 检查URC队列
                    urc_count = self.driver.get_pending_urc_count()
                    
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"驱动操作错误: {str(e)}")
        
        # 启动线程
        data_thread = threading.Thread(target=simulate_data_arrival)
        driver_thread = threading.Thread(target=driver_operations)
        
        data_thread.start()
        driver_thread.start()
        
        # 等待线程完成
        data_thread.join()
        driver_thread.join()
        
        # 检查没有发生错误
        assert len(errors) == 0, f"后台接收线程安全测试发生错误: {errors}"
    
    def test_concurrent_get_urc_messages(self):
        """测试并发获取URC消息的安全性"""
        errors = []
        
        # 添加一些URC消息
        for i in range(10):
            self.driver._urc_queue.put(f"URC_{i}".encode())
        
        def get_urc_messages(thread_id, clear_flag):
            """获取URC消息的线程函数"""
            try:
                for i in range(3):
                    messages = self.driver.get_urc_messages(clear=clear_flag)
                    time.sleep(0.001)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # 创建多个线程同时获取URC消息
        threads = []
        for i in range(3):
            # 交替使用clear=True和clear=False
            clear_flag = i % 2 == 0
            t = threading.Thread(target=get_urc_messages, args=(i, clear_flag))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 检查没有发生错误
        assert len(errors) == 0, f"并发获取URC消息发生错误: {errors}"


class TestBackgroundReaderThreadSafety:
    """后台接收线程安全性测试"""
    
    def test_urc_buffer_thread_safety(self):
        """测试URC缓冲区的线程安全性"""
        reader = BackgroundReader()
        
        errors = []
        
        def modify_buffer(thread_id):
            """修改缓冲区的线程函数"""
            try:
                for i in range(10):
                    # 模拟添加数据到缓冲区
                    data = f"thread_{thread_id}_data_{i}".encode()
                    reader._urc_buffer.extend(data)
                    
                    # 模拟访问缓冲区状态
                    size = len(reader._urc_buffer)
                    time.sleep(0.001)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        def check_idle_timeout(thread_id):
            """检查空闲超时的线程函数"""
            try:
                for i in range(10):
                    # 调用空闲超时检查方法
                    reader._check_urc_idle_timeout()
                    time.sleep(0.001)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # 创建多个线程
        threads = []
        for i in range(3):
            threads.append(threading.Thread(target=modify_buffer, args=(i,)))
            threads.append(threading.Thread(target=check_idle_timeout, args=(i,)))
        
        # 启动所有线程
        for t in threads:
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 检查没有发生错误
        assert len(errors) == 0, f"URC缓冲区线程安全测试发生错误: {errors}"