"""
日志配置工具
设置项目日志记录格式和级别
"""
import structlog
import logging
import sys
from typing import Any


def setup_logging(level: str = "INFO", format_type: str = "json") -> None:
    """
    配置项目日志系统

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: 日志格式类型 ("json", "console")
    """
    # 设置日志级别
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')

    # 配置结构化日志
    if format_type == "json":
        # JSON 格式日志配置
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.filter_by_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.UnicodeDecoder(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    else:
        # 控制台格式日志配置
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.filter_by_level,
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.UnicodeDecoder(),
                structlog.processors.format_exc_info,
                structlog.dev.ConsoleRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    # 配置根日志记录器
    logging.basicConfig(
        level=numeric_level,
        format="%(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # 强制重新配置
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