# MCP串口工具使用示例

## 1. 基础操作示例

### 1.1 列出可用串口
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
    },
    {
      "port": "COM3",
      "description": "Prolific USB-to-Serial Comm Port",
      "hardware_id": "USB\\VID_067B&PID_2303\\6&12345678&0&2"
    }
  ]
}
```

### 1.2 打开串口连接
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

### 1.3 关闭串口连接
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

## 2. 数据发送与接收示例

该工具支持四种等待策略，可根据不同场景选择：

### 2.1 AT指令交互（推荐使用keyword模式）
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CGMI\\r\\n",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "OK",
    "timeout_ms": 3000
  }
}
```

**说明**: keyword模式用于等待AT指令响应结束标识，通常以"OK"结尾。

返回示例：
```json
{
  "success": true,
  "data": "AT+CGMI\\r\\n\\r\\nSIMCOM INCORPORATED\\r\\n\\r\\nOK\\r\\n",
  "raw_data": "b'AT+CGMI\\r\\n\\r\\nSIMCOM INCORPORATED\\r\\n\\r\\nOK\\r\\n'",
  "is_hex": false,
  "bytes_received": 34,
  "pending_async_count": 0
}
```

**注意**: AT指令通常需要以`\\r\\n`结尾才能正确执行。

### 2.2 AT指令交互（使用keyword模式）
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CGMI\\r\\n",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "OK",
    "timeout_ms": 3000
  }
}
```

**说明**: keyword模式将持续接收数据直到找到指定停止模式或超时。

返回示例：
```json
{
  "success": true,
  "data": "SIMCOM INCORPORATED\\r\\n\\r\\nOK",
  "raw_data": "b'SIMCOM INCORPORATED\\r\\n\\r\\nOK'",
  "is_hex": false,
  "found_stop_pattern": true,
  "bytes_received": 26,
  "pending_async_count": 0
}
```

### 2.3 AT指令交互（使用timeout模式）
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CGMI\\r\\n",
    "encoding": "utf8",
    "wait_policy": "timeout",
    "timeout_ms": 3000
  }
}
```

**说明**: timeout模式将在指定时间内收集所有数据，无论是否包含特定模式。

返回示例：
```json
{
  "success": true,
  "data": "AT+CGMI\\r\\n\\r\\nSIMCOM INCORPORATED\\r\\n\\r\\nOK\\r\\n",
  "raw_data": "b'AT+CGMI\\r\\n\\r\\nSIMCOM INCORPORATED\\r\\n\\r\\nOK\\r\\n'",
  "is_hex": false,
  "bytes_received": 34,
  "pending_async_count": 0
}
```

### 2.4 查询信号强度
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

### 2.5 查询网络注册状态
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CREG?\\r\\n",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "OK",
    "timeout_ms": 3000
  }
}
```

## 3. 二进制协议交互示例

### 3.1 发送Modbus请求（使用timeout模式）
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

### 3.2 发送自定义二进制数据
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AA BB CC DD EE FF",
    "encoding": "hex",
    "wait_policy": "timeout",
    "timeout_ms": 500
  }
}
```

## 4. 交互式命令示例

### 4.1 发送短信（等待>提示符）
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CMGS=\"+123456789\"\\r\\n",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "> ",
    "timeout_ms": 10000
  }
}
```

**说明**: keyword模式将在超时时间内收集所有数据，然后检查是否包含"> "提示符。

在收到"> "提示符后，再发送短信内容：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "Hello World\x1A",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "OK",
    "timeout_ms": 20000
  }
}
```

## 5. 配置操作示例

### 5.1 射后不理模式发送配置命令
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

返回示例：
```json
{
  "success": true,
  "message": "数据已发送，不等待响应",
  "pending_async_count": 0
}
```

**说明**: none模式发送后立即返回，响应将在后台积累为异步消息。

## 6. 异步消息处理示例

### 6.1 检查待处理异步消息
每次工具调用的返回都包含`pending_async_count`字段。如果有待处理消息，则调用`read_async_messages`：

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

**重要提示**: 每次调用`read_async_messages`会清除已读取的异步消息。

## 7. 错误处理示例

### 7.1 命令超时
如果工具返回超时，可以尝试使用timeout模式查看设备真实响应：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CSQ\\r\\n",
    "encoding": "utf8",
    "wait_policy": "timeout",
    "timeout_ms": 5000
  }
}
```

### 7.2 十六进制数据格式错误时
确保十六进制数据格式正确（以空格分隔的两字符十六进制对）：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "01 02 03 04 05 06",
    "encoding": "hex",
    "wait_policy": "timeout",
    "timeout_ms": 1000
  }
}
```

### 7.3 常见错误处理
```json
{
  "success": false,
  "error_message": "接收超时，未找到停止模式: OK",
  "error_code": "TIMEOUT_ERROR"
}
```

## 8. 完整交互流程示例

### 8.1 连接设备并获取基本信息
1. 列出可用端口：
```json
{
  "name": "list_ports",
  "arguments": {}
}
```

2. 连接设备（选择合适的端口和波特率）：
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

3. 查询设备信息：
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "ATI\\r\\n",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "OK",
    "timeout_ms": 3000
  }
}
```

4. 断开连接：
```json
{
  "name": "configure_connection",
  "arguments": {
    "action": "close"
  }
}
```

## 9. 性能监控示例

每次交互后可以检查返回结果中的性能指标，如`bytes_received`、`pending_async_count`等字段，以评估数据交互情况。

## 10. 特殊场景处理

### 10.1 设备重启后等待
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CFUN=1,1\\r\\n",  // 重启设备
    "encoding": "utf8",
    "wait_policy": "none"
  }
}
```

稍后再检查设备是否重启完成：
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT\\r\\n",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "OK",
    "timeout_ms": 10000  // 设置较长超时
  }
}
```

### 10.2 长时间运行监控
定期调用`read_async_messages`处理积累的消息：
```json
{
  "name": "read_async_messages",
  "arguments": {}
}
```

## 11. 策略选择指南

### 11.1 AT指令处理
- **keyword**: 推荐用于标准AT指令，等待响应结束标识(如OK)
- **keyword**: 适用于需要特定关键词确认的场景
- **例**: AT+CSQ, AT+CGMI 等查询指令

### 11.2 二进制协议
- **timeout**: 适用于Modbus、自定义二进制协议等
- **说明**: 在固定时间内收集所有数据
- **例**: "01 03 00 00 00 06 C5 DB"

### 11.3 配置命令
- **none**: 适用于设置命令，无需等待响应
- **例**: ATE0, AT+CMEE=1 等配置指令

### 11.4 交互式命令
- **keyword**: 等待特定提示符
- **例**: AT+CMGS 等需要交互的命令

这些示例涵盖了MCP串口工具的主要使用场景，可以帮助大模型理解如何有效地与串口设备进行交互。