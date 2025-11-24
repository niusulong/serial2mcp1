# 智能串口 MCP 工具配置与使用方式文档

**版本号:** V1.3
**项目代号:** Serial-Agent-MCP
**创建日期:** 2025年11月24日

## 1. 简介

本文档描述了智能串口 MCP 工具的配置与使用方式，包括 MCP 服务器的部署、串口设备的连接管理、以及不同模式下的数据交互方式。该工具通过 MCP (Model Context Protocol) 协议与大语言模型集成，实现智能化的串口通信。

## 2. 环境准备

### 2.1 系统要求
- Python 3.8+
- Windows/Linux/macOS 操作系统
- 可用串口设备

### 2.2 依赖安装
```bash
pip install -r requirements.txt
```

### 2.3 核心依赖说明
- **pyserial**: 串口通信库，支持跨平台串口操作
- **mcp**: 官方MCP协议实现库
- **structlog**: 结构化日志记录

## 3. MCP 服务器配置

### 3.1 服务器启动
```bash
# 启动 MCP 服务器
python -m serial2mcp.main
```

### 3.2 配置管理
系统使用配置管理器管理运行时配置，可以通过环境变量或配置文件进行设置：

```python
# 配置结构
{
  "serial": {
    "port": null,          # 默认端口
    "baudrate": 115200,    # 默认波特率
    "bytesize": 8,         # 数据位
    "parity": "N",         # 奇偶校验
    "stopbits": 1,         # 停止位
    "timeout": 5.0         # 超时时间
  },
  "driver": {
    "idle_timeout": 0.1,       # 空闲超时阈值（用于异步消息分包）
    "max_buffer_size": 4096,   # 最大缓冲区大小
    "urc_buffer_size": 1000,   # 异步消息缓冲区大小
    "sync_timeout_default": 5.0 # 同步模式默认超时时间
  }
}
```

### 3.3 启动参数
服务器通过 stdio 协议与 MCP 客户端通信，无需额外配置网络参数。

## 4. 工具使用方式

### 4.1 列出串口设备

#### 4.1.1 调用 list_ports 工具
使用 `list_ports` 工具获取系统中所有可用的串口设备：

```json
{
  "name": "list_ports",
  "arguments": {}
}
```

返回示例：
```json
{
  "success": true,
  "data": [
    {
      "port": "COM1",
      "description": "USB Serial Port (COM1)",
      "hardware_id": "USB\\VID_10C4&PID_EA60\\0001"
    }
  ]
}
```

### 4.2 串口连接管理

#### 4.2.1 打开串口连接
使用 `configure_connection` 工具打开串口连接：

```json
{
  "name": "configure_connection",
  "arguments": {
    "port": "COM1",
    "baudrate": 115200,
    "action": "open"
  }
}
```

返回示例：
```json
{
  "success": true,
  "message": "串口 COM1 连接成功",
  "port": "COM1",
  "baudrate": 115200
}
```

#### 4.2.2 关闭串口连接
使用 `configure_connection` 工具关闭串口连接：

```json
{
  "name": "configure_connection",
  "arguments": {
    "action": "close"
  }
}
```

返回示例：
```json
{
  "success": true,
  "message": "串口连接已断开"
}
```

### 4.3 数据发送与接收

该工具支持四种等待策略，可根据不同的应用场景选择：

#### 4.3.1 关键字等待模式 (Wait-for-Keyword)
发送数据并等待特定关键字出现：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CSQ\\r\\n",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "OK",
    "timeout_ms": 3000
  }
}
```

**说明**:
- `wait_policy: "keyword"`: 使用关键字等待模式
- `stop_pattern`: 指定停止模式，当接收到该模式时停止等待
- 需要使用 `\\r\\n` 来表示换行符

返回示例：
```json
{
  "success": true,
  "data": "+CSQ: 22,99\\r\\n\\r\\nOK\\r\\n",
  "raw_data": "b'\\x2b\\x43\\x53\\x51\\x3a\\x20\\x32\\x32\\x2c\\x39\\x39\\x0d\\x0a\\x0d\\x0a\\x4f\\x4b\\x0d\\x0a'",
  "is_hex": false,
  "found_stop_pattern": true,
  "pending_async_count": 0,
  "bytes_received": 18
}
```

#### 4.3.2 纯时间等待模式 (Wait-for-Timeout)
发送数据并等待指定时间后返回所有数据：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "01 03 00 00 00 06 C5 DB",
    "encoding": "hex",
    "wait_policy": "timeout",
    "timeout_ms": 500
  }
}
```

**说明**:
- `wait_policy: "timeout"`: 使用纯时间等待模式
- 在指定时间间隔内收集所有接收的数据

返回示例：
```json
{
  "success": true,
  "data": "01 03 0c 00 01 00 02 00 03 00 04 84 0b",
  "raw_data": "b'\\x01\\x03\\x0c\\x00\\x01\\x00\\x02\\x00\\x03\\x00\\x04\\x84\\x0b'",
  "is_hex": true,
  "bytes_received": 13,
  "pending_async_count": 0
}
```

