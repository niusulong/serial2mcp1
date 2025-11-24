"""
pytest 配置文件
"""
import os
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 设置日志相关环境变量
os.environ.setdefault('SERIAL2MCP_LOG_LEVEL', 'INFO')
os.environ.setdefault('COM_LOG_ENABLED', 'true')
os.environ.setdefault('TOOL_LOG_ENABLED', 'true')
os.environ.setdefault('COM_LOG_PATH', 'logs/com_log')
os.environ.setdefault('TOOL_LOG_PATH', 'logs/tool_log')
os.environ.setdefault('LOG_RETENTION_DAYS', '30')
os.environ.setdefault('LOG_MAX_FILE_SIZE_MB', '10')

# 确保日志目录存在
(Path.cwd() / 'logs' / 'com_log').mkdir(parents=True, exist_ok=True)
(Path.cwd() / 'logs' / 'tool_log').mkdir(parents=True, exist_ok=True)