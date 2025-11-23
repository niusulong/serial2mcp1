# 串口 MCP 工具接口定义契约 (Interface Schema)

**版本:** V1.0  
**用途:** 定义大模型调用串口工具的标准格式。

这份文档采用了标准 JSON Schema 格式（兼容 OpenAI Function Calling 和 MCP Protocol）。你可以直接将此内容复制给大模型（如 ChatGPT、Claude），并在 System Prompt 中告诉它："你拥有以下工具，请根据用户的需求选择合适的工具进行调用。"

如果不确定模型能否理解，可以看文档末尾的**"自测验证部分"**。

## 1. 工具列表概览

| 工具名称 (name) | 简述 (description) | 核心参数 |
|----------------|-------------------|---------|
| list_ports | 列出当前系统所有可用的串口设备。 | 无 |
| configure_connection | 打开或关闭串口，配置参数。 | action, port, baudrate |
| send_data | 核心函数。发送数据并根据策略获取响应。 | payload, wait_policy, stop_pattern |
| read_urc | 读取后台缓冲区中积累的未处理消息（URC）。 | 无 |

## 2. 详细 JSON Schema 定义

### Tool 1: list_ports

```json
{
  "name": "list_ports",
  "description": "列出当前系统所有可用的串口设备。",
  "parameters": {
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
  "parameters": {
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
  "parameters": {
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
}
```

### Tool 4: read_urc

```json
{
  "name": "read_urc",
  "description": "读取后台缓冲区中积累的未处理消息（URC）。",
  "parameters": {
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
  "is_hex": false,
  "found_stop_pattern": true,  // 仅在 keyword 模式下有效
  "bytes_received": 15,  // 接收到的字节数
  "pending_urc_count": 2  // 告知模型后台还有URC没读
}
```

### 失败通用结构:

```json
{
  "success": false,
  "error_message": "Serial port not open"
}
```

## 4. 验证测试 (Self-Check)

为了验证这套 Schema 是否合理，你可以把下面的测试提示词 (Prompt) 发给 ChatGPT，看它生成的 JSON 是否符合你的预期。

### 验证 Prompt:

"你是一个串口助手专家。我定义了以下工具（此处粘贴上面的 JSON Schema）。
请帮我完成以下任务，输出对应的函数调用 JSON：

1. 连接 COM3，波特率 9600。
2. 发送查询信号质量的 AT 指令 (AT+CSQ)，我知道它通常以 OK 结尾，最多等 3 秒。
3. 发送一个 Modbus 读取指令 (Hex: 01 03 00 00 00 01)，我不确定设备什么时候回完，通过等待 500ms 来收集所有返回数据。
4. 刚刚好像来了条短信，帮我看看后台有没有收到什么新消息。"

### 预期的大模型输出 (Reference Output):

#### 1. 连接

```json
{
  "name": "configure_connection",
  "arguments": {
    "action": "open",
    "port": "COM3",
    "baudrate": 9600
  }
}
```

#### 2. 查询信号 (Wait for OK)

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CSQ\r\n",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "OK",
    "timeout_ms": 3000
  }
}
```

#### 3. Hex 透传 (Wait for Timeout)

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "01 03 00 00 00 01",
    "encoding": "hex",
    "wait_policy": "timeout",
    "timeout_ms": 500
  }
}
```

#### 4. 读 URC

```json
{
  "name": "read_urc",
  "arguments": {}
}
```

如果模型输出了类似的结构，说明这份接口契约定义成功。