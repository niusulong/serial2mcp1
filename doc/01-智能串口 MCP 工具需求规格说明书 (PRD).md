# 智能串口 MCP 工具需求规格说明书 (PRD)

**版本号:** V1.0
**项目代号:** Serial-Agent-MCP

## 1. 项目概述

### 1.1 产品背景
传统串口助手只能进行机械的收发，无法理解协议逻辑。本项目旨在开发一个基于 Model Context Protocol (MCP) 的串口工具，作为大语言模型（LLM）的物理接口。

### 1.2 核心设计理念
- **无状态执行器：** 工具本体不硬编码任何 AT 指令集或特定协议解析逻辑。
- **动态策略：** 由 LLM 在运行时决定发送什么、怎么接收、何时超时。
- **全类型支持：** 兼顾 AT 指令（文本行）与 纯数据传输（HEX/二进制）。
- **智能分流：** 自动区分同步响应和异步URC（未请求消息）。

## 2. 核心功能需求 (Functional Requirements)

### 2.1 串口连接管理 (Connection Manager)
**F1-1 参数配置：** 支持配置 端口号 (Port)、波特率 (Baudrate)、数据位、停止位、校验位。
**F1-2 热插拔检测：** (可选) 自动检测可用串口列表的变化。
**F1-3 状态反馈：** 向 LLM 提供当前连接状态（Connected/Disconnected/Occupied）。

### 2.2 智能收发接口 (Smart Transceiver)
这是工具最核心的功能，必须实现一个"万能发送函数"，支持以下四种模式：

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

**F2-4 AT命令模式 (AT Command Mode)：**
- 专门处理AT命令的回显和响应。
- 自动处理命令回显（如发送"AT+CSQ"后会收到回显"AT+CSQ"）。
- 适用场景：标准AT指令交互。

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
**返回：** 设备路径列表及描述（如 [{"port": "/dev/ttyUSB0", "description": "CP2102", "hardware_id": "USB VID:PID..."}]）。

### 3.2 configure_connection
**描述：** 打开或关闭串口，配置参数。
**参数：** 
- port: 串口设备路径
- baudrate: 波特率
- timeout: 超时时间
- action: 操作类型 (open/close)

### 3.3 send_data (核心)
**描述：** 发送数据并根据策略获取响应。
**参数：**
- payload: 发送内容
- encoding: 编码格式 (utf8/hex)
- wait_policy: 等待策略 (keyword/timeout/none/at_command)
- stop_pattern: 仅在 keyword 模式下有效（如 'OK'）
- timeout_ms: 等待超时时间（毫秒）

### 3.4 read_urc
**描述：** 读取后台缓冲区中积累的未处理消息（URC）。
**返回：** URC消息列表

## 4. 技术实现栈

### 4.1 MCP 实现
- **MCP 库:** 使用官方 `mcp` 库实现 MCP 协议
- **协议:** JSON-RPC over stdio
- **并发:** asyncio 支持

### 4.2 串口通信
- **库:** pyserial
- **并发模型:** 单生产者-双消费者模型
- **线程安全:** 使用 threading.Event 和 queue.Queue

### 4.3 架构层次
- **接口层:** main.py, server.py (MCP协议实现)
- **适配层:** adapter/ (参数转换、异常处理)
- **驱动层:** driver/ (串口驱动、数据处理)
- **工具层:** utils/ (日志、配置、异常定义)