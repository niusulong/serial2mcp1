"""
异常处理器
负责捕获和处理驱动层异常并转换为 MCP 格式
"""
import traceback
from typing import Dict, Any
from ..utils.logger import get_logger
from ..utils.exceptions import (
    SerialAgentError,
    SerialConnectionError,
    SerialConfigurationError,
    SerialDataError,
    MCPProtocolError,
    DataParsingError,
    TimeoutError as SerialTimeoutError,
    InvalidInputError,
    URCHandlerError,
    DriverNotInitializedError
)


class ExceptionHandler:
    """异常处理器，负责捕获和处理驱动层异常并转换为MCP格式"""

    def __init__(self):
        """初始化异常处理器"""
        self.logger = get_logger("exception_handler")

    def handle_exception(self, exception: Exception) -> Dict[str, Any]:
        """
        处理异常并返回标准格式的错误响应

        Args:
            exception: 捕获的异常对象

        Returns:
            标准格式的错误响应字典
        """
        # 记录异常信息
        self.logger.error(
            f"异常处理: {type(exception).__name__}: {str(exception)}",
            exc_info=True  # 记录完整的堆栈跟踪
        )

        # 根据异常类型返回不同的错误响应
        if isinstance(exception, SerialConnectionError):
            return self._create_error_response(
                "串口连接错误",
                str(exception),
                error_code="SERIAL_CONNECTION_ERROR"
            )

        elif isinstance(exception, SerialConfigurationError):
            return self._create_error_response(
                "串口配置错误",
                str(exception),
                error_code="SERIAL_CONFIGURATION_ERROR"
            )

        elif isinstance(exception, SerialDataError):
            return self._create_error_response(
                "串口数据错误",
                str(exception),
                error_code="SERIAL_DATA_ERROR"
            )

        elif isinstance(exception, MCPProtocolError):
            return self._create_error_response(
                "MCP协议错误",
                str(exception),
                error_code="MCP_PROTOCOL_ERROR"
            )

        elif isinstance(exception, DataParsingError):
            return self._create_error_response(
                "数据解析错误",
                str(exception),
                error_code="DATA_PARSING_ERROR"
            )

        elif isinstance(exception, SerialTimeoutError):
            return self._create_error_response(
                "操作超时",
                str(exception),
                error_code="TIMEOUT_ERROR"
            )

        elif isinstance(exception, InvalidInputError):
            return self._create_error_response(
                "无效输入",
                str(exception),
                error_code="INVALID_INPUT_ERROR"
            )

        elif isinstance(exception, URCHandlerError):
            return self._create_error_response(
                "URC处理错误",
                str(exception),
                error_code="URC_HANDLER_ERROR"
            )

        elif isinstance(exception, DriverNotInitializedError):
            return self._create_error_response(
                "驱动未初始化",
                str(exception),
                error_code="DRIVER_NOT_INITIALIZED"
            )

        elif isinstance(exception, NotImplementedError):
            return self._create_error_response(
                "功能未实现",
                f"该功能尚未实现: {str(exception)}",
                error_code="NOT_IMPLEMENTED_ERROR"
            )

        elif isinstance(exception, AttributeError):
            return self._create_error_response(
                "属性错误",
                f"访问不存在的属性: {str(exception)}",
                error_code="ATTRIBUTE_ERROR"
            )

        elif isinstance(exception, ValueError):
            return self._create_error_response(
                "值错误",
                f"无效的值: {str(exception)}",
                error_code="VALUE_ERROR"
            )

        elif isinstance(exception, TypeError):
            return self._create_error_response(
                "类型错误",
                f"类型不匹配: {str(exception)}",
                error_code="TYPE_ERROR"
            )

        elif isinstance(exception, OSError):
            # 处理系统级错误，如串口被占用等
            return self._create_error_response(
                "系统错误",
                f"系统级错误: {str(exception)}",
                error_code="SYSTEM_ERROR"
            )

        elif isinstance(exception, Exception):
            # 对于其他未分类的异常，返回通用错误
            return self._create_error_response(
                "未知错误",
                f"发生未知错误: {str(exception)}",
                error_code="UNKNOWN_ERROR"
            )

        else:
            # 万能兜底处理
            return self._create_error_response(
                "未知异常",
                f"发生未知异常: {str(exception)}",
                error_code="UNKNOWN_EXCEPTION"
            )

    def _create_error_response(self, error_type: str, error_message: str,
                              error_code: str = "UNKNOWN_ERROR") -> Dict[str, Any]:
        """
        创建标准格式的错误响应

        Args:
            error_type: 错误类型描述
            error_message: 错误消息
            error_code: 错误代码

        Returns:
            标准格式的错误响应字典
        """
        return {
            'success': False,
            'error_type': error_type,
            'error_message': error_message,
            'error_code': error_code,
            'timestamp': __import__('time').time()
        }

    def safe_execute(self, func, *args, **kwargs) -> Dict[str, Any]:
        """
        安全执行函数，捕获异常并返回标准格式响应

        Args:
            func: 要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果或错误响应字典
        """
        try:
            result = func(*args, **kwargs)

            # 如果函数执行成功，检查返回值是否已经是标准格式
            if isinstance(result, dict) and 'success' in result:
                return result
            else:
                # 如果返回值不是标准格式，将其包装为成功响应
                return {
                    'success': True,
                    'data': result,
                    'timestamp': __import__('time').time()
                }

        except Exception as e:
            # 捕获异常并返回标准错误格式
            return self.handle_exception(e)

    def register_error_handler(self, exception_class, handler_func):
        """
        注册特定异常类型的处理函数

        Args:
            exception_class: 异常类
            handler_func: 处理函数
        """
        # 此方法可在未来扩展，为特定异常类型提供自定义处理逻辑
        pass

    def get_error_info(self, exception: Exception) -> Dict[str, Any]:
        """
        获取异常的详细信息

        Args:
            exception: 异常对象

        Returns:
            异常详细信息字典
        """
        return {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc(),
            'module': getattr(exception, '__module__', 'unknown'),
            'timestamp': __import__('time').time()
        }