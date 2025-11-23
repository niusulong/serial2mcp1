"""
自定义异常定义
定义项目中使用的各种自定义异常类型
"""

class SerialAgentError(Exception):
    """串口代理工具的基础异常类"""
    pass


class SerialConnectionError(SerialAgentError):
    """串口连接相关异常"""
    pass


class SerialConfigurationError(SerialAgentError):
    """串口配置相关异常"""
    pass


class SerialDataError(SerialAgentError):
    """串口数据处理相关异常"""
    pass


class MCPProtocolError(SerialAgentError):
    """MCP协议相关异常"""
    pass


class DataParsingError(SerialAgentError):
    """数据解析相关异常"""
    pass


class TimeoutError(SerialAgentError):
    """超时相关异常"""
    pass


class InvalidInputError(SerialAgentError):
    """无效输入相关异常"""
    pass


class URCHandlerError(SerialAgentError):
    """URC处理相关异常"""
    pass


class DriverNotInitializedError(SerialAgentError):
    """驱动未初始化异常"""
    pass