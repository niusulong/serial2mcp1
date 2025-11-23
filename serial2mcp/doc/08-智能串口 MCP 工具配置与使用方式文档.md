# 智能串口 MCP 工具配置与使用方式文档

**版本号:** V1.0  
**项目代号:** Serial-Agent-MCP  
**创建日期:** 2025年11月23日

## 1. 简介

本文档描述了智能串口 MCP 工具的配置与使用方式，包括 MCP 服务器的部署、串口设备的连接管理、以及不同模式下的数据交互方式。

## 2. 环境准备

### 2.1 系统要求
- Python 3.8+
- Windows/Linux/macOS 操作系统
- 可用串口设备

### 2.2 依赖安装
```bash
pip install -r requirements.txt
```

## 3. MCP 服务器配置

### 3.1 服务器启动
```python
# 启动 MCP 服务器
python -m serial2mcp.main
```

### 3.2 配置文件
系统支持通过配置文件进行参数配置：

```json
{
  "serial": {
    "port": "/dev/ttyUSB0",
    "baudrate": 115200,
    "bytesize": 8,
    "parity": "N",
    "stopbits": 1,
    "timeout": 5.0
  },
  "mcp": {
    "host": "127.0.0.1",
    "port": 3000,
    "max_connections": 100
  },
  "driver": {
    "idle_timeout": 0.1,
    "max_buffer_size": 4096,
    "urc_buffer_size": 1000,
    "sync_timeout_default": 5.0
  }
}
```

## 4. 工具使用方式

### 4.1 连接串口设备

#### 4.1.1 列出可用串口
调用 `list_ports` 工具获取系统中所有可用的串口设备：

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

#### 4.1.2 打开串口连接
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

### 4.2 数据发送与接收

#### 4.2.1 关键字等待模式 (Wait-for-Keyword)
发送数据并等待特定关键字出现：

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

返回示例：
```json
{
  "success": true,
  "data": "+CSQ: 22,99\r\n\r\nOK\r\n",
  "is_hex": false,
  "found_stop_pattern": true,
  "pending_urc_count": 1,
  "bytes_received": 15
}
```

#### 4.2.2 纯时间等待模式 (Wait-for-Timeout)  
发送数据并等待指定时间后返回：

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

返回示例：
```json
{
  "success": true,
  "data": "01 03 0C 00 01 00 02 00 03 00 04 84 0B",
  "is_hex": true,
  "bytes_received": 13
}
```

#### 4.2.3 射后不理模式 (No-Wait)
发送数据后立即返回，不等待响应：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CMEE=1\r\n",
    "encoding": "utf8",
    "wait_policy": "none"
  }
}
```

返回示例：
```json
{
  "success": true,
  "message": "数据已发送，不等待响应"
}
```

### 4.3 URC 消息处理

#### 4.3.1 读取 URC 消息
使用 `read_urc` 工具读取后台缓冲区中的未处理消息：

```json
{
  "name": "read_urc",
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
      "raw_data": "+CMTI: \"SM\", 1",
      "is_hex": false,
      "timestamp": 1699123456.789
    }
  ],
  "count": 1
}
```

### 4.4 断开连接

#### 4.4.1 关闭串口连接
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

## 5. 典型使用场景

### 5.1 AT 指令交互
标准 AT 指令交互示例：

```json
{
  "name": "send_data",
  "arguments": {
    "payload": "AT+CSQ\r\n",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "OK",
    "timeout_ms": 5000
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
    "payload": "AT+CMGS=\"+1234567890\"\r",
    "encoding": "utf8",
    "wait_policy": "keyword",
    "stop_pattern": "> ",
    "timeout_ms": 5000
  }
}
```

## 6. 错误处理

### 6.1 常见错误类型
- `SERIAL_CONNECTION_ERROR`: 串口连接错误
- `SERIAL_DATA_ERROR`: 串口数据错误
- `TIMEOUT_ERROR`: 操作超时
- `INVALID_INPUT_ERROR`: 无效输入
- `SYSTEM_ERROR`: 系统错误

### 6.2 错误处理示例
```json
{
  "success": false,
  "error_type": "操作超时",
  "error_message": "接收超时，未找到停止模式: OK",
  "error_code": "TIMEOUT_ERROR"
}
```

## 7. 性能监控

系统提供性能指标监控功能，可以通过以下方式获取：

```python
# 获取驱动状态
driver_status = serial_driver.get_driver_status()
# 获取性能指标
metrics = serial_driver.get_performance_metrics()
```

## 8. 注意事项

1. **URC 处理**: 在每次交互后检查 `pending_urc_count` 字段，如不为0需调用 `read_urc` 处理。
2. **编码选择**: 根据协议类型选择合适的编码格式（utf8 或 hex）。
3. **超时设置**: 根据设备响应特性合理设置超时时间。
4. **缓冲区限制**: 单次接收缓冲区限制为 4KB，过大数据会被截断。
5. **连接管理**: 使用完毕后务必调用 `configure_connection` 关闭连接。