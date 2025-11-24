"""
工具包装器
将串口驱动功能适配为 MCP 工具接口
"""
from typing import Dict, Any
from ..utils.logger import get_logger
from ..driver.serial_driver import SerialDriver
from ..tools.connection import ConnectionTool
from ..tools.communication import CommunicationTool
from ..tools.urc import URCTool


class SerialToolWrapper:
    """
    串口工具包装器
    将底层串口驱动功能封装为MCP协议兼容的工具接口
    """

    def __init__(self):
        """初始化工具包装器"""
        self.logger = get_logger("serial_tool_wrapper")
        self.driver = SerialDriver()

        # 初始化各个工具模块
        self.connection_tool = ConnectionTool(self.driver)
        self.communication_tool = CommunicationTool(self.driver)
        self.urc_tool = URCTool(self.driver)

        # 初始化驱动
        try:
            self.driver.initialize()
            self.logger.info("串口工具包装器初始化完成")
        except Exception as e:
            self.logger.error(f"串口工具包装器初始化失败: {e}")
            raise

    def list_ports(self) -> Dict[str, Any]:
        """
        列出当前系统所有可用的串口设备

        Returns:
            包含串口列表的字典
        """
        return self.connection_tool.list_ports()

    def configure_connection(self, **kwargs) -> Dict[str, Any]:
        """
        打开或关闭串口，配置参数

        Args:
            **kwargs: 配置参数，包括 port, baudrate, action等

        Returns:
            操作结果字典
        """
        return self.connection_tool.configure_connection(**kwargs)

    def send_data(self, **kwargs) -> Dict[str, Any]:
        """
        核心函数：发送数据并根据策略获取响应

        Args:
            **kwargs: 发送参数，包括 payload, encoding, wait_policy, stop_pattern, timeout_ms等

        Returns:
            发送结果和响应数据的字典
        """
        return self.communication_tool.send_data(**kwargs)

    def read_urc(self) -> Dict[str, Any]:
        """
        读取后台缓冲区中积累的未处理消息（URC）

        Returns:
            URC消息列表的字典
        """
        return self.urc_tool.read_urc()

    def get_driver_status(self) -> Dict[str, Any]:
        """
        获取驱动状态

        Returns:
            驱动状态信息字典
        """
        try:
            status = self.driver.get_driver_status()
            return {
                'success': True,
                'data': status
            }
        except Exception as e:
            return self.connection_tool.handle_exception(e)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标

        Returns:
            性能指标字典
        """
        try:
            metrics = self.driver.get_performance_metrics()
            return {
                'success': True,
                'data': metrics
            }
        except Exception as e:
            return self.connection_tool.handle_exception(e)