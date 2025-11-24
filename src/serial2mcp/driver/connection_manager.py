"""
连接管理器
负责串口连接的建立、维护和断开
"""
import serial
import time
from typing import Optional
from ..utils.logger import get_logger
from ..utils.exceptions import SerialConnectionError, SerialConfigurationError
from ..utils.config import config_manager
from ..utils.serial_data_logger import serial_data_logger_manager


class ConnectionManager:
    """串口连接管理器，负责串口连接的建立、维护和断开"""

    def __init__(self):
        """初始化连接管理器"""
        self.logger = get_logger("connection_manager")
        self.config = config_manager.get_config()
        self.serial_port: Optional[serial.Serial] = None
        self._is_connected = False
        self.current_port = None  # 当前连接的端口名称

    def initialize(self) -> None:
        """初始化连接管理器"""
        self.logger.info("连接管理器初始化完成")

    def connect(self, port: str, baudrate: int = None) -> None:
        """
        连接串口

        Args:
            port: 串口设备路径
            baudrate: 波特率，默认使用配置中的值
        """
        if self._is_connected and self.serial_port and self.serial_port.is_open:
            self.logger.warning(f"串口 {self.serial_port.port} 已连接，先断开现有连接")
            self.disconnect()

        try:
            # 如果没有指定波特率，使用配置中的默认值
            if baudrate is None:
                baudrate = self.config.serial.baudrate

            # 使用配置中的其他参数
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=self.config.serial.bytesize,
                parity=self.config.serial.parity,
                stopbits=self.config.serial.stopbits,
                timeout=self.config.serial.timeout,
                xonxoff=self.config.serial.xonxoff,
                rtscts=self.config.serial.rtscts,
                dsrdtr=self.config.serial.dsrdtr
            )

            self._is_connected = True
            self.current_port = port  # 记录当前连接的端口
            self.logger.info(f"串口连接成功: {port}@{baudrate}")

        except serial.SerialException as e:
            self.logger.error(f"串口连接失败: {e}")
            raise SerialConnectionError(f"串口连接失败: {e}")
        except Exception as e:
            self.logger.error(f"连接时发生未知错误: {e}")
            raise SerialConnectionError(f"连接时发生未知错误: {e}")

    def disconnect(self) -> None:
        """断开串口连接"""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
                self._is_connected = False
                self.current_port = None  # 清除当前端口
                self.logger.info(f"串口 {self.serial_port.port} 已断开")
            except Exception as e:
                self.logger.error(f"断开串口连接时发生错误: {e}")
                # 即使出错也设置为未连接状态
                self._is_connected = False
                self.current_port = None
            finally:
                self.serial_port = None
        else:
            self.logger.warning("尝试断开未连接的串口")

    def write(self, data: bytes) -> int:
        """
        向串口写入数据

        Args:
            data: 要写入的字节数据

        Returns:
            实际写入的字节数
        """
        if not self._is_connected or not self.serial_port or not self.serial_port.is_open:
            raise SerialConnectionError("串口未连接")

        try:
            bytes_written = self.serial_port.write(data)
            self.serial_port.flush()  # 确保数据被发送

            # 记录发送的数据到通信日志
            if self.current_port and self.config.logging.com_log_enabled:
                serial_data_logger_manager.log_data(self.current_port, 'TX', data)

            self.logger.debug(f"写入 {bytes_written} 字节数据: {data.hex()}")
            return bytes_written
        except serial.SerialException as e:
            self.logger.error(f"写入串口数据失败: {e}")
            raise SerialConnectionError(f"写入串口数据失败: {e}")
        except Exception as e:
            self.logger.error(f"写入数据时发生未知错误: {e}")
            raise SerialConnectionError(f"写入数据时发生未知错误: {e}")

    def read(self, size: int = 1) -> bytes:
        """
        从串口读取数据

        Args:
            size: 要读取的字节数

        Returns:
            读取到的字节数据
        """
        if not self._is_connected or not self.serial_port or not self.serial_port.is_open:
            raise SerialConnectionError("串口未连接")

        try:
            data = self.serial_port.read(size)
            if data:
                self.logger.debug(f"读取 {len(data)} 字节数据: {data.hex()}")
            return data
        except serial.SerialException as e:
            self.logger.error(f"读取串口数据失败: {e}")
            raise SerialConnectionError(f"读取串口数据失败: {e}")
        except Exception as e:
            self.logger.error(f"读取数据时发生未知错误: {e}")
            raise SerialConnectionError(f"读取数据时发生未知错误: {e}")

    def read_until(self, expected: bytes = b'\n', size: Optional[int] = None) -> bytes:
        """
        从串口读取数据直到遇到预期字节

        Args:
            expected: 期望遇到的字节序列
            size: 最大读取字节数

        Returns:
            读取到的字节数据
        """
        if not self._is_connected or not self.serial_port or not self.serial_port.is_open:
            raise SerialConnectionError("串口未连接")

        try:
            data = self.serial_port.read_until(expected, size)
            if data:
                self.logger.debug(f"读取直到 {expected}，获得 {len(data)} 字节数据: {data.hex()}")
            return data
        except serial.SerialException as e:
            self.logger.error(f"读取串口数据失败: {e}")
            raise SerialConnectionError(f"读取串口数据失败: {e}")
        except Exception as e:
            self.logger.error(f"读取数据时发生未知错误: {e}")
            raise SerialConnectionError(f"读取数据时发生未知错误: {e}")

    def flush_input(self) -> None:
        """清空输入缓冲区"""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.reset_input_buffer()
                self.logger.debug("输入缓冲区已清空")
            except Exception as e:
                self.logger.error(f"清空输入缓冲区失败: {e}")
                raise SerialConnectionError(f"清空输入缓冲区失败: {e}")

    def flush_output(self) -> None:
        """清空输出缓冲区"""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.reset_output_buffer()
                self.logger.debug("输出缓冲区已清空")
            except Exception as e:
                self.logger.error(f"清空输出缓冲区失败: {e}")
                raise SerialConnectionError(f"清空输出缓冲区失败: {e}")

    def is_connected(self) -> bool:
        """
        检查串口是否连接

        Returns:
            串口连接状态
        """
        return (self._is_connected and
                self.serial_port is not None and
                self.serial_port.is_open)

    def get_connection_info(self) -> dict:
        """
        获取连接信息

        Returns:
            连接信息字典
        """
        if self.is_connected():
            return {
                'port': self.serial_port.port,
                'baudrate': self.serial_port.baudrate,
                'bytesize': self.serial_port.bytesize,
                'parity': self.serial_port.parity,
                'stopbits': self.serial_port.stopbits,
                'timeout': self.serial_port.timeout,
                'xonxoff': self.serial_port.xonxoff,
                'rtscts': self.serial_port.rtscts,
                'dsrdtr': self.serial_port.dsrdtr,
                'is_connected': True
            }
        else:
            return {
                'is_connected': False
            }

    def change_baudrate(self, new_baudrate: int) -> None:
        """
        更改波特率

        Args:
            new_baudrate: 新的波特率
        """
        if not self.is_connected():
            raise SerialConnectionError("串口未连接，无法更改波特率")

        try:
            self.serial_port.baudrate = new_baudrate
            self.logger.info(f"波特率已更改为: {new_baudrate}")
        except Exception as e:
            self.logger.error(f"更改波特率失败: {e}")
            raise SerialConnectionError(f"更改波特率失败: {e}")