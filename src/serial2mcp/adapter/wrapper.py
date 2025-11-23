"""
工具包装器
将串口驱动功能适配为 MCP 工具接口
"""
import threading
from typing import Dict, Any, List, Optional
from ..utils.logger import get_logger
from ..utils.exceptions import SerialConnectionError, SerialDataError, InvalidInputError
from ..driver.serial_driver import SerialDriver
from .converter import ParameterConverter
from .exception_handler import ExceptionHandler


class SerialToolWrapper:
    """
    串口工具包装器
    将底层串口驱动功能封装为MCP协议兼容的工具接口
    """

    def __init__(self):
        """初始化工具包装器"""
        self.logger = get_logger("serial_tool_wrapper")
        self.driver = SerialDriver()
        self.converter = ParameterConverter()
        self.exception_handler = ExceptionHandler()

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
        try:
            import serial.tools.list_ports

            ports = []
            for port in serial.tools.list_ports.comports():
                ports.append({
                    'port': port.device,
                    'description': port.description,
                    'hardware_id': port.hwid
                })

            self.logger.info(f"找到 {len(ports)} 个串口设备")

            return {
                'success': True,
                'data': ports
            }

        except Exception as e:
            self.logger.error(f"列出串口失败: {e}")
            return self.exception_handler.handle_exception(e)

    def configure_connection(self, **kwargs) -> Dict[str, Any]:
        """
        打开或关闭串口，配置参数

        Args:
            **kwargs: 配置参数，包括 port, baudrate, action等

        Returns:
            操作结果字典
        """
        try:
            # 解析参数
            action = kwargs.get('action')
            port = kwargs.get('port')
            baudrate = kwargs.get('baudrate')

            if not action:
                raise InvalidInputError("必须指定操作类型 (action)")

            if action == 'open':
                if not port:
                    raise InvalidInputError("打开串口时必须指定端口 (port)")

                self.driver.connect(port, baudrate)
                return {
                    'success': True,
                    'message': f'串口 {port} 连接成功',
                    'port': port,
                    'baudrate': baudrate or self.driver.config.serial.baudrate
                }

            elif action == 'close':
                self.driver.disconnect()
                return {
                    'success': True,
                    'message': '串口连接已断开'
                }

            else:
                raise InvalidInputError(f"无效的操作类型: {action}，支持的操作: open, close")

        except Exception as e:
            self.logger.error(f"配置串口连接失败: {e}")
            return self.exception_handler.handle_exception(e)

    def send_data(self, **kwargs) -> Dict[str, Any]:
        """
        核心函数：发送数据并根据策略获取响应

        Args:
            **kwargs: 发送参数，包括 payload, encoding, wait_policy, stop_pattern, timeout_ms等

        Returns:
            发送结果和响应数据的字典
        """
        try:
            # 解析参数
            payload = kwargs.get('payload', '')
            encoding = kwargs.get('encoding', 'utf8')
            wait_policy = kwargs.get('wait_policy', 'none')
            stop_pattern = kwargs.get('stop_pattern')
            timeout_ms = kwargs.get('timeout_ms', 5000)  # 默认5秒

            if not payload:
                raise InvalidInputError("必须指定要发送的数据 (payload)")

            if wait_policy not in ['keyword', 'timeout', 'none', 'at_command']:
                raise InvalidInputError(f"无效的等待策略: {wait_policy}，支持的策略: keyword, timeout, none, at_command")

            if not self.driver.is_connected():
                raise SerialConnectionError("串口未连接")

            # 编码数据
            data_bytes = self.converter.convert_to_bytes(payload, encoding)

            # 根据等待策略执行相应操作
            if wait_policy == 'none':
                # 射后不理模式
                result = self.driver.send_data(data_bytes, wait_policy='none')

            elif wait_policy == 'keyword':
                # 关键字等待模式
                if not stop_pattern:
                    raise InvalidInputError("关键字等待模式必须指定停止模式 (stop_pattern)")

                # 使用驱动内置的关键词等待功能
                result = self.driver.send_data(
                    data_bytes,
                    wait_policy='keyword',
                    stop_pattern=stop_pattern,
                    timeout=timeout_ms/1000.0
                )

            elif wait_policy == 'timeout':
                # 纯时间等待模式
                # 使用驱动内置的时间等待功能
                result = self.driver.send_data(
                    data_bytes,
                    wait_policy='timeout',
                    timeout=timeout_ms/1000.0
                )

            elif wait_policy == 'at_command':
                # AT命令模式 - 专门处理回显和响应
                result = self.driver.send_data(
                    data_bytes,
                    wait_policy='at_command',
                    timeout=timeout_ms/1000.0
                )

            if result is None:
                result = {
                    'data': '',
                    'raw_data': b'',
                    'is_hex': False,
                    'bytes_received': 0
                }

            # 添加待处理URC计数
            result['pending_urc_count'] = self.driver.get_pending_urc_count()

            # 标记操作成功
            result['success'] = True

            self.logger.info(f"数据发送成功，等待策略: {wait_policy}")

            return result

        except Exception as e:
            self.logger.error(f"发送数据失败: {e}")
            return self.exception_handler.handle_exception(e)

    def read_urc(self) -> Dict[str, Any]:
        """
        读取后台缓冲区中积累的未处理消息（URC）

        Returns:
            URC消息列表的字典
        """
        try:
            urc_messages = self.driver.get_urc_messages(clear=True)

            result = {
                'success': True,
                'data': urc_messages,
                'count': len(urc_messages)
            }

            self.logger.info(f"读取到 {len(urc_messages)} 条URC消息")

            return result

        except Exception as e:
            self.logger.error(f"读取URC失败: {e}")
            return self.exception_handler.handle_exception(e)

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
            self.logger.error(f"获取驱动状态失败: {e}")
            return self.exception_handler.handle_exception(e)

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
            self.logger.error(f"获取性能指标失败: {e}")
            return self.exception_handler.handle_exception(e)