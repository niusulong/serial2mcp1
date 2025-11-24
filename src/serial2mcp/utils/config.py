"""
配置管理工具
管理项目配置参数和默认值
"""
import os
import json
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class SerialConfig:
    """串口配置数据类"""
    port: str = ""
    baudrate: int = 115200
    bytesize: int = 8
    parity: str = 'N'  # None, Even, Odd, Mark, Space
    stopbits: int = 1
    timeout: Optional[float] = 5.0
    xonxoff: bool = False
    rtscts: bool = False
    dsrdtr: bool = False


@dataclass
class MCPConfig:
    """MCP协议配置数据类"""
    host: str = "127.0.0.1"
    port: int = 3000
    max_connections: int = 100
    heartbeat_interval: float = 30.0  # 心跳间隔（秒）


@dataclass
class LoggingConfig:
    """日志配置数据类"""
    com_log_enabled: bool = True  # 启用串口通信日志
    tool_log_enabled: bool = True  # 启用工具运行日志
    com_log_path: str = "logs/com_log"  # 串口日志存储路径
    tool_log_path: str = "logs/tool_log"  # 工具日志存储路径
    retention_days: int = 30  # 日志保留天数
    max_file_size_mb: int = 10  # 最大文件大小MB
    level: str = "INFO"  # 日志级别


@dataclass
class DriverConfig:
    """驱动配置数据类"""
    idle_timeout: float = 0.1  # 空闲超时时间（秒）
    max_buffer_size: int = 4096  # 最大缓冲区大小
    urc_buffer_size: int = 1000  # URC缓冲区大小
    sync_timeout_default: float = 5.0  # 同步操作默认超时时间
    reconnect_attempts: int = 3  # 重连尝试次数
    reconnect_delay: float = 1.0  # 重连延迟时间


