# MCP串口工具使用示例

## 1. 基础操作示例

### 1.1 发现串口设备
```json
{
  "name": "list_ports",
  "arguments": {}
}
```

### 1.2 建立串口连接
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

## 2. AT指令交互示例

### 2.1 查询设备制造商信息
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

**注意**: AT指令通常需要以\\r\\n结尾才能正确执行。响应将包含完整的回显和设备响应（例如对于"AT\\r\\n"命令，可能返回"AT\\r\\n\\r\\nOK\\r\\n"）。使用keyword模式可等待特定响应如"OK"。

### 2.2 查询信号强度
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
**注意**: at_command模式将返回超时时间内接收到的所有数据，包括回显和响应。

### 2.3 使用关键字模式查询信号强度
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
**注意**: keyword模式将持续接收数据直到找到"OK"响应或超时。

### 2.3 查询网络注册状态
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CREG?\\r\\n",
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 3000
  }
}
```

## 3. 交互式命令示例

### 3.1 发送短信
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CMGS=\"+1234567890\"\\r\\n",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "> ",
    "timeout_ms": 10000
  }
}
```

收到"> "提示符后，发送短信内容：
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "Hello World\x1A",  // Ctrl+Z结束短信
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 20000
  }
}
```

## 4. 二进制协议示例

### 4.1 Modbus协议交互
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

## 5. 配置操作示例

### 5.1 设置回显关闭
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

## 6. URC消息处理

### 6.1 检查并读取URC消息
当`pending_urc_count > 0`时：
```json
{
  "name": "read_urc",
  "arguments": {}
}
```

## 7. 错误处理示例

### 7.1 超时检查
如果AT指令超时，使用timeout策略查看设备实际响应：
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CSQ\\r\\n",
    "encoding": "utf8",
    "wait_policy": "timeout",
    "timeout_ms": 3000
  }
}
```

## 8. 完整交互流程示例

### 8.1 设备连接与信息获取
1. 发现设备：
```json
{
  "name": "list_ports",
  "arguments": {}
}
```

2. 连接设备：
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

3. 获取设备信息：
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "ATI\\r\\n",
    "encoding": "utf8",
    "wait_policy": "at_command",
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

这些示例展示了MCP串口工具在各种常见场景下的使用方式，帮助AI理解和应用正确的交互策略。