"""
串口驱动数据发送接收单元测试
测试串口驱动的数据发送和接收功能
"""
import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock, ANY
from serial2mcp.driver.serial_driver import SerialDriver
from serial2mcp.utils.exceptions import (
    SerialConnectionError,
    SerialDataError,
    TimeoutError as SerialTimeoutError
)


class TestSerialDriverDataTransmission:
    """串口驱动数据传输测试类"""
    
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
    
    @patch('serial2mcp.driver.connection_manager.ConnectionManager.write')
    def test_send_data_success(self, mock_write):
        """测试数据发送成功"""
        mock_write.return_value = 5  # 模拟写入5个字节
        
        data = b"hello"
        self.driver.send_data(data)
        
        # 验证写入操作
        mock_write.assert_called_once_with(data)
    
    @patch('serial2mcp.driver.connection_manager.ConnectionManager.write')
    def test_send_data_not_connected(self, mock_write):
        """测试未连接时发送数据"""
        # 设置未连接状态
        self.driver._is_connected = False
        self.driver.connection_manager.is_connected.return_value = False
        
        data = b"hello"
        
        with pytest.raises(SerialConnectionError):
            self.driver.send_data(data)
        
        # 验证没有调用写入操作
        mock_write.assert_not_called()
    
    def test_send_string(self):
        """测试发送字符串"""
        # 模拟write方法
        self.driver.connection_manager.write = Mock(return_value=5)
        
        test_string = "hello"
        self.driver.send_string(test_string)
        
        # 验证字符串被正确编码为字节并发送
        expected_bytes = test_string.encode('utf-8')
        self.driver.connection_manager.write.assert_called_once_with(expected_bytes)
    
    def test_enter_exit_sync_mode(self):
        """测试同步模式切换"""
        initial_state = self.driver._sync_mode.is_set()
        
        # 进入同步模式
        self.driver.enter_sync_mode()
        assert self.driver._sync_mode.is_set() is True
        
        # 退出同步模式
        self.driver.exit_sync_mode()
        assert self.driver._sync_mode.is_set() is False
    
    def test_receive_sync_with_stop_pattern_found(self):
        """测试同步接收模式 - 找到停止模式"""
        # 进入同步模式
        self.driver.enter_sync_mode()
        
        # 模拟向同步响应队列添加数据
        test_data = b"response OK"
        self.driver._sync_response_queue.put(test_data)
        
        # 接收数据，期望找到"OK"
        result = self.driver.receive_sync(timeout=1.0, stop_pattern="OK")
        
        assert result is not None
        assert result['data'] == 'response OK'
        assert result['found_stop_pattern'] is True
    
    def test_receive_sync_timeout(self):
        """测试同步接收模式 - 超时"""
        # 进入同步模式
        self.driver.enter_sync_mode()
        
        # 尝试接收数据，但不放入任何数据到队列，期望超时
        with pytest.raises(SerialTimeoutError):
            self.driver.receive_sync(timeout=0.1, stop_pattern="OK")
    
    def test_receive_for_timeout(self):
        """测试定时接收模式"""
        # 进入同步模式
        self.driver.enter_sync_mode()
        
        # 模拟向同步响应队列添加数据
        test_data = b"response data"
        self.driver._sync_response_queue.put(test_data)
        
        # 按指定时间接收数据
        result = self.driver.receive_for_timeout(duration=0.1)
        
        assert result['data'] == 'response data'
        assert result['bytes_received'] == len(test_data)
    
    def test_receive_no_wait(self):
        """测试无需等待接收模式"""
        result = self.driver.receive_no_wait()
        
        assert result['success'] is True
        assert result['message'] == '数据已发送，不等待响应'
    
    def test_get_async_messages(self):
        """测试获取异步消息"""
        # 模拟向异步队列添加数据
        async_data1 = b"Async message 1"
        async_data2 = b"Async message 2"
        self.driver._async_queue.put(async_data1)
        self.driver._async_queue.put(async_data2)

        # 获取异步消息
        async_messages = self.driver.get_async_messages(clear=True)

        assert len(async_messages) == 2
        assert async_messages[0]['raw_data'] == async_data1
        assert async_messages[1]['raw_data'] == async_data2
    
    def test_get_pending_async_count(self):
        """测试获取待处理异步消息计数"""
        # 添加一些异步消息
        self.driver._async_queue.put(b"Async1")
        self.driver._async_queue.put(b"Async2")

        count = self.driver.get_pending_async_count()
        assert count == 2

        # 清空后计数应为0
        self.driver.get_async_messages(clear=True)
        count = self.driver.get_pending_async_count()
        assert count == 0
    
    @patch('serial2mcp.utils.metrics.metrics_collector')
    def test_performance_metrics_integration(self, mock_metrics):
        """测试性能指标集成"""
        # 发送一些数据
        self.driver.connection_manager.write = Mock(return_value=5)
        data = b"test"
        self.driver.send_data(data)
        
        # 验证性能指标被记录
        mock_metrics.record_send.assert_called_once_with(len(data))
        
        # 模拟接收数据
        self.driver._sync_response_queue.put(data)
        self.driver.receive_for_timeout(duration=0.01)
        
        # 验证接收性能指标被记录
        mock_metrics.record_receive.assert_called()
    
    def test_driver_status(self):
        """测试获取驱动状态"""
        # 设置一些状态值
        self.driver._is_connected = True
        self.driver._sync_mode.set()
        
        # 添加一些URC消息
        self.driver._urc_queue.put(b"URC")
        
        status = self.driver.get_driver_status()
        
        assert status['is_connected'] is True
        assert status['sync_mode'] is True
        assert status['pending_async_count'] == 1