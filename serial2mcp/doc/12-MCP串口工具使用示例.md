# MCP串口工具使用示例

## 1. 基础操作示例

### 1.1 列出可用串口
```json
{
  "name": "list_ports",
  "arguments": {}
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

### 1.3 关闭串口连接
```json
{
  "name": "configure_connection",
  "arguments": {
    "action": "close"
  }
}
```

## 2. AT指令交互示例

### 2.1 查询设备制造商信息（推荐使用at_command模式）
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

**注意**: AT指令通常需要以\\r\\n结尾才能正确执行。

### 2.2 查询设备制造商信息（使用keyword模式）
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

### 2.3 查询信号强度
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

### 2.4 查询网络注册状态
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

## 6. URC处理示例

### 6.1 检查待处理URC消息
每次工具调用的返回都包含`pending_urc_count`字段。如果有待处理消息，则：

```json
{
  "name": "read_urc",
  "arguments": {}
}
```

## 7. 错误处理示例

### 7.1 命令超时
如果工具返回超时，可以尝试使用timeout模式查看设备真实响应：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CSQ",
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
    "encoding": "hex",  // 明确指定为十六进制
    "wait_policy": "timeout",
    "timeout_ms": 1000
  }
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

## 9. 性能监控示例

每次交互后可以检查返回结果中的性能指标，如`bytes_received`、`pending_urc_count`等字段，以评估数据交互情况。

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
    "wait_policy": "at_command",
    "timeout_ms": 10000  // 设置较长超时
  }
}
```

这些示例涵盖了MCP串口工具的主要使用场景，可以帮助大模型理解如何有效地与串口设备进行交互。