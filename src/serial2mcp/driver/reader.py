"""
后台数据接收线程
负责持续从串口读取数据并进行分流处理
"""
import threading
import queue
import time
from typing import Optional
import serial
from ..utils.logger import get_logger
from ..utils.exceptions import SerialConnectionError
from ..utils.config import config_manager
from ..utils.metrics import metrics_collector
from ..utils.serial_data_logger import serial_data_logger_manager


class BackgroundReader:
    """后台数据接收线程，负责持续从串口读取数据并根据模式进行分流处理"""

    def __init__(self):
        """初始化后台接收线程"""
        self.logger = get_logger("background_reader")
        self.config = config_manager.get_config()
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # 依赖组件
        self.connection_manager = None
        self.sync_mode_event = None
        self.sync_response_queue = None
        self.async_queue = None
        self.current_port = None  # 当前连接的端口

        # 本地缓冲区和状态
        self._async_buffer = bytearray()
        self._last_receive_time = time.time()
        self._is_running = False

    def initialize(self,
                   connection_manager,
                   sync_mode_event: threading.Event,
                   sync_response_queue: queue.Queue,
                   async_queue: queue.Queue) -> None:
        """
        初始化后台接收线程的依赖

        Args:
            connection_manager: 连接管理器实例
            sync_mode_event: 同步模式事件
            sync_response_queue: 同步响应队列
            async_queue: 异步消息队列
        """
        self.connection_manager = connection_manager
        self.sync_mode_event = sync_mode_event
        self.sync_response_queue = sync_response_queue
        self.async_queue = async_queue
        self.logger.info("后台接收线程初始化完成")

    def start(self, port: str = None) -> None:
        """
        启动后台接收线程

        Args:
            port: 当前连接的端口名称，用于日志记录
        """
        if self._is_running:
            self.logger.warning("后台接收线程已在运行中")
            return

        if port:
            self.current_port = port
            self.logger.info(f"为端口 {port} 启动后台接收线程")
            # 启动串口通信日志记录
            if self.config.logging.com_log_enabled:
                self.logger.info(f"为端口 {port} 启动通信日志记录")
                serial_data_logger_manager.start_logging(port)
            else:
                self.logger.info(f"串口通信日志记录已禁用 (COM_LOG_ENABLED={self.config.logging.com_log_enabled})")

        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self._is_running = True
        self.logger.info(f"后台接收线程已为 {port} 启动")

    def stop(self) -> None:
        """停止后台接收线程"""
        if not self._is_running:
            return

        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)  # 等待最多2秒让线程结束

        self._is_running = False

        # 停止串口通信日志记录
        if self.current_port and self.config.logging.com_log_enabled:
            serial_data_logger_manager.stop_logging(self.current_port)
            self.current_port = None

        self.logger.info("后台接收线程已停止")

    def _run(self) -> None:
        """后台接收线程主循环"""
        self.logger.debug("后台接收线程主循环开始")

        # 为RX数据添加消息缓冲区，用于基于回车换行符的完整消息记录
        rx_message_buffer = bytearray()

        while not self.stop_event.is_set():
            try:
                # 检查串口是否连接
                if not self.connection_manager or not self.connection_manager.is_connected():
                    # 短暂休眠，避免过度占用CPU
                    time.sleep(0.1)
                    continue

                # 检查是否有可读数据
                if self.connection_manager.serial_port and self.connection_manager.serial_port.in_waiting > 0:
                    # 读取可用数据，使用较小的读取块以减少数据拼接问题
                    chunk_size = min(1024, self.connection_manager.serial_port.in_waiting)
                    data = self.connection_manager.read(chunk_size)

                    if data:
                        # 记录接收数据到性能指标
                        metrics_collector.record_receive(len(data))

                        # 基于回车换行符的消息边界记录日志
                        if self.current_port and self.config.logging.com_log_enabled:
                            # 将新数据添加到RX缓冲区
                            rx_message_buffer.extend(data)

                            # 检查是否有完整的基于回车换行的消息
                            while b'\n' in rx_message_buffer:
                                # 找到第一个换行符的位置
                                newline_idx = rx_message_buffer.find(b'\n')
                                # 提取完整的消息（包含换行符）
                                complete_message = rx_message_buffer[:newline_idx + 1]
                                # 保留剩余数据
                                rx_message_buffer = rx_message_buffer[newline_idx + 1:]

                                # 记录完整的RX消息到日志
                                serial_data_logger_manager.log_data(self.current_port, 'RX', complete_message)

                            # 如果没有完整的消息，继续收集数据
                        else:
                            # 如果日志未启用，仍然需要更新接收时间
                            pass

                        # 根据当前模式决定数据流向
                        if self.sync_mode_event.is_set():
                            # 同步模式：直接发送到同步响应队列
                            try:
                                self.logger.debug(f"接收到同步模式数据: {len(data)} 字节")
                                self.sync_response_queue.put_nowait(data)
                                self.logger.debug(f"同步模式：发送 {len(data)} 字节到响应队列: {data!r}")

                                # 如果异步缓冲区有数据，需要强制推送到异步队列
                                if self._async_buffer:
                                    self.logger.debug("同步模式下刷新异步缓冲区")
                                    self._flush_async_buffer()

                            except queue.Full:
                                self.logger.error("同步响应队列已满")
                        else:
                            # 异步模式：添加到异步缓冲区
                            self.logger.debug(f"接收到异步模式数据: {len(data)} 字节")
                            self._async_buffer.extend(data)
                            self._last_receive_time = time.time()
                            self.logger.debug(f"异步模式：添加 {len(data)} 字节到异步缓冲区: {data!r}")

                # 检查异步缓冲区是否需要分包（基于空闲超时）
                self._check_async_idle_timeout()

                # 短暂休眠，避免过度占用CPU
                time.sleep(0.005)  # 减少休眠时间以提高响应性

            except serial.SerialException as e:
                if not self.stop_event.is_set():  # 如果不是主动停止
                    self.logger.error(f"串口读取异常: {e}")
                    metrics_collector.record_error()
                    # 短暂休眠后继续尝试
                    time.sleep(0.5)
            except Exception as e:
                if not self.stop_event.is_set():  # 如果不是主动停止
                    self.logger.error(f"后台接收线程发生未知错误: {e}")
                    metrics_collector.record_error()
                    # 短暂休眠后继续 try
                    time.sleep(0.5)

        # 线程结束前，处理剩余的RX缓冲区数据
        if rx_message_buffer and self.current_port and self.config.logging.com_log_enabled:
            # 记录未完成的消息（可能没有换行结尾）
            serial_data_logger_manager.log_data(self.current_port, 'RX', bytes(rx_message_buffer))

        # 线程结束前，确保异步缓冲区中的数据被处理
        self._flush_async_buffer()
        self.logger.debug("后台接收线程主循环结束")

    def _check_async_idle_timeout(self) -> None:
        """检查异步消息空闲超时，如果超过设定时间没有新数据，则分包"""
        current_time = time.time()
        idle_duration = current_time - self._last_receive_time

        # 如果异步缓冲区有数据且空闲时间超过阈值，则进行分包
        if (self._async_buffer and
            idle_duration >= self.config.driver.idle_timeout):
            self._flush_async_buffer()

    def _flush_async_buffer(self) -> None:
        """刷新异步缓冲区，将数据发送到异步消息队列"""
        if not self._async_buffer:
            return

        async_data = bytes(self._async_buffer)
        self._async_buffer.clear()

        try:
            # 尝试将异步消息数据放入队列
            self.async_queue.put_nowait(async_data)
            self.logger.debug(f"异步缓冲区数据已推送到队列: {len(async_data)} 字节")
        except queue.Full:
            self.logger.error("异步消息队列已满，数据丢失")
            metrics_collector.record_async_overflow()

        # 更新最后接收时间
        self._last_receive_time = time.time()

    def is_running(self) -> bool:
        """
        检查后台接收线程是否在运行

        Returns:
            线程运行状态
        """
        return self._is_running and self.thread and self.thread.is_alive()

    def get_reader_status(self) -> dict:
        """
        获取接收线程状态

        Returns:
            接收线程状态信息
        """
        return {
            'is_running': self.is_running(),
            'async_buffer_size': len(self._async_buffer),
            'last_receive_time': self._last_receive_time,
            'idle_duration': time.time() - self._last_receive_time
        }