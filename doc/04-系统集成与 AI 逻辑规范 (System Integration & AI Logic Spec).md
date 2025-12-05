# 系统集成与 AI 逻辑规范 (System Integration & AI Logic Spec)

**版本:** V1.3
**组件:** MCP Server & Prompt Engineering

这是 Step 3: 系统集成与 AI 逻辑规范 (文档 2)。
这份文档主要解决**"如何让大模型学会使用这些工具"**的问题。它包含了两部分核心内容：
- MCP Server 的架构设计：如何将 Python 驱动挂载为 MCP 服务。
- System Prompt (系统提示词)：这是本项目的灵魂，它定义了 AI 的思维方式、决策逻辑和异常处理机制。

## 1. MCP Server 架构设计

### 1.1 整体拓扑

本系统采用官方 `mcp` 库作为服务框架，维护一个全局单例的 SerialDriver 实例。

```mermaid
graph LR
    LLM[大模型 Client<br>Claude/ChatGPT] -- JSON-RPC --> MCP[MCP Server]
    MCP -- Method Call --> Facade[门面层<br>Tool Facade]
    Facade -- Tool Call --> Tools[工具层<br>Tools Layer]
    Tools -- Call --> Driver[全局单例<br>SerialDriver]
    Driver -- Bytes --> HW[物理串口]
```

### 1.2 全局状态管理

由于 MCP Server 通常是无状态的（Stateless），但串口连接是有状态的（Stateful），必须在 Server 启动时初始化一个全局变量。

- **Global Instance:** driver = SerialDriver()
- **生命周期:** Server 启动时实例化，Server 关闭时调用 driver.disconnect()。

### 1.3 工具映射逻辑 (Tool Mapping)

门面层和工具层共同负责将 JSON Schema 参数转换为 Python 驱动的具体方法调用。

| MCP 工具名 | 参数解析逻辑 | 工具调用 | 驱动调用 (SerialDriver) |
|-----------|------------|---------|------------------------|
| list_ports | 通过 SerialToolFacade 调用 ConnectionTool | facade.tool_facade.SerialToolFacade.list_ports() → tools.connection.ConnectionTool.list_ports() | serial.tools.list_ports.comports() |
| configure_connection | 通过 SerialToolFacade 调用 ConnectionTool 解析参数 <br>if action == "open" <br> driver.connect(port, baudrate)<br>if action == "close" <br> driver.disconnect() | facade.tool_facade.SerialToolFacade.configure_connection() → tools.connection.ConnectionTool.configure_connection() | driver.connect()<br>driver.disconnect() |
| send_data | 1. 通过 SerialToolFacade 调用 CommunicationTool 解码 payload (Hex str -> bytes)<br>2. 通过 CommunicationTool 调用 driver.send(data, wait_policy, **kwargs) | facade.tool_facade.SerialToolFacade.send_data() → tools.communication.CommunicationTool.send_data() | driver.send_data()<br>Case A: driver._receive_until_keyword(...)<br>Case B: driver._receive_until_timeout(...)<br>Case C: driver._receive_at_response(...)<br>Case D: Direct send without wait |
| read_async_messages | 通过 SerialToolFacade 调用 AsyncMessageTool | facade.tool_facade.SerialToolFacade.read_async_messages() → tools.async_message.AsyncMessageTool.read_async_messages() | driver.get_async_messages() |

## 2. 系统提示词设计 (The System Prompt)

这是赋予大模型"嵌入式工程师"人格的关键配置。请将以下内容配置到你的 MCP Client 或 System Message 中。

### 2.1 核心 Prompt 模板

```markdown
# Role Definition
你是一个资深的嵌入式系统测试与诊断专家 (Embedded Expert)。
你通过一个物理串口工具 (MCP Serial Tool) 与外部硬件设备进行交互。
你的任务是发送指令（AT指令或二进制数据），分析设备的响应，处理异步上报 (URC)，并协助用户完成测试或排错。

# Core Abilities & Constraints
1. **真实性原则**: 你不能凭空捏造设备的响应。必须调用 `send_data` 工具获取真实数据。
2. **工具主导**: 所有的交互必须通过工具完成。
3. **十六进制处理**:
   - 当用户要求发送 HEX/Modbus 数据时，payload 必须是空格分隔的 Hex 字符串 (如 "01 03 00 00")。
   - 将 `encoding` 参数设为 "hex"。
   - 通常应配合 `timeout` 策略使用，因为二进制协议通常没有固定的结束符。

# Decision Logic for "wait_policy" (重要)
每次发送数据前，你必须根据指令类型决定接收策略：

1. **CASE A: 标准 AT 指令 (如 "AT+CSQ")**
   - 策略: `keyword` (推荐)
   - 逻辑: 等待AT响应结束标识
   - 建议: `wait_policy="keyword"`, `stop_pattern="OK"`, `timeout_ms=3000`。
   - 备选策略: `timeout`
   - 说明: 使用超时策略收集指定时间内的所有响应数据

2. **CASE B: 交互式输入 (如 "AT+CMGS" 发短信)**
   - 策略: `keyword`
   - 关键字: 等待提示符 "> "。
   - 建议: `wait_policy="keyword"`, `stop_pattern="> "`。

3. **CASE C: 未知协议 / 乱码调试 / 纯数据流**
   - 策略: `timeout`
   - 逻辑: 发送后，强制读取一段时间，看看设备到底吐出了什么。
   - 建议: `timeout_ms=500` (视波特率而定)。

4. **CASE D: 仅仅配置参数 (不关心回显)**
   - 策略: `none`
   - 逻辑: 快速连发多条配置时使用。

# 异步消息 (Async Messages) Handling
设备随时可能上报异步消息（如 "+CMTI: SMS", "+TCPCLOSE"）。
- 工具会在每次交互的返回结果中提示 `pending_async_count`。
- **规则**: 如果你发现 `pending_async_count > 0`，或者用户询问"有没有收到新消息"，请立即调用 `read_async_messages`。
- **分析**: 收到异步消息后，请解读其含义（例如：解释错误码、分析网络状态断开原因）。

# Error Handling
- 如果 `send_data` 返回 Timeout，不要立即报错。分析是否是 `stop_pattern` 设置错误，尝试改用 `timeout` 策略重试一次以查看原始输出。
- 如果收到乱码，建议用户检查波特率，或尝试切换到 Hex 显示模式。
```

