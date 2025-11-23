"""
串口驱动主类
实现串口连接、数据收发等核心功能
"""
import threading
import queue
import time
from typing import Optional, Dict, Any, List, Tuple
import serial
from ..utils.logger import get_logger
from ..utils.exceptions import (
    SerialConnectionError,
    SerialDataError,
    TimeoutError as SerialTimeoutError,
    DriverNotInitializedError
)
from ..utils.config import config_manager
from ..utils.metrics import metrics_collector
from .connection_manager import ConnectionManager
from .reader import BackgroundReader
from .processor import DataProcessor


class SerialDriver:
    """串口驱动主类，实现串口连接、数据收发等核心功能"""

    def __init__(self):
        """初始化串口驱动"""
        self.logger = get_logger("serial_driver")
        self.config = config_manager.get_config()
        self.connection_manager = ConnectionManager()
        self.background_reader = BackgroundReader()
        self.data_processor = DataProcessor()

        # 同步模式标志 - 用于区分同步响应和异步URC
        self._sync_mode = threading.Event()
        self._sync_response_queue = queue.Queue()
        self._urc_queue = queue.Queue(maxsize=self.config.driver.urc_buffer_size)

        # 驱动状态
        self._is_initialized = False
        self._is_connected = False

        # 同步操作相关
        self._current_operation_timeout = self.config.driver.sync_timeout_default

    def initialize(self) -> None:
        """初始化驱动"""
        try:
            self.connection_manager.initialize()
            self.background_reader.initialize(
                connection_manager=self.connection_manager,
                sync_mode_event=self._sync_mode,
                sync_response_queue=self._sync_response_queue,
                urc_queue=self._urc_queue
            )
            self.data_processor.initialize()

            self._is_initialized = True
            self.logger.info("串口驱动初始化完成")
        except Exception as e:
            self.logger.error(f"串口驱动初始化失败: {e}")
            raise SerialConnectionError(f"串口驱动初始化失败: {e}")

    def connect(self, port: str, baudrate: int = None) -> None:
        """
        连接串口

        Args:
            port: 串口设备路径
            baudrate: 波特率，默认使用配置中的值
        """
        if not self._is_initialized:
            raise DriverNotInitializedError("驱动未初始化")

        try:
            # 如果没有指定波特率，使用配置中的默认值
            if baudrate is None:
                baudrate = self.config.serial.baudrate

            self.connection_manager.connect(port, baudrate)
            self.background_reader.start()

            self._is_connected = True
            metrics_collector.record_connection_attempt(success=True)
            self.logger.info(f"串口连接成功: {port}@{baudrate}")
        except Exception as e:
            metrics_collector.record_connection_attempt(success=False)
            self.logger.error(f"串口连接失败: {e}")
            raise SerialConnectionError(f"串口连接失败: {e}")

    def disconnect(self) -> None:
        """断开串口连接"""
        try:
            # 停止后台读取线程
            self.background_reader.stop()

            # 断开连接
            self.connection_manager.disconnect()

            self._is_connected = False
            self.logger.info("串口连接已断开")
        except Exception as e:
            self.logger.error(f"串口断开连接失败: {e}")
            raise SerialConnectionError(f"串口断开连接失败: {e}")

    def is_connected(self) -> bool:
        """
        检查串口是否连接

        Returns:
            串口连接状态
        """
        return self._is_connected and self.connection_manager.is_connected()

    def send_data(self, data: bytes, wait_policy: str = 'none', stop_pattern: str = None,
                  timeout: float = 5.0, is_hex: bool = False) -> Dict[str, Any]:
        """
        发送数据并根据策略获取响应

        Args:
            data: 要发送的字节数据
            wait_policy: 等待策略 ('none', 'keyword', 'timeout', 'at_command')
            stop_pattern: 仅在 'keyword' 模式下有效，停止模式
            timeout: 等待超时时间（秒）
            is_hex: 是否为十六进制数据

        Returns:
            包含响应数据的字典
        """
        if not self.is_connected():
            raise SerialConnectionError("串口未连接")

        try:
            # 记录发送数据到性能指标
            metrics_collector.record_send(len(data))

            self.connection_manager.write(data)
            self.logger.debug(f"发送数据: {data.hex() if is_hex else data.decode('utf-8', errors='replace')}")

            # 根据策略获取响应
            if wait_policy == 'none':
                # 射后不理模式：直接发送数据
                self.connection_manager.write(data)
                return {
                    'success': True,
                    'message': '数据已发送，不等待响应',
                    'pending_urc_count': self.get_pending_urc_count()
                }
            elif wait_policy in ['keyword', 'timeout', 'at_command']:
                # 清空同步响应队列以避免之前的残留数据
                while not self._sync_response_queue.empty():
                    try:
                        self._sync_response_queue.get_nowait()
                    except queue.Empty:
                        break

                # 进入同步模式以捕获响应数据
                self._sync_mode.set()

                # 在发送前短暂延迟，确保模式切换生效
                time.sleep(0.001)

                # 发送数据前清空输入缓冲区，防止残留数据干扰
                self.connection_manager.flush_input()

                # 发送数据
                self.connection_manager.write(data)

                # 立即开始接收响应（在同步模式下）
                if wait_policy == 'keyword':
                    # 关键字模式：等待直到找到指定的停止模式
                    result = self._receive_until_keyword(stop_pattern, timeout)
                elif wait_policy == 'timeout':
                    result = self._receive_until_timeout(timeout)
                elif wait_policy == 'at_command':
                    # 专门针对AT指令的处理模式：等待回显+响应
                    original_cmd = data.decode('utf-8', errors='replace')
                    result = self._receive_at_response(original_cmd, timeout)

                # 退出同步模式
                self._sync_mode.clear()

                return result
            else:
                raise InvalidInputError(f"不支持的等待策略: {wait_policy}")

        except Exception as e:
            metrics_collector.record_error()
            self.logger.error(f"数据发送失败: {e}")
            raise SerialDataError(f"数据发送失败: {e}")

    def _receive_until_keyword(self, stop_pattern: str, timeout: float) -> Dict[str, Any]:
        """接收数据直到找到指定关键词"""
        if not stop_pattern:
            raise InvalidInputError("停止模式不能为空")

        start_time = time.time()
        received_data = b""
        stop_pattern_bytes = stop_pattern.encode('utf-8')

        while time.time() - start_time < timeout:
            try:
                # 尝试从同步响应队列获取数据
                chunk = self._sync_response_queue.get(timeout=0.1)
                if chunk:
                    received_data += chunk
                    self.logger.debug(f"接收到数据块: {chunk!r}, 累计: {received_data!r}")

                    # 检查是否包含停止模式
                    if stop_pattern_bytes in received_data:
                        self.logger.debug(f"找到停止模式 '{stop_pattern}' 在数据中")
                        break
            except queue.Empty:
                # 继续等待
                continue

        # 如果超时仍未收到停止模式，则视为超时
        if stop_pattern_bytes not in received_data:
            self.logger.warning(f"接收超时，未找到停止模式: {stop_pattern}")
            raise SerialTimeoutError(f"接收超时，未找到停止模式: {stop_pattern}")

        # 记录接收数据到性能指标
        if received_data:
            metrics_collector.record_receive(len(received_data))

        if received_data:
            # 尝试解码为字符串
            try:
                decoded_data = received_data.decode('utf-8')
                is_hex = False
            except UnicodeDecodeError:
                decoded_data = received_data.hex()
                is_hex = True

            return {
                'data': decoded_data,
                'raw_data': received_data,
                'is_hex': is_hex,
                'found_stop_pattern': stop_pattern_bytes in received_data,
                'bytes_received': len(received_data),
                'pending_urc_count': self.get_pending_urc_count(),
                'success': True
            }
        else:
            return {
                'data': '',
                'raw_data': b'',
                'is_hex': False,
                'found_stop_pattern': False,
                'bytes_received': 0,
                'pending_urc_count': self.get_pending_urc_count(),
                'success': True
            }

    def _receive_until_timeout(self, timeout: float) -> Dict[str, Any]:
        """在指定时间内接收所有数据"""
        start_time = time.time()
        received_data = b""

        while time.time() - start_time < timeout:
            try:
                # 尝试从同步响应队列获取数据
                chunk = self._sync_response_queue.get(timeout=0.1)
                if chunk:
                    received_data += chunk
            except queue.Empty:
                # 继续等待直到时间结束
                continue

        # 记录接收数据到性能指标
        if received_data:
            metrics_collector.record_receive(len(received_data))

        if received_data:
            # 尝试解码为字符串
            try:
                decoded_data = received_data.decode('utf-8')
                is_hex = False
            except UnicodeDecodeError:
                decoded_data = received_data.hex()
                is_hex = True

            return {
                'data': decoded_data,
                'raw_data': received_data,
                'is_hex': is_hex,
                'bytes_received': len(received_data),
                'pending_urc_count': self.get_pending_urc_count(),
                'success': True
            }
        else:
            return {
                'data': '',
                'raw_data': b'',
                'is_hex': False,
                'bytes_received': 0,
                'pending_urc_count': self.get_pending_urc_count(),
                'success': True
            }

    def _receive_for_timeout(self, duration: float) -> Dict[str, Any]:
        """在指定时间内接收数据"""
        start_time = time.time()
        received_data = b""

        while time.time() - start_time < duration:
            try:
                # 尝试从同步响应队列获取数据
                chunk = self._sync_response_queue.get(timeout=0.1)
                if chunk:
                    received_data += chunk
            except queue.Empty:
                # 继续等待直到时间结束
                continue

        # 记录接收数据到性能指标
        if received_data:
            metrics_collector.record_receive(len(received_data))

        if received_data:
            # 尝试解码为字符串
            try:
                decoded_data = received_data.decode('utf-8')
                is_hex = False
            except UnicodeDecodeError:
                decoded_data = received_data.hex()
                is_hex = True

            return {
                'data': decoded_data,
                'raw_data': received_data,
                'is_hex': is_hex,
                'bytes_received': len(received_data),
                'pending_urc_count': self.get_pending_urc_count(),
                'success': True
            }
        else:
            return {
                'data': '',
                'raw_data': b'',
                'is_hex': False,
                'bytes_received': 0,
                'pending_urc_count': self.get_pending_urc_count(),
                'success': True
            }

    def _receive_at_response(self, original_cmd: str, timeout: float) -> Dict[str, Any]:
        """接收AT命令响应，简单地在超时时间内收集所有数据"""
        # 直接使用超时接收方法收集所有数据
        return self._receive_until_timeout(timeout)

    def send_string(self, data: str, encoding: str = 'utf-8') -> None:
        """
        发送字符串数据

        Args:
            data: 要发送的字符串
            encoding: 字符串编码，默认为utf-8
        """
        encoded_data = data.encode(encoding)
        self.send_data(encoded_data)

    def enter_sync_mode(self) -> None:
        """进入同步模式，所有接收到的数据将被路由到同步响应队列"""
        self._sync_mode.set()
        # 清空之前可能存在的响应数据
        while not self._sync_response_queue.empty():
            try:
                self._sync_response_queue.get_nowait()
            except queue.Empty:
                break

    def exit_sync_mode(self) -> None:
        """退出同步模式，所有接收到的数据将被路由到URC队列"""
        self._sync_mode.clear()

    def receive_sync(self, timeout: float = None, stop_pattern: str = None) -> Optional[Dict[str, Any]]:
        """
        在同步模式下接收数据

        Args:
            timeout: 超时时间（秒），None表示使用默认值
            stop_pattern: 停止模式，当接收到此模式时停止接收

        Returns:
            接收到的数据和相关信息的字典
        """
        if timeout is None:
            timeout = self._current_operation_timeout

        start_time = time.time()
        received_data = b""

        while time.time() - start_time < timeout:
            try:
                # 尝试从同步响应队列获取数据
                chunk = self._sync_response_queue.get(timeout=0.1)
                if chunk:
                    received_data += chunk

                    # 检查是否包含停止模式
                    if stop_pattern and stop_pattern.encode() in received_data:
                        self.logger.debug(f"找到停止模式: {stop_pattern}")
                        break
            except queue.Empty:
                # 继续等待
                continue

        # 如果超时仍未收到停止模式，则视为超时
        if stop_pattern and stop_pattern.encode() not in received_data:
            self.logger.warning(f"接收超时，未找到停止模式: {stop_pattern}")
            raise SerialTimeoutError(f"接收超时，未找到停止模式: {stop_pattern}")

        # 记录接收数据到性能指标
        if received_data:
            metrics_collector.record_receive(len(received_data))

        if received_data:
            # 尝试解码为字符串
            try:
                decoded_data = received_data.decode('utf-8')
                is_hex = False
            except UnicodeDecodeError:
                decoded_data = received_data.hex()
                is_hex = True

            return {
                'data': decoded_data,
                'raw_data': received_data,
                'is_hex': is_hex,
                'found_stop_pattern': stop_pattern.encode() in received_data if stop_pattern else False,
                'bytes_received': len(received_data)
            }
        else:
            return None

    def receive_for_timeout(self, duration: float) -> Dict[str, Any]:
        """
        按指定时间接收数据

        Args:
            duration: 接收时间（秒）

        Returns:
            接收到的数据和相关信息的字典
        """
        start_time = time.time()
        received_data = b""

        while time.time() - start_time < duration:
            try:
                # 尝试从同步响应队列获取数据
                chunk = self._sync_response_queue.get(timeout=0.1)
                if chunk:
                    received_data += chunk
            except queue.Empty:
                # 继续等待直到时间结束
                continue

        # 记录接收数据到性能指标
        if received_data:
            metrics_collector.record_receive(len(received_data))

        if received_data:
            # 尝试解码为字符串
            try:
                decoded_data = received_data.decode('utf-8')
                is_hex = False
            except UnicodeDecodeError:
                decoded_data = received_data.hex()
                is_hex = True

            return {
                'data': decoded_data,
                'raw_data': received_data,
                'is_hex': is_hex,
                'bytes_received': len(received_data)
            }
        else:
            return {
                'data': '',
                'raw_data': b'',
                'is_hex': False,
                'bytes_received': 0
            }

    def receive_no_wait(self) -> Dict[str, Any]:
        """
        立即发送，不等待响应

        Returns:
            操作结果字典
        """
        return {
            'success': True,
            'message': '数据已发送，不等待响应'
        }

    def get_urc_messages(self, clear: bool = True) -> List[Dict[str, Any]]:
        """
        获取URC消息

        Args:
            clear: 是否清空URC队列

        Returns:
            URC消息列表
        """
        urc_messages = []

        while True:
            try:
                if clear:
                    urc_data = self._urc_queue.get_nowait()
                else:
                    urc_data = self._urc_queue.get(timeout=0.1)

                # 处理URC数据
                try:
                    decoded_data = urc_data.decode('utf-8')
                    is_hex = False
                except UnicodeDecodeError:
                    decoded_data = urc_data.hex()
                    is_hex = True

                urc_messages.append({
                    'data': decoded_data,
                    'raw_data': urc_data,
                    'is_hex': is_hex,
                    'timestamp': time.time()
                })

                metrics_collector.record_urc_message()
            except queue.Empty:
                break

        return urc_messages

    def get_pending_urc_count(self) -> int:
        """
        获取待处理的URC消息数量

        Returns:
            待处理URC消息数量
        """
        return self._urc_queue.qsize()

    def get_driver_status(self) -> Dict[str, Any]:
        """
        获取驱动状态

        Returns:
            驱动状态信息字典
        """
        return {
            'is_initialized': self._is_initialized,
            'is_connected': self.is_connected(),
            'sync_mode': self._sync_mode.is_set(),
            'pending_urc_count': self.get_pending_urc_count(),
            'sync_response_queue_size': self._sync_response_queue.qsize()
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标

        Returns:
            性能指标字典
        """
        return metrics_collector.get_metrics()

    def reset_performance_metrics(self) -> None:
        """重置性能指标"""
        metrics_collector.reset_metrics()