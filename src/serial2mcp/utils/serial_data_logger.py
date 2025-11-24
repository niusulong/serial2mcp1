"""
串口数据日志记录器
负责记录串口通信的原始数据到文件
"""
import os
import time
from datetime import datetime
from typing import Optional, Union, BinaryIO
import threading
from pathlib import Path


class SerialDataLogger:
    """
    串口数据日志记录器
    记录串口通信的原始数据，支持HEX和字符串两种格式
    """
    
    def __init__(self, port_name: str, log_dir: str = "logs/com_log"):
        """
        初始化串口数据日志记录器

        Args:
            port_name: 串口名称 (如 'COM1', '/dev/ttyUSB0')
            log_dir: 日志存储目录
        """
        self.port_name = port_name.replace('/', '_').replace('\\', '_')  # 确保文件名安全
        self.log_dir = Path(log_dir)
        self.hex_file: Optional[BinaryIO] = None
        self.txt_file: Optional[BinaryIO] = None
        self.file_lock = threading.Lock()  # 确保文件操作线程安全
        self.is_logging = False
        
        # 创建日志目录
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def start_logging(self) -> None:
        """开始记录日志"""
        with self.file_lock:
            if self.is_logging:
                return
            
            # 生成带时间戳的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            hex_filename = f"{self.port_name}_{timestamp}.hex"
            txt_filename = f"{self.port_name}_{timestamp}.txt"
            
            # 创建日期子目录
            date_dir = self.log_dir / datetime.now().strftime("%Y") / datetime.now().strftime("%m") / datetime.now().strftime("%d")
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # 打开日志文件
            self.hex_file_path = date_dir / hex_filename
            self.txt_file_path = date_dir / txt_filename
            
            self.hex_file = open(self.hex_file_path, 'a', encoding='utf-8')
            self.txt_file = open(self.txt_file_path, 'a', encoding='utf-8')
            
            self.is_logging = True
            
            # 记录开始日志
            start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            hex_start_entry = f"[{start_time_str}] *** LOG START ***\n"
            txt_start_entry = f"[{start_time_str}] *** LOG START ***\n"
            
            self.hex_file.write(hex_start_entry)
            self.txt_file.write(txt_start_entry)
            self.hex_file.flush()
            self.txt_file.flush()
    
    def stop_logging(self) -> None:
        """停止记录日志"""
        with self.file_lock:
            if not self.is_logging:
                return
            
            # 记录结束日志
            end_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            hex_end_entry = f"[{end_time_str}] *** LOG END ***\n"
            txt_end_entry = f"[{end_time_str}] *** LOG END ***\n"
            
            if self.hex_file:
                self.hex_file.write(hex_end_entry)
                self.hex_file.flush()
                self.hex_file.close()
                self.hex_file = None
            
            if self.txt_file:
                self.txt_file.write(txt_end_entry)
                self.txt_file.flush()
                self.txt_file.close()
                self.txt_file = None
            
            self.is_logging = False
    
    def log_data(self, direction: str, data: bytes) -> None:
        """
        记录数据到日志文件

        Args:
            direction: 数据流向 ('TX' 或 'RX')
            data: 要记录的字节数据
        """
        if not self.is_logging or not data:
            return
        
        with self.file_lock:
            if not self.hex_file or not self.txt_file:
                return
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            # 记录HEX格式
            hex_data = " ".join([f"{b:02X}" for b in data])
            hex_entry = f"[{timestamp}] {direction} -> {hex_data}\n"
            self.hex_file.write(hex_entry)
            
            # 记录字符串格式
            try:
                str_data = data.decode('utf-8', errors='replace')
                # 确保特殊字符在字符串中正确显示
                str_data = str_data.replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t')
            except:
                str_data = repr(data)[1:-1]  # 使用repr并去除引号
            txt_entry = f"[{timestamp}] {direction} -> {str_data}\n"
            self.txt_file.write(txt_entry)
            
            # 立即刷新确保数据写入
            self.hex_file.flush()
            self.txt_file.flush()
    
    def __del__(self):
        """析构函数，确保日志文件被关闭"""
        self.stop_logging()


class SerialDataLoggerManager:
    """
    串口数据日志记录器管理器
    管理多个串口的数据日志记录器
    """
    
    def __init__(self, log_dir: str = "logs/com_log"):
        self.loggers = {}
        self.log_dir = log_dir
        self.lock = threading.Lock()
    
    def get_logger(self, port_name: str) -> SerialDataLogger:
        """
        获取指定串口的日志记录器

        Args:
            port_name: 串口名称

        Returns:
            串口数据日志记录器实例
        """
        with self.lock:
            if port_name not in self.loggers:
                self.loggers[port_name] = SerialDataLogger(port_name, self.log_dir)
            return self.loggers[port_name]
    
    def start_logging(self, port_name: str) -> None:
        """
        开始记录指定串口的日志

        Args:
            port_name: 串口名称
        """
        logger = self.get_logger(port_name)
        logger.start_logging()
    
    def stop_logging(self, port_name: str) -> None:
        """
        停止记录指定串口的日志

        Args:
            port_name: 串口名称
        """
        with self.lock:
            if port_name in self.loggers:
                self.loggers[port_name].stop_logging()
                del self.loggers[port_name]
    
    def log_data(self, port_name: str, direction: str, data: bytes) -> None:
        """
        记录指定串口的数据

        Args:
            port_name: 串口名称
            direction: 数据流向 ('TX' 或 'RX')
            data: 要记录的字节数据
        """
        logger = self.get_logger(port_name)
        logger.log_data(direction, data)
    
    def stop_all_logging(self) -> None:
        """停止所有串口的日志记录"""
        with self.lock:
            for logger in list(self.loggers.values()):
                logger.stop_logging()
            self.loggers.clear()


# 全局串口数据日志管理器实例
serial_data_logger_manager = SerialDataLoggerManager()