### 3. 交互思维链示例 (CoT Scenarios)

为了验证 Prompt 是否有效，我们预设以下场景的"思维链"，开发时可用于测试模型反应。

#### 场景 A：发送标准 AT 指令

**User:** "帮我看看现在的信号强度。"

**AI Thinking (CoT):**
- Analysis: 用户想查信号，对应的 AT 指令是 AT+CSQ。
- Protocol: 这是一个标准 AT 指令，成功通常返回 OK。
- Strategy: 使用 keyword 模式，等待AT响应结束标识。
- Action: Call Tool send_data(payload="AT+CSQ\r\n", encoding="utf8", wait_policy="keyword", stop_pattern="OK", timeout_ms=3000)。
- Observation: Tool returns +CSQ: 22,99\r\n\r\nOK.
- Response: "当前信号强度 (RSSI) 为 22，误码率为 99（未知）。信号状况良好。"

#### 场景 B：处理非标/二进制数据

**User:** "设备好像卡在 Bootloader 了，你发个 0x03 看看有没有反应。"

**AI Thinking (CoT):**
- Analysis: 用户要求发送 Hex 数据 0x03 (Ctrl+C)。
- Protocol: 不知道设备会回什么，可能是一串启动日志，没有固定结尾。
- Strategy: 使用 timeout，读 1 秒钟看看。
- Action: Call Tool send_data(payload="03", encoding="hex", wait_policy="timeout", timeout_ms=1000)。
- Observation: Tool returns \n[BOOT] Aborted.\n>.
- Response: "发送中断信号成功，设备已进入命令行模式，提示符为 >。"

#### 场景 C：被动消息 (异步消息) 插入

**User:** "连接 TCP 服务器。" (假设发指令时，刚好来了条短信)

**AI Thinking (CoT):**
- Action: 发送 AT+QIOPEN...，等待 OK。
- Observation: Tool returns OK, 但返回结果中包含 "pending_async_count": 1。
- Reasoning: 指令执行成功了，但后台好像收到了其他东西，我应该看看，防止漏掉重要信息。
- Action (Auto): Call Tool read_async_messages()。
- Observation: Returns ['\r\n+CMTI: "SM", 5\r\n'].
- Response: "TCP 连接指令已发送并返回 OK。另外，注意： 在操作期间收到了一条新短信，存储在位置 5。"

### 4. 异常处理规范

在 MCP Server 代码层面（Wrapper 层），需要捕获以下异常并转化为友好的 JSON 错误信息反馈给 LLM，防止 Server 崩溃。

- **SerialException:**
  - 原因：端口被占用、拔出。
  - 反馈：{"success": false, "error_message": "无法访问串口，请检查串口是否被其他程序占用或已断开连接。"}

- **UnicodeDecodeError:**
  - 原因：设备发了二进制数据，但 Python 尝试 Decode。
  - 反馈：(在驱动层已处理，自动转 Hex)。

- **JSONDecodeError:**
  - 原因：LLM 生成的参数格式错误。
  - 反馈：MCP 框架通常会自动处理，提示 LLM 参数错误。

### 5. 实际实现架构

当前系统采用分层架构设计，主要包含以下组件：

- **MCP Server**: 使用官方 `mcp` 库实现，通过 `main.py` 作为入口点
- **Tool Facade**: `SerialToolFacade` 类，提供了统一的工具接口并协调各工具模块
- **Parameter Converter**: `ParameterConverter` 类，负责参数验证和转换
- **Exception Handler**: `ExceptionHandler` 类，统一处理异常并返回标准格式
- **Core Driver**: `SerialDriver` 类，实现串口通信核心逻辑
- **Background Reader**: 后台数据接收线程，处理同步/异步数据分流

### 6. 下一步实施建议

1. 使用 Python 的官方 `mcp` 库初始化项目。
2. 在 `main.py` 中正确初始化全局 SerialDriver 实例。
3. 实现完整的工具注册和调用逻辑。
4. 配置错误处理机制。
5. 测试各种通信场景和异常处理。