#### 4.3.3 射后不理模式 (No-Wait/Fire-and-Forget)
发送数据后立即返回，不等待响应：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CMEE=1\\r\\n",
    "encoding": "utf8",
    "wait_policy": "none"
  }
}
```

**说明**:
- `wait_policy: "none"`: 射后不理模式
- 数据发送后立即返回，响应将在后台积累为异步消息

返回示例：
```json
{
  "success": true,
  "message": "数据已发送，不等待响应",
  "pending_async_count": 0
}
```

#### 4.3.4 AT命令模式 (AT Command Pattern)
专门用于AT命令交互，自动处理回显和响应：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CGMI\\r\\n",
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 3000
  }
}
```

**说明**:
- `wait_policy: "at_command"`: AT命令专用模式
- 专门优化用于AT指令交互，自动处理回显和响应
- 适合标准AT指令交互场景

返回示例：
```json
{
  "success": true,
  "data": "AT+CGMI\\r\\n\\r\\nSIMCOM INCORPORATED\\r\\n\\r\\nOK\\r\\n",
  "raw_data": "b'...'",
  "is_hex": false,
  "bytes_received": 34,
  "pending_async_count": 0
}
```

### 4.4 异步消息处理

#### 4.4.1 读取 异步消息
使用 `read_async_messages` 工具读取后台缓冲区中的未处理消息：

```json
{
  "name": "read_async_messages",
  "arguments": {}
}
```

返回示例：
```json
{
  "success": true,
  "data": [
    {
      "data": "+CMTI: \"SM\", 1",
      "raw_data": "b'+CMTI: \"SM\", 1'",
      "is_hex": false,
      "timestamp": 1700123456.789
    }
  ],
  "count": 1
}
```

**重要提示**:
- 每次调用 `read_async_messages` 会清除已读取的异步消息
- 建议在交互后检查 `pending_async_count` 字段，如不为0则调用 `read_async_messages` 处理

## 5. 典型使用场景

### 5.1 AT 指令交互
标准 AT 指令交互，推荐使用 at_command 或 keyword 模式：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CSQ\\r\\n",
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 3000
  }
}
```

或者使用 keyword 模式：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CSQ\\r\\n",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "OK",
    "timeout_ms": 3000
  }
}
```

### 5.2 二进制协议交互
发送十六进制数据并等待超时读取：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "01 03 00 00 00 06 C5 DB",
    "encoding": "hex",
    "wait_policy": "timeout",
    "timeout_ms": 1000
  }
}
```

### 5.3 交互式命令
等待设备特定提示符的交互式命令：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CMGS=\"+1234567890\"\\r",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "> ",
    "timeout_ms": 5000
  }
}
```

### 5.4 配置命令
快速配置命令，可使用 none 模式：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "ATE0\\r\\n",
    "encoding": "utf8",
    "wait_policy": "none"
  }
}
```

## 6. 编码格式说明

### 6.1 UTF-8 编码
- **适用场景**: AT指令、文本协议等
- **注意事项**: 使用 `\\r`, `\\n`, `\\r\\n` 等转义序列表示控制字符
- **示例**: `"AT+CSQ\\r\\n"`

### 6.2 HEX 编码
- **适用场景**: 二进制协议、Modbus、自定义协议等
- **格式**: 空格分隔的十六进制字节，如 `"01 03 00 00"`
- **示例**: `"01 03 00 00 00 06 C5 DB"`

## 7. 错误处理

### 7.1 常见错误类型
- `SERIAL_CONNECTION_ERROR`: 串口连接错误
- `SERIAL_DATA_ERROR`: 串口数据错误
- `TIMEOUT_ERROR`: 操作超时
- `INVALID_INPUT_ERROR`: 无效输入
- `SYSTEM_ERROR`: 系统错误

### 7.2 错误处理示例
```json
{
  "success": false,
  "error_message": "接收超时，未找到停止模式: OK",
  "error_code": "TIMEOUT_ERROR"
}
```

## 8. 注意事项

1. **异步消息处理**: 交互后应检查 `pending_async_count` 字段，如不为0需调用 `read_async_messages` 处理。
2. **编码选择**: AT指令使用 `utf8` 编码，二进制协议使用 `hex` 编码。
3. **转义字符**: 在UTF-8模式下使用 `\\r\\n` 表示换行符。
4. **等待策略**:
   - `keyword`: 适合AT指令，等待特定停止模式
   - `timeout`: 适合二进制协议，等待固定时间
   - `none`: 适合配置命令，发送后不等待
   - `at_command`: 专门用于AT指令，自动处理回显
5. **连接管理**: 使用完毕后务必调用 `configure_connection` 且 `action: "close"` 关闭连接。
6. **性能考虑**: 合理设置超时时间，避免过长等待影响响应性。