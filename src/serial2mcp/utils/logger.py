"""
日志配置工具
设置项目日志记录格式和级别
"""
import structlog
import logging
import sys
from typing import Any
from datetime import datetime
from pathlib import Path
import os


def setup_logging(level: str = "INFO", format_type: str = "console", enable_file_logging: bool = True, log_dir: str = "logs/tool_log", disable_console: bool = True) -> None:
    """
    配置项目日志系统

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: 日志格式类型 ("json", "console")
        enable_file_logging: 是否启用文件日志
        log_dir: 日志文件存储目录
        disable_console: 是否禁用控制台输出（对于MCP服务器应该设为True）
    """
    # 设置日志级别
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')

    # 创建日志目录
    if enable_file_logging:
        log_path = Path(log_dir)
        date_path = log_path / datetime.now().strftime("%Y") / datetime.now().strftime("%m") / datetime.now().strftime("%d")
        date_path.mkdir(parents=True, exist_ok=True)

        # 生成带时间戳的日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = date_path / f"serial-agent-mcp_{timestamp}.log"

        # 确保日志文件目录存在
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # 配置根日志记录器，可以选择性地输出到控制台或仅输出到文件
    handlers = []

    # 添加文件处理器（如果启用文件日志）
    if enable_file_logging and 'log_file_path' in locals():
        # 对于文件日志使用标准logging格式
        try:
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            handlers.append(file_handler)
        except Exception as e:
            print(f"无法创建日志文件 {log_file_path}: {e}", file=sys.stderr)
            # 如果无法创建日志文件，仍然继续运行，但禁用文件日志
            enable_file_logging = False

    # 如果不是MCP服务器环境，可以添加控制台处理器
    if not disable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)

    # 配置根日志记录器
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        force=True  # 强制重新配置
    )

    # 配置结构化日志，让structlog使用标准logging作为后端
    if format_type == "json":
        # JSON 格式日志配置
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,  # 让structlog使用logging处理器
        ]
    else:
        # 普通格式日志配置（避免颜色代码）
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,  # 让structlog使用logging处理器
        ]

    # 配置structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    获取结构化日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        配置好的结构化日志记录器
    """
    return structlog.get_logger(name)


# 全局日志记录器
logger = get_logger("serial2mcp")