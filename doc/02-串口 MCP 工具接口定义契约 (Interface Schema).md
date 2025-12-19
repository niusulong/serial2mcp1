# 串口 MCP 工具接口定义契约 (Interface Schema)

**版本:** V1.3
**用途:** 定义大模型调用串口工具的标准格式。

这份文档采用了标准 JSON Schema 格式（兼容 OpenAI Function Calling 和 MCP Protocol）。你可以直接将此内容复制给大模型（如 ChatGPT、Claude），并在 System Prompt 中告诉它："你拥有以下工具，请根据用户的需求选择合适的工具进行调用。"

## 1. 工具列表概览

| 工具名称 (name) | 简述 (description) | 核心参数 |
|----------------|-------------------|---------|
| list_ports | 列出当前系统所有可用的串口设备。 | 无 |
| configure_connection | 打开或关闭串口，配置参数。 | action, port, baudrate |
| send_data | 核心函数。发送数据并根据策略获取响应。 | payload, wait_policy, stop_pattern |
| read_async_messages | 读取后台缓冲区中积累的异步消息。 | 无 |

## 2. 详细 JSON Schema 定义

### Tool 1: list_ports

```json
{
  "name": "list_ports",
  "description": "列出当前系统所有可用的串口设备。",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

### Tool 2: configure_connection

```json
{
  "name": "configure_connection",
  "description": "打开或关闭串口，配置参数。",
  "inputSchema": {
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
}
```

### Tool 3: send_data (核心)

这是体现**"AI 决策接收逻辑"**的核心工具。

```json
{
  "name": "send_data",
  "description": "发送数据并根据策略获取响应。",
  "inputSchema": {
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
        "enum": ["keyword", "timeout", "none"],
        "description": "等待策略：'keyword'关键字等待模式，'timeout'纯时间等待模式，'none'射后不理模式"
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
}
```

### Tool 4: read_async_messages

```json
{
  "name": "read_async_messages",
  "description": "读取后台缓冲区中积累的异步消息。",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

## 3. 接口返回结构 (Return Schema)

工具执行后，将以 JSON 格式返回结果给大模型。

### 成功通用结构:

```json
{
  "success": true,
  "data": "响应内容...",
  "raw_data": "b'\\x01\\x03...'",  // 原始字节数据
  "is_hex": false,
  "found_stop_pattern": true,  // 仅在 keyword 模式下有效
  "bytes_received": 15,  // 接收到的字节数
  "pending_async_count": 2,  // 告知模型后台还有异步消息没读
  "message": "额外信息（可选）"
}
```

### 失败通用结构:

```json
{
  "success": false,
  "error_message": "Serial port not open"
}
```
