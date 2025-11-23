# 智能串口 MCP 工具需求规格说明书 (PRD)

**版本号:** V0.1 (Draft)  
**项目代号:** Serial-Agent-MCP

## 1. 项目概述

### 1.1 产品背景
传统串口助手只能进行机械的收发，无法理解协议逻辑。本项目旨在开发一个基于 Model Context Protocol (MCP) 的串口工具，作为大语言模型（LLM）的物理接口。

### 1.2 核心设计理念
- **无状态执行器：** 工具本体不硬编码任何 AT 指令集或特定协议解析逻辑。
- **动态策略：** 由 LLM 在运行时决定发送什么、怎么接收、何时超时。
- **全类型支持：** 兼顾 AT 指令（文本行）与 纯数据传输（HEX/二进制）。

## 2. 核心功能需求 (Functional Requirements)

### 2.1 串口连接管理 (Connection Manager)
**F1-1 参数配置：** 支持配置 端口号 (Port)、波特率 (Baudrate)、数据位、停止位、校验位。  
**F1-2 热插拔检测：** (可选) 自动检测可用串口列表的变化。  
**F1-3 状态反馈：** 向 LLM 提供当前连接状态（Connected/Disconnected/Occupied）。

### 2.2 智能收发接口 (Smart Transceiver)
这是工具最核心的功能，必须实现一个"万能发送函数"，支持以下三种模式：

**F2-1 关键字等待模式 (Wait-for-Keyword)：**
- 发送数据后，持续读取，直到接收流中出现指定字符串（如 OK, ERROR, >）。
- 支持超时设置，若超时未收到关键字则返回当前已收到的所有数据并标记超时。

**F2-2 纯时间等待模式 (Wait-for-Timeout)：**
- 发送数据后，不判断内容，强制等待指定时长（如 500ms）。
- 将该时间段内收到的所有数据打包返回。
- 适用场景：未知协议、无响应协议、乱码分析。

**F2-3 射后不理模式 (No-Wait/Fire-and-Forget)：**
- 发送数据后立即返回"发送成功"，不读取任何响应。
- 后续产生的响应数据归入"被动接收流（URC）"处理。

### 2.3 数据流处理与 URC (Data Stream Processor)
由于串口是字节流，工具需负责将流切分为"包"：

**F3-1 空闲分包 (Idle-Slicing)：**
- 引入 Idle Timer (默认约 50-100ms)。当串口有数据到达时重置计时器，计时器超时则认为一包数据结束。

**F3-2 编码自动适配：**
- 尝试使用 UTF-8 解码接收到的数据。
- 如果解码失败（包含不可见字符），自动转为 HEX 字符串（如 0A 0D FF）返回，并在元数据中标记 format: hex。

**F3-3 异步消息缓冲 (URC Buffer)：**
- 当 LLM 未处于"等待响应"状态时，收到的所有数据（如短信上报、心跳包）存入内部队列。
- 提供接口供 LLM 轮询或在下一次交互时附带推送。

### 2.4 本地数据存储 (Local Storage)
**F4-1 交互日志 (Raw Logs)：**
- 以文件形式记录最原始的 Tx/Rx 字节流和时间戳，作为"真理来源"供排查。

## 3. MCP 接口定义 (Interface Definition)

工具需通过 MCP 协议暴露以下 Tool 给大模型：

### 3.1 list_ports
**描述：** 列出当前系统所有可用的串口设备。  
**返回：** 设备路径列表及描述（如 ["/dev/ttyUSB0 - CP2102"]）。

### 3.2 configure_connection
**描述：** 打开或关闭串口，配置参数。  
**参数：** port, baudrate, timeout, action (open/close)。

### 3.3 send_data (核心)
**描述：** 发送数据并根据策略获取响应。  
**参数：**
- payload (string): 发送内容。
- encoding (enum): "utf8" | "hex"。
- wait_policy (enum): "keyword" | "timeout" | "none"。
- stop_pattern (string): 仅在 keyword 模式下有效（如 "OK"）。
- timeout_ms (int): 等待超时时间。

**返回：**
```json
{
  "success": true,
  "data": "响应内容...",
  "is_hex": false,
  "found_keyword": true,
  "pending_urc_count": 2  // 告知模型后台还有URC没读
}
```

### 3.4 read_urc
**描述：** 读取后台缓冲区中积累的未处理消息（URC）。  
**返回：** 数据包列表。

## 4. 非功能需求 (Non-Functional Requirements)

### 4.1 响应延迟
工具自身的处理开销（不含串口IO时间）应 < 10ms，保证透传的实时性。

### 4.2 鲁棒性与熔断
**数据熔断：** 单次接收缓冲区限制（例如 4KB）。如果设备发送大量数据，工具必须截断并返回"Output Truncated"，防止 Token 消耗过大或造成 LLM 幻觉。  
**容错：** 发送 HEX 格式错误的字符串时，工具应返回清晰的 Error Message 而不是崩溃。

### 4.3 平台兼容性
优先支持 Windows/Linux (pyserial 跨平台)，考虑到嵌入式开发环境的多样性。

## 5. 系统边界 (Boundaries)

### 5.1 工具 不做 什么
- 不解析语义：工具不知道 +CSQ: 20,99 是信号好的意思，只管把它当字符串返回。
- 不判断业务结果：工具不判定"测试通过"或"失败"，只返回"收到了什么"。
- 不自动重试：除非 LLM 发起第二次调用，否则工具层不进行自动重传。

### 5.2 大模型 做 什么
- 决定发什么：构建 AT 指令或二进制包。
- 决定怎么收：根据指令类型选择等待 OK 还是等待 500ms。
- 分析结果：解析返回的数据，判断是否符合预期。
- 处理 URC：根据 read_urc 的内容，分析设备是否出现异常或状态变更。
