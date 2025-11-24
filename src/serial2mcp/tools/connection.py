"""
连接管理工具
负责串口设备的连接和断开操作
"""
from typing import Dict, Any
from .base import BaseTool
from ..utils.exceptions import InvalidInputError


class ConnectionTool(BaseTool):
    """串口连接管理工具"""

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
            return self.handle_exception(e)

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
            return self.handle_exception(e)