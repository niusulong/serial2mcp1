"""
基础工具类定义
包含所有 MCP 工具的基类和通用功能
"""
from typing import Dict, Any
from ..utils.logger import get_logger
from ..utils.exceptions import SerialConnectionError, SerialDataError, InvalidInputError
from ..driver.serial_driver import SerialDriver


class BaseTool:
    """MCP工具基类"""

    def __init__(self, driver: SerialDriver):
        self.driver = driver
        self.logger = get_logger(self.__class__.__name__.lower())

        # 延迟导入以避免循环导入
        from ..facade.parameter_converter import ParameterConverter
        from ..facade.exception_handler import ExceptionHandler
        self.converter = ParameterConverter()
        self.exception_handler = ExceptionHandler()

    def handle_exception(self, e: Exception) -> Dict[str, Any]:
        """统一异常处理"""
        return self.exception_handler.handle_exception(e)