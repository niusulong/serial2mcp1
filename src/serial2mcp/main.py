"""
MCP 服务器入口点文件
负责启动和运行 MCP 服务器
"""
import asyncio
import sys
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from .facade.tool_facade import SerialToolFacade
from .utils.logger import setup_logging
from .utils.config import config_manager
from .utils.serial_data_logger import serial_data_logger_manager
import mcp.types as types
import atexit


async def main():
    """主函数 - 使用官方mcp库启动服务器"""
    # 获取配置
    config = config_manager.get_config()

    # 初始化日志 - 只写入文件，不在控制台输出
    setup_logging(
        level=config.logging.level,
        format_type="console",  # 可以根据需要设置为 "json"
        enable_file_logging=config.logging.tool_log_enabled,
        log_dir=config.logging.tool_log_path,
        disable_console=True  # MCP服务器不应输出到控制台
    )

    # 创建工具门面实例
    facade = SerialToolFacade()

    # 创建MCP服务器
    server = Server(
        name="serial-agent-mcp",
        version="1.0.0",
        instructions="智能串口 MCP 工具，用于与串口设备通信"
    )

    # 注册退出时的清理函数
    def cleanup_resources():
        """在程序退出时清理资源"""
        try:
            # 停止所有串口通信日志记录
            serial_data_logger_manager.stop_all_logging()
            print("已清理日志资源", file=sys.stderr)  # 使用stderr输出清理信息
        except Exception as e:
            print(f"清理资源时出错: {e}", file=sys.stderr)

    atexit.register(cleanup_resources)

    # 定义并注册 list_tools 处理器
    @server.list_tools()
    async def handle_list_tools(request: types.ListToolsRequest) -> types.ListToolsResult:
        """处理 list_tools 请求"""
        tools = [
            types.Tool(
                name="list_ports",
                description="列出当前系统所有可用的串口设备。",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            types.Tool(
                name="configure_connection",
                description="打开或关闭串口，配置参数。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "port": {
                            "type": "string",
                            "description": "串口设备路径"
                        },
                        "baudrate": {
                            "type": "integer",
                            "description": "波特率"
                        },
                        "timeout": {
                            "type": "number",
                            "description": "超时时间"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["open", "close"],
                            "description": "操作类型：'open'打开串口，'close'关闭串口"
                        }
                    },
                    "required": ["action"]
                }
            ),
            types.Tool(
                name="send_data",
                description="发送数据并根据策略获取响应。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "payload": {
                            "type": "string",
                            "description": "发送内容"
                        },
                        "encoding": {
                            "type": "string",
                            "enum": ["utf8", "hex"],
                            "description": "编码格式：'utf8'或'hex'"
                        },
                        "wait_policy": {
                            "type": "string",
                            "enum": ["keyword", "timeout", "none", "at_command"],
                            "description": "等待策略：'keyword'关键字等待模式，'timeout'纯时间等待模式，'none'射后不理模式，'at_command'AT命令专用模式"
                        },
                        "stop_pattern": {
                            "type": "string",
                            "description": "仅在 keyword 模式下有效（如 'OK'）"
                        },
                        "timeout_ms": {
                            "type": "integer",
                            "description": "等待超时时间（毫秒）"
                        }
                    },
                    "required": ["payload", "wait_policy"]
                }
            ),
            types.Tool(
                name="read_urc",
                description="读取后台缓冲区中积累的未处理消息（URC）。",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]
        return types.ListToolsResult(tools=tools)

    # 定义并注册 call_tool 处理器
    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict):
        """处理 call_tool 请求"""
        try:
            if name == "list_ports":
                result = facade.list_ports()
            elif name == "configure_connection":
                result = facade.configure_connection(**arguments)
            elif name == "send_data":
                result = facade.send_data(**arguments)
            elif name == "read_urc":
                result = facade.read_urc()
            else:
                return [
                    types.TextContent(
                        type="text",
                        text=f"未知工具: {name}"
                    )
                ], {"success": False, "error": f"未知工具: {name}"}

            # 将结果包装为适当的MCP内容格式
            if result.get("success", True):
                # 成功时返回内容
                return [
                    types.TextContent(
                        type="text",
                        text=str(result)
                    )
                ], result
            else:
                # 失败时返回错误消息
                return [
                    types.TextContent(
                        type="text",
                        text=f"错误: {result.get('error_message', '未知错误')}"
                    )
                ], result
        except Exception as e:
            error_content = {
                "success": False,
                "error_message": f"工具调用失败: {str(e)}"
            }
            return [
                types.TextContent(
                    type="text",
                    text=f"工具调用失败: {str(e)}"
                )
            ], error_content

    # 创建初始化选项
    init_options = server.create_initialization_options(
        experimental_capabilities={}
    )

    # 启动服务器，使用stdio协议
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            init_options
        )


if __name__ == "__main__":
    asyncio.run(main())