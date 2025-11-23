# MCP串口工具使用示例

## 1. 基础连接操作

### 1.1 列出可用串口设备
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

### 2.1 查询设备制造商信息
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CGMI",
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 3000
  }
}
```

### 2.2 查询设备型号
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CGMM",
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 3000
  }
}
```

### 2.3 查询固件版本
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CGMR",
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 3000
  }
}
```

### 2.4 查询IMEI
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CGSN",
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 3000
  }
}
```

### 2.5 查询信号质量
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CSQ",
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 3000
  }
}
```

### 2.6 配置串口回显
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "ATE1",
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 3000
  }
}
```

## 3. 网络状态查询

### 3.1 查询网络注册状态
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CREG?",
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 3000
  }
}
```

### 3.2 查询网络运营商信息
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+COPS?",
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 3000
  }
}
```

### 3.3 查询网络技术
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CNCFG?",
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 3000
  }
}
```

## 4. 数据协议交互

### 4.1 发送十六进制数据并等待响应
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

### 4.2 发送Modbus读取请求
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "01 03 00 00 00 03 C4 0B",
    "encoding": "hex",
    "wait_policy": "timeout",
    "timeout_ms": 1000
  }
}
```

### 4.3 发送配置命令（射后不理）
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "CONFIG:SET_PARA=123",
    "encoding": "utf8",
    "wait_policy": "none"
  }
}
```

## 5. 等待特定响应

### 5.1 等待特定关键字
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CMGL=\"REC UNREAD\"",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "+CMGL:",
    "timeout_ms": 10000
  }
}
```

### 5.2 等待多个可能的响应
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CFUN=1",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "OK",
    "timeout_ms": 5000
  }
}
```

## 6. URC消息处理

### 6.1 检查待处理URC消息
每次交互后，检查返回结果中的`pending_urc_count`字段：
- 如果`pending_urc_count > 0`，立即调用`read_urc`工具

### 6.2 读取URC消息
```json
{
  "name": "read_urc",
  "arguments": {}
}
```

## 7. 高级使用场景

### 7.1 交互式命令 - 发送短信
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CMGS=\"+1234567890\"",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "> ",  // 等待"> "提示符
    "timeout_ms": 5000
  }
}
```
在收到"> "提示符后，再发送短信内容并以Ctrl+Z结尾：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "Hello world\x1A",  // \x1A是Ctrl+Z
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "OK",
    "timeout_ms": 20000
  }
}
```

### 7.2 交互式命令 - PPP拨号
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "ATDT*99#",  // 拨号命令
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "CONNECT",
    "timeout_ms": 30000
  }
}
```

### 7.3 长时间数据监听
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT^TRACECTRL=1,\"ON\"",  // 开启调试追踪
    "encoding": "utf8",
    "wait_policy": "at_command",
    "timeout_ms": 5000
  }
}
```

稍后可以定期调用`read_urc`获取追踪数据。

## 8. 错误处理

### 8.1 命令超时处理
如果工具返回超时错误，可以尝试：
1. 检查设备是否响应
2. 验证波特率设置是否正确
3. 尝试使用`timeout`策略而非`keyword`策略，查看设备实际响应

### 8.2 无效响应处理
如果收到意外响应，分析可能的原因：
1. 命令格式错误
2. 设备不支持此命令
3. 参数超出范围
4. 设备忙或未就绪

## 9. 性能优化建议

1. **使用合适的等待策略**：AT命令优先使用`at_command`模式
2. **合理设置超时时间**：根据命令预期响应时间设置
3. **批量操作**：对多个设备连续操作时，保持连接状态
4. **URC监控**：定期检查和处理URC，避免缓冲区溢出

## 10. 调试技巧

### 10.1 调试AT命令
如果AT命令无响应，尝试：
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "ATE0V1",  // 关闭回显，开启响应码
    "encoding": "utf8",
    "wait_policy": "timeout",
    "timeout_ms": 1000
  }
}
```

### 10.2 调试二进制协议
对二进制协议，使用`timeout`模式查看原始字节流：
```json
{
  "name": "send_data",
  "arguments": {
    "payload": "十六进制数据",
    "encoding": "hex",
    "wait_policy": "timeout",
    "timeout_ms": 5000
  }
}
```