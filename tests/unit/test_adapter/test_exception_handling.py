"""
异常处理单元测试
测试系统中各种异常情况的处理
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from serial2mcp.utils.exceptions import (
    SerialAgentError,
    SerialConnectionError,
    SerialConfigurationError,
    SerialDataError,
    MCPProtocolError,
    DataParsingError,
    TimeoutError as SerialTimeoutError,
    InvalidInputError,
    AsyncMessageHandlerError,
    DriverNotInitializedError
)
from serial2mcp.adapter.exception_handler import ExceptionHandler
from serial2mcp.driver.serial_driver import SerialDriver
from serial2mcp.adapter.wrapper import SerialToolWrapper


class TestExceptionHandler:
    """异常处理器测试类"""
    
    def setup_method(self):
        """测试方法执行前的设置"""
        self.handler = ExceptionHandler()
    
    def test_handle_serial_connection_error(self):
        """测试处理串口连接错误"""
        error = SerialConnectionError("连接失败")
        result = self.handler.handle_exception(error)
        
        assert result['success'] is False
        assert result['error_type'] == '串口连接错误'
        assert result['error_code'] == 'SERIAL_CONNECTION_ERROR'
        assert '连接失败' in result['error_message']
    
    def test_handle_serial_data_error(self):
        """测试处理串口数据错误"""
        error = SerialDataError("数据发送失败")
        result = self.handler.handle_exception(error)
        
        assert result['success'] is False
        assert result['error_type'] == '串口数据错误'
        assert result['error_code'] == 'SERIAL_DATA_ERROR'
        assert '数据发送失败' in result['error_message']
    
    def test_handle_timeout_error(self):
        """测试处理超时错误"""
        error = SerialTimeoutError("操作超时")
        result = self.handler.handle_exception(error)
        
        assert result['success'] is False
        assert result['error_type'] == '操作超时'
        assert result['error_code'] == 'TIMEOUT_ERROR'
        assert '操作超时' in result['error_message']
    
    def test_handle_invalid_input_error(self):
        """测试处理无效输入错误"""
        error = InvalidInputError("参数无效")
        result = self.handler.handle_exception(error)
        
        assert result['success'] is False
        assert result['error_type'] == '无效输入'
        assert result['error_code'] == 'INVALID_INPUT_ERROR'
        assert '参数无效' in result['error_message']
    
    def test_handle_standard_exceptions(self):
        """测试处理标准异常"""
        # 测试ValueError
        error = ValueError("值错误")
        result = self.handler.handle_exception(error)
        assert result['error_code'] == 'VALUE_ERROR'
        
        # 测试TypeError
        error = TypeError("类型错误")
        result = self.handler.handle_exception(error)
        assert result['error_code'] == 'TYPE_ERROR'
        
        # 测试AttributeError
        error = AttributeError("属性错误")
        result = self.handler.handle_exception(error)
        assert result['error_code'] == 'ATTRIBUTE_ERROR'
    
    def test_handle_unknown_exception(self):
        """测试处理未知异常"""
        error = RuntimeError("未知运行时错误")
        result = self.handler.handle_exception(error)
        
        assert result['success'] is False
        assert result['error_type'] == '未知错误'
        assert '未知运行时错误' in result['error_message']
    
    def test_safe_execute_success(self):
        """测试安全执行函数-成功情况"""
        def success_func():
            return "success_result"
        
        result = self.handler.safe_execute(success_func)
        
        assert result['success'] is True
        assert result['data'] == 'success_result'
    
    def test_safe_execute_with_standard_response(self):
        """测试安全执行函数-已标准格式响应"""
        def standard_func():
            return {'success': True, 'data': 'already_standard'}
        
        result = self.handler.safe_execute(standard_func)
        
        assert result['success'] is True
        assert result['data'] == 'already_standard'
    
    def test_safe_execute_with_exception(self):
        """测试安全执行函数-异常情况"""
        def error_func():
            raise SerialConnectionError("连接失败")
        
        result = self.handler.safe_execute(error_func)
        
        assert result['success'] is False
        assert result['error_type'] == '串口连接错误'
        assert '连接失败' in result['error_message']


class TestDriverExceptions:
    """驱动层异常测试"""
    
    def test_driver_not_initialized_error(self):
        """测试驱动未初始化异常"""
        # 创建驱动但不初始化
        with patch('serial2mcp.driver.connection_manager.ConnectionManager'):
            with patch('serial2mcp.driver.reader.BackgroundReader'):
                with patch('serial2mcp.driver.processor.DataProcessor'):
                    driver = SerialDriver()
                    # 不调用initialize()

        with pytest.raises(DriverNotInitializedError):
            driver.connect("COM1", 9600)

    def test_serial_connection_error_in_driver(self):
        """测试驱动中的串口连接错误"""
        with patch('serial2mcp.driver.connection_manager.ConnectionManager') as mock_conn_manager, \
             patch('serial2mcp.driver.reader.BackgroundReader'), \
             patch('serial2mcp.driver.processor.DataProcessor'):
            driver = SerialDriver()
            driver.initialize()

            # 设置模拟对象
            driver.connection_manager = mock_conn_manager

        # 模拟连接失败
        driver.connection_manager.connect.side_effect = SerialConnectionError("连接异常")

        with pytest.raises(SerialConnectionError):
            driver.connect("COM1", 9600)

    @patch('serial2mcp.driver.connection_manager.ConnectionManager')
    @patch('serial2mcp.driver.reader.BackgroundReader')
    @patch('serial2mcp.driver.processor.DataProcessor')
    def test_send_data_not_connected_error(self, mock_processor, mock_reader, mock_conn_manager):
        """测试未连接时发送数据的错误"""
        driver = SerialDriver()
        driver.initialize()

        # 设置未连接状态
        driver._is_connected = False
        
        with pytest.raises(SerialConnectionError):
            driver.send_data(b"test data")


class TestAdapterExceptions:
    """适配层异常测试"""
    
    @patch('serial2mcp.driver.serial_driver.SerialDriver')
    @patch('serial2mcp.adapter.converter.ParameterConverter')
    @patch('serial2mcp.adapter.exception_handler.ExceptionHandler')
    def test_wrapper_list_ports_exception(self, mock_handler, mock_converter, mock_driver):
        """测试包装器中列出端口时的异常处理"""
        wrapper = SerialToolWrapper()
        
        # 模拟serial.tools.list_ports抛出异常
        with patch('serial.tools.list_ports.comports', side_effect=OSError("串口访问错误")):
            mock_handler.handle_exception.return_value = {
                'success': False,
                'error_message': '串口访问错误',
                'error_code': 'SYSTEM_ERROR'
            }
            
            result = wrapper.list_ports()
            
            # 验证异常处理器被调用
            mock_handler.handle_exception.assert_called_once()
            assert result['success'] is False
    
    @patch('serial2mcp.driver.serial_driver.SerialDriver')
    @patch('serial2mcp.adapter.converter.ParameterConverter')
    @patch('serial2mcp.adapter.exception_handler.ExceptionHandler')
    def test_wrapper_configure_connection_missing_action(self, mock_handler, mock_converter, mock_driver):
        """测试配置连接时缺少必需参数"""
        wrapper = SerialToolWrapper()

        # 不提供action参数
        result = wrapper.configure_connection(port="COM1")

        # 期望返回InvalidInputError
        mock_handler.handle_exception.assert_called_once()
        args = mock_handler.handle_exception.call_args[0]
        assert isinstance(args[0], InvalidInputError)
        assert "必须指定操作类型" in str(args[0])

    @patch('serial2mcp.driver.serial_driver.SerialDriver')
    @patch('serial2mcp.adapter.converter.ParameterConverter')
    @patch('serial2mcp.adapter.exception_handler.ExceptionHandler')
    def test_wrapper_configure_connection_invalid_action(self, mock_handler, mock_converter, mock_driver):
        """测试配置连接时无效操作类型"""
        wrapper = SerialToolWrapper()

        result = wrapper.configure_connection(action="invalid_action", port="COM1")

        # 期望返回InvalidInputError
        mock_handler.handle_exception.assert_called_once()
        args = mock_handler.handle_exception.call_args[0]
        assert isinstance(args[0], InvalidInputError)
        assert "无效的操作类型" in str(args[0])

    @patch('serial2mcp.driver.serial_driver.SerialDriver')
    @patch('serial2mcp.adapter.converter.ParameterConverter')
    @patch('serial2mcp.adapter.exception_handler.ExceptionHandler')
    def test_wrapper_send_data_missing_payload(self, mock_handler, mock_converter, mock_driver):
        """测试发送数据时缺少必要参数"""
        wrapper = SerialToolWrapper()

        result = wrapper.send_data(wait_policy="keyword", stop_pattern="OK")

        # 期望返回InvalidInputError
        mock_handler.handle_exception.assert_called_once()
        args = mock_handler.handle_exception.call_args[0]
        assert isinstance(args[0], InvalidInputError)
        assert "必须指定要发送的数据" in str(args[0])

    @patch('serial2mcp.driver.serial_driver.SerialDriver')
    @patch('serial2mcp.adapter.converter.ParameterConverter')
    @patch('serial2mcp.adapter.exception_handler.ExceptionHandler')
    def test_wrapper_send_data_invalid_wait_policy(self, mock_handler, mock_converter, mock_driver):
        """测试发送数据时无效等待策略"""
        wrapper = SerialToolWrapper()

        result = wrapper.send_data(payload="test", wait_policy="invalid")
        
        # 期望返回InvalidInputError
        mock_handler.handle_exception.assert_called_once()
        args = mock_handler.handle_exception.call_args[0]
        assert isinstance(args[0], InvalidInputError)
        assert "无效的等待策略" in str(args[0])
    
    @patch('serial2mcp.driver.serial_driver.SerialDriver')
    @patch('serial2mcp.adapter.converter.ParameterConverter')
    @patch('serial2mcp.adapter.exception_handler.ExceptionHandler')
    def test_wrapper_send_data_keyword_missing_stop_pattern(self, mock_handler, mock_converter, mock_driver):
        """测试关键字等待模式缺少停止模式"""
        wrapper = SerialToolWrapper()

        result = wrapper.send_data(payload="test", wait_policy="keyword")

        # 期望返回InvalidInputError
        mock_handler.handle_exception.assert_called_once()
        args = mock_handler.handle_exception.call_args[0]
        assert isinstance(args[0], InvalidInputError)
        assert "关键字等待模式必须指定停止模式" in str(args[0])


class TestConverterExceptions:
    """参数转换器异常测试"""

    def setup_method(self):
        """测试方法执行前的设置"""
        from serial2mcp.adapter.converter import ParameterConverter
        self.converter = ParameterConverter()
    
    def test_convert_to_bytes_invalid_encoding(self):
        """测试转换为字节时无效编码"""
        with pytest.raises(InvalidInputError):
            self.converter.convert_to_bytes("test", "invalid_encoding")
    
    def test_convert_to_bytes_invalid_hex(self):
        """测试转换为字节时无效十六进制字符串"""
        with pytest.raises(InvalidInputError):
            self.converter.convert_to_bytes("invalid_hex_string!", "hex")
    
    def test_convert_from_bytes_invalid_encoding(self):
        """测试从字节转换时无效编码"""
        with pytest.raises(InvalidInputError):
            self.converter.convert_from_bytes(b"test", "invalid_encoding")
    
    def test_parse_baudrate_invalid_string(self):
        """测试解析波特率时无效字符串"""
        with pytest.raises(InvalidInputError):
            self.converter.parse_baudrate("not_a_number")
    
    def test_parse_baudrate_out_of_range(self):
        """测试解析波特率时超出范围"""
        with pytest.raises(InvalidInputError):
            self.converter.parse_baudrate(2000000)  # 超出合理范围
    
    def test_parse_timeout_invalid_value(self):
        """测试解析超时时无效值"""
        with pytest.raises(InvalidInputError):
            self.converter.parse_timeout("not_a_number")
    
    def test_convert_wait_policy_invalid(self):
        """测试转换等待策略时无效值"""
        with pytest.raises(InvalidInputError):
            self.converter.convert_wait_policy("invalid_policy")
    
    def test_convert_encoding_invalid(self):
        """测试转换编码时无效值"""
        with pytest.raises(InvalidInputError):
            self.converter.convert_encoding("invalid_encoding")
    
    def test_validate_parameters_invalid_port(self):
        """测试验证参数时无效端口"""
        with pytest.raises(InvalidInputError):
            self.converter.validate_parameters(port="invalid_port_name")
    
    def test_validate_parameters_invalid_action(self):
        """测试验证参数时无效操作"""
        with pytest.raises(InvalidInputError):
            self.converter.validate_parameters(action="invalid_action")