"""
连接管理器单元测试
测试串口连接管理器的各项功能
"""
import pytest
import serial
from unittest.mock import Mock, patch, MagicMock
from serial2mcp.driver.connection_manager import ConnectionManager
from serial2mcp.utils.exceptions import SerialConnectionError


class TestConnectionManager:
    """连接管理器测试类"""
    
    def setup_method(self):
        """测试方法执行前的设置"""
        self.connection_manager = ConnectionManager()
        self.connection_manager.initialize()
    
    def test_initialize(self):
        """测试连接管理器初始化"""
        # 初始化已在setup_method中完成
        assert self.connection_manager.logger is not None
        assert self.connection_manager.serial_port is None
        assert self.connection_manager._is_connected is False
    
    @patch('serial.Serial')
    def test_connect_success(self, mock_serial):
        """测试串口连接成功"""
        mock_serial_instance = Mock()
        mock_serial_instance.is_open = True
        mock_serial.return_value = mock_serial_instance
        
        port = "COM1"
        baudrate = 9600
        
        self.connection_manager.connect(port, baudrate)
        
        # 验证串口对象被正确创建
        mock_serial.assert_called_once_with(
            port=port,
            baudrate=baudrate,
            bytesize=self.connection_manager.config.serial.bytesize,
            parity=self.connection_manager.config.serial.parity,
            stopbits=self.connection_manager.config.serial.stopbits,
            timeout=self.connection_manager.config.serial.timeout,
            xonxoff=self.connection_manager.config.serial.xonxoff,
            rtscts=self.connection_manager.config.serial.rtscts,
            dsrdtr=self.connection_manager.config.serial.dsrdtr
        )
        
        assert self.connection_manager._is_connected is True
        assert self.connection_manager.serial_port == mock_serial_instance
    
    @patch('serial.Serial')
    def test_connect_serial_exception(self, mock_serial):
        """测试串口连接时发生SerialException"""
        mock_serial.side_effect = serial.SerialException("连接失败")
        
        with pytest.raises(SerialConnectionError):
            self.connection_manager.connect("COM1", 9600)
    
    @patch('serial.Serial')
    def test_disconnect_when_connected(self, mock_serial):
        """测试断开已连接的串口"""
        mock_serial_instance = Mock()
        mock_serial_instance.is_open = True
        mock_serial.return_value = mock_serial_instance
        
        # 先连接
        self.connection_manager.connect("COM1", 9600)
        
        # 然后断开
        self.connection_manager.disconnect()
        
        # 验证close方法被调用
        mock_serial_instance.close.assert_called_once()
        assert self.connection_manager._is_connected is False
        assert self.connection_manager.serial_port is None
    
    def test_disconnect_when_not_connected(self):
        """测试断开未连接的串口"""
        # 初始状态就是未连接
        assert self.connection_manager.serial_port is None
        assert self.connection_manager._is_connected is False
        
        # 断开操作不应引发异常
        self.connection_manager.disconnect()
    
    @patch('serial.Serial')
    def test_write_when_connected(self, mock_serial):
        """测试连接状态下写入数据"""
        mock_serial_instance = Mock()
        mock_serial_instance.is_open = True
        mock_serial_instance.write.return_value = 5  # 返回写入字节数
        mock_serial.return_value = mock_serial_instance
        
        # 连接
        self.connection_manager.connect("COM1", 9600)
        
        # 写入数据
        data = b"hello"
        result = self.connection_manager.write(data)
        
        # 验证写入操作
        mock_serial_instance.write.assert_called_once_with(data)
        mock_serial_instance.flush.assert_called_once()
        assert result == 5
    
    def test_write_when_not_connected(self):
        """测试未连接状态下写入数据"""
        data = b"hello"
        
        with pytest.raises(SerialConnectionError):
            self.connection_manager.write(data)
    
    @patch('serial.Serial')
    def test_read_when_connected(self, mock_serial):
        """测试连接状态下读取数据"""
        mock_serial_instance = Mock()
        mock_serial_instance.is_open = True
        mock_serial_instance.read.return_value = b"test"
        mock_serial.return_value = mock_serial_instance
        
        # 连接
        self.connection_manager.connect("COM1", 9600)
        
        # 读取数据
        result = self.connection_manager.read(4)
        
        # 验证读取操作
        mock_serial_instance.read.assert_called_once_with(4)
        assert result == b"test"
    
    def test_read_when_not_connected(self):
        """测试未连接状态下读取数据"""
        with pytest.raises(SerialConnectionError):
            self.connection_manager.read(4)
    
    @patch('serial.Serial')
    def test_flush_operations(self, mock_serial):
        """测试清空缓冲区操作"""
        mock_serial_instance = Mock()
        mock_serial_instance.is_open = True
        mock_serial.return_value = mock_serial_instance
        
        # 连接
        self.connection_manager.connect("COM1", 9600)
        
        # 测试清空输入缓冲区
        self.connection_manager.flush_input()
        mock_serial_instance.reset_input_buffer.assert_called_once()
        
        # 测试清空输出缓冲区
        self.connection_manager.flush_output()
        mock_serial_instance.reset_output_buffer.assert_called_once()
    
    def test_is_connected(self):
        """测试连接状态检查"""
        # 初始状态
        assert self.connection_manager.is_connected() is False
        
        # 模拟连接状态
        self.connection_manager._is_connected = True
        self.connection_manager.serial_port = Mock()
        self.connection_manager.serial_port.is_open = True
        assert self.connection_manager.is_connected() is True
        
        # 模拟断开状态（但对象还存在）
        self.connection_manager.serial_port.is_open = False
        assert self.connection_manager.is_connected() is False