@dataclass
class AppConfig:
    """应用配置数据类"""
    serial: SerialConfig = None
    mcp: MCPConfig = None
    driver: DriverConfig = None
    logging: LoggingConfig = None

    def __post_init__(self):
        if self.serial is None:
            self.serial = SerialConfig()
        if self.mcp is None:
            self.mcp = MCPConfig()
        if self.driver is None:
            self.driver = DriverConfig()
        if self.logging is None:
            self.logging = LoggingConfig()


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = AppConfig()

        if config_file and os.path.exists(config_file):
            self.load_from_file(config_file)
        else:
            self.load_from_environment()

    def load_from_file(self, file_path: str) -> None:
        """
        从文件加载配置

        Args:
            file_path: 配置文件路径
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载串口配置
            if 'serial' in data:
                serial_data = data['serial']
                self.config.serial = SerialConfig(
                    port=serial_data.get('port', ''),
                    baudrate=serial_data.get('baudrate', 115200),
                    bytesize=serial_data.get('bytesize', 8),
                    parity=serial_data.get('parity', 'N'),
                    stopbits=serial_data.get('stopbits', 1),
                    timeout=serial_data.get('timeout', 5.0),
                    xonxoff=serial_data.get('xonxoff', False),
                    rtscts=serial_data.get('rtscts', False),
                    dsrdtr=serial_data.get('dsrdtr', False)
                )

            # 加载MCP配置
            if 'mcp' in data:
                mcp_data = data['mcp']
                self.config.mcp = MCPConfig(
                    host=mcp_data.get('host', '127.0.0.1'),
                    port=mcp_data.get('port', 3000),
                    max_connections=mcp_data.get('max_connections', 100),
                    heartbeat_interval=mcp_data.get('heartbeat_interval', 30.0)
                )

            # 加载驱动配置
            if 'driver' in data:
                driver_data = data['driver']
                self.config.driver = DriverConfig(
                    idle_timeout=driver_data.get('idle_timeout', 0.1),
                    max_buffer_size=driver_data.get('max_buffer_size', 4096),
                    urc_buffer_size=driver_data.get('urc_buffer_size', 1000),
                    sync_timeout_default=driver_data.get('sync_timeout_default', 5.0),
                    reconnect_attempts=driver_data.get('reconnect_attempts', 3),
                    reconnect_delay=driver_data.get('reconnect_delay', 1.0)
                )

            # 加载日志配置
            if 'logging' in data:
                log_data = data['logging']
                self.config.logging = LoggingConfig(
                    com_log_enabled=log_data.get('com_log_enabled', True),
                    tool_log_enabled=log_data.get('tool_log_enabled', True),
                    com_log_path=log_data.get('com_log_path', 'logs/com_log'),
                    tool_log_path=log_data.get('tool_log_path', 'logs/tool_log'),
                    retention_days=log_data.get('retention_days', 30),
                    max_file_size_mb=log_data.get('max_file_size_mb', 10),
                    level=log_data.get('level', 'INFO')
                )

        except Exception as e:
            print(f"从文件加载配置时出错: {e}")
            # 使用默认配置
            self.config = AppConfig()

    def load_from_environment(self) -> None:
        """从环境变量加载配置"""
        # 串口相关环境变量
        self.config.serial.port = os.getenv('SERIAL_PORT', self.config.serial.port)
        baudrate_env = os.getenv('SERIAL_BAUDRATE')
        if baudrate_env:
            self.config.serial.baudrate = int(baudrate_env)

        timeout_env = os.getenv('SERIAL_TIMEOUT')
        if timeout_env:
            self.config.serial.timeout = float(timeout_env)

        # MCP相关环境变量
        self.config.mcp.host = os.getenv('MCP_HOST', self.config.mcp.host)
        port_env = os.getenv('MCP_PORT')
        if port_env:
            self.config.mcp.port = int(port_env)

        max_conn_env = os.getenv('MCP_MAX_CONNECTIONS')
        if max_conn_env:
            self.config.mcp.max_connections = int(max_conn_env)

        # 驱动相关环境变量
        idle_timeout_env = os.getenv('DRIVER_IDLE_TIMEOUT')
        if idle_timeout_env:
            self.config.driver.idle_timeout = float(idle_timeout_env)

        max_buffer_env = os.getenv('DRIVER_MAX_BUFFER_SIZE')
        if max_buffer_env:
            self.config.driver.max_buffer_size = int(max_buffer_env)

        # 日志相关环境变量
        self.config.logging.com_log_enabled = os.getenv('COM_LOG_ENABLED', str(self.config.logging.com_log_enabled)).lower() == 'true'
        self.config.logging.tool_log_enabled = os.getenv('TOOL_LOG_ENABLED', str(self.config.logging.tool_log_enabled)).lower() == 'true'
        self.config.logging.com_log_path = os.getenv('COM_LOG_PATH', self.config.logging.com_log_path)
        self.config.logging.tool_log_path = os.getenv('TOOL_LOG_PATH', self.config.logging.tool_log_path)
        retention_days_env = os.getenv('LOG_RETENTION_DAYS')
        if retention_days_env:
            self.config.logging.retention_days = int(retention_days_env)
        max_file_size_env = os.getenv('LOG_MAX_FILE_SIZE_MB')
        if max_file_size_env:
            self.config.logging.max_file_size_mb = int(max_file_size_env)
        # 检查两个环境变量名称：SERIAL2MCP_LOG_LEVEL（配置文件中使用的）和LOG_LEVEL（代码默认的）
        self.config.logging.level = os.getenv('SERIAL2MCP_LOG_LEVEL', os.getenv('LOG_LEVEL', self.config.logging.level))

    def save_to_file(self, file_path: str) -> None:
        """
        保存配置到文件

        Args:
            file_path: 配置文件路径
        """
        config_dict = {
            'serial': asdict(self.config.serial),
            'mcp': asdict(self.config.mcp),
            'driver': asdict(self.config.driver),
            'logging': asdict(self.config.logging)
        }

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)

    def get_config(self) -> AppConfig:
        """
        获取当前配置

        Returns:
            当前配置对象
        """
        return self.config


# 全局配置管理器实例
config_manager = ConfigManager()