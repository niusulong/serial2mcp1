# Serial-Agent-MCP

**版本号:** V1.3
**项目代号:** Serial-Agent-MCP

基于 MCP (Model Context Protocol) 的智能串口交互工具，作为大语言模型与物理硬件之间的桥梁。

## 项目背景

传统串口助手只能进行机械的收发，无法理解协议逻辑。本项目旨在开发一个基于 Model Context Protocol (MCP) 的串口工具，作为大语言模型（LLM）的物理接口。工具本体不硬编码任何 AT 指令集或特定协议解析逻辑，由 LLM 在运行时决定发送什么、怎么接收、何时超时。

## 工具用途

- **智能数据分流**: 自动区分同步响应和异步消息
- **多协议支持**: 兼顾 AT 指令（文本行）与 纯数据传输（HEX/二进制）
- **智能收发接口**: 支持多种模式的智能数据收发
- **零数据丢失**: 确保所有数据被正确处理
- **实时交互**: 与大语言模型无缝集成进行实时串口操作

## 核心功能

1. **list_ports**: 列出当前系统所有可用的串口设备
   - 无输入参数
   - 返回设备列表(端口、描述、硬件ID)

2. **configure_connection**: 打开或关闭串口，配置参数
   - 输入: port(端口), baudrate(波特率), action(操作类型)
   - 返回: 连接状态信息

3. **send_data**: 发送数据并根据策略获取响应
   - 输入: payload(发送内容), encoding(编码格式), wait_policy(等待策略), stop_pattern(停止模式), timeout_ms(超时时间)
   - 支持多种等待策略: keyword(关键字模式), timeout(超时模式), none(射后不理)
   - 返回: 发送结果和响应数据

4. **read_async_messages**: 读取后台缓冲区中积累的异步消息
   - 无输入参数
   - 返回: 异步消息列表

## 安装和配置

### 环境要求
- Python 3.8+
- Windows/Linux/macOS 操作系统
- 可用串口设备

### 依赖安装
```bash
pip install -r requirements.txt
```

### MCP 服务器配置

在使用此MCP服务器时，需要在MCP客户端配置中添加如下配置：

```json
{
  "mcpServers": {
    "serial-agent-mcp": {
      "command": "python",
      "args": [
        "-m",
        "serial2mcp.main"
      ],
      "env": {
        "PYTHONPATH": "D:\\niusulong\\serial2mcp--1\\src",
        "SERIAL2MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## 使用方法

### 1. 启动 MCP 服务器
```bash
python -m serial2mcp.main
```

### 2. 与大语言模型集成
将工具接口定义提供给大语言模型，模型即可通过MCP协议调用串口功能。
