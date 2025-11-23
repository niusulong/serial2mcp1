# 串口底层驱动设计规范 (Serial Driver Design Spec)

**版本:** V1.1 (Logic & Architecture Focus)  
**目标:** 构建一个无业务逻辑、线程安全、支持"同步指令"与"异步URC"自动分流的串口 I/O 引擎。

这是 Step 2: 底层驱动设计规范 (文档 3) 的修订版。  
根据您的要求，本文档不包含具体代码，而是侧重于核心逻辑描述、程序流程图 (Flowcharts) 和 时序图 (Sequence Diagrams)，以便于开发人员理解数据流向和并发控制机制。

## 1. 核心架构设计

### 1.1 生产者-消费者模型

本驱动采用 "单生产者 - 双消费者" 的并发模型来处理串口的全双工特性。

**生产者 (Background Reader):**
- 一个独立的守护线程，负责从物理串口持续读取字节流。
- 它是数据的唯一入口。

**消费者 A (同步响应通道):**
- 服务于大模型发起的 send_and_receive 请求。
- 当大模型在等待结果时，数据流向此通道。

**消费者 B (异步 URC 通道):**
- 服务于后台日志和通知系统。
- 当大模型空闲时，数据流向此通道，并根据时间切片自动打包。

### 1.2 状态控制机制 (Mode Switch)

为了决定数据流向哪个消费者，驱动内部维护一个原子状态标志 (Sync Event)：

- **Sync Mode (同步模式):** 标志位置位。表示"现在正在执行指令交互，所有收到的数据都属于当前指令的响应"。
- **Idle Mode (空闲模式):** 标志位复位。表示"现在没有主动请求，所有收到的数据都是设备自动上报的 URC"。

## 2. 详细逻辑流程图 (Logic Flowcharts)

### 2.1 后台接收线程逻辑 (The Background Producer)

这是驱动的心脏，负责数据的分流和 URC 的组包。

```mermaid
flowchart TD
    Start((线程启动)) --> CheckConn{串口已连接?}
    CheckConn -- No --> Exit((线程结束))
    CheckConn -- Yes --> HasData{硬件缓冲区<br>有数据?}
    
    %% 读取数据分支
    HasData -- Yes --> ReadBytes[读取字节流]
    ReadBytes --> IsSync{处于同步模式?<br>(Sync Event Set?)}
    
    %% 同步模式处理 (直接转发)
    IsSync -- Yes --> PushResp[写入同步响应队列<br>Response Queue]
    PushResp --> CheckURCBuffer{URC缓冲<br>非空?}
    CheckURCBuffer -- Yes --> ForceFlush[强制打包剩余URC<br>写入URC队列] --> ResetTimer
    CheckURCBuffer -- No --> ResetTimer[更新最后接收时间]
    
    %% 空闲模式处理 (缓冲+分包)
    IsSync -- No --> AppendBuff[追加到本地 URC Buffer]
    AppendBuff --> ResetTimer
    
    %% 空闲超时检查 (URC 分包核心逻辑)
    HasData -- No --> CheckBuff{URC Buffer<br>非空?}
    CheckBuff -- Yes --> TimeDiff{当前时间 - 最后接收时间<br> > 空闲阈值(100ms)?}
    TimeDiff -- Yes --> PackURC[打包 Buffer 内容<br>生成 URC 消息]
    PackURC --> PushURC[写入异步 URC 队列<br>URC Queue]
    PushURC --> ClearBuff[清空 URC Buffer]
    
    %% 循环
    ResetTimer --> Sleep[微小休眠 10ms]
    ClearBuff --> Sleep
    TimeDiff -- No --> Sleep
    CheckBuff -- No --> Sleep
    Sleep --> CheckConn
```

### 2.2 智能发送与接收逻辑 (Main Thread Action)

这是大模型调用工具时的主线程行为，负责控制模式切换和判定结束条件。

```mermaid
flowchart TD
    Start((开始调用)) --> Validate[检查连接状态]
    Validate --> EnterSync[**进入同步模式**<br>Set Sync Event = True]
    EnterSync --> ClearQ[清空旧的响应队列]
    ClearQ --> SendData[发送 Payload 数据]
    
    %% 接收循环
    SendData --> LoopStart{循环检查}
    LoopStart --> CheckTimeout{总耗时 ><br>Timeout?}
    CheckTimeout -- Yes --> TimeoutExit[标记为超时]
    
    CheckTimeout -- No --> FetchQ[尝试从响应队列<br>获取数据片段]
    FetchQ -- 空/无数据 --> LoopStart
    FetchQ -- 有数据 --> Append[追加到结果 Buffer]
    
    %% 策略判定
    Append --> CheckPolicy{策略类型?}
    
    %% 策略 A: 关键字等待
    CheckPolicy -- Keyword --> Match{Buffer 包含<br>关键字?}
    Match -- Yes --> SuccessExit[标记为成功]
    Match -- No --> LoopStart
    
    %% 策略 B: 纯时间等待
    CheckPolicy -- Timeout --> LoopStart
    
    %% 退出处理
    TimeoutExit --> ExitAction
    SuccessExit --> ExitAction
    
    ExitAction[**退出同步模式**<br>Set Sync Event = False] --> Return[返回 Buffer 数据]
```

## 3. 关键交互时序图 (Sequence Diagram)

此图展示了最复杂的场景："在接收 URC 的过程中，突然插入了一条 AT 指令"。这能有效验证设计的鲁棒性。

**场景描述:**
- 设备正在上报一条短信通知 +CMTI: "SM", 1 (分两段到达)。
- 在短信第一段到达后，LLM 突然下发了查询指令 AT+CSQ。
- 驱动必须正确地将短信归类为 URC，将 +CSQ 的结果归类为响应。

```mermaid
sequenceDiagram
    participant LLM as 大模型/工具层
    participant Driver as 驱动主线程
    participant Thread as 后台接收线程
    participant QueueResp as 响应队列
    participant QueueURC as URC队列
    participant HW as 串口硬件

    Note over Driver, Thread: 初始状态：Idle Mode (空闲)

    %% 1. URC 第一部分到达
    HW->>Thread: 收到数据: "\r\n+CMTI:" (半包)
    Thread->>Thread: 检查模式: Idle
    Thread->>Thread: 存入本地 URC Buffer
    
    %% 2. LLM 此时发起指令调用
    LLM->>Driver: 调用 send("AT+CSQ", wait="OK")
    Driver->>Thread: **Set Sync Mode = True** (原子操作)
    Driver->>QueueResp: 清空残留数据
    Driver->>HW: 发送 "AT+CSQ\r\n"
    
    %% 3. 硬件回显指令 (Echo) + URC 第二部分到达
    %% 假设运气不好，它们混在一起了
    HW->>Thread: 收到数据: " SM, 1\r\n" (URC剩余)
    
    %% 这里的逻辑很关键：一旦进入 Sync Mode，数据优先给响应队列
    %% 但为了防止 URC 丢失，我们需要在切换瞬间做处理（参考逻辑说明）
    Note right of Thread: 检测到 Sync Mode 开启
    Thread->>QueueURC: **强制打包** Buffer里的 "\r\n+CMTI:"
    Thread->>QueueResp: 转发新数据 " SM, 1\r\n"
    
    %% 4. 真正的指令响应到达
    HW->>Thread: 收到数据: "\r\n+CSQ: 20,99\r\nOK\r\n"
    Thread->>QueueResp: 转发数据
    
    %% 5. 主线程读取与判定
    Loop 主线程读取
        Driver->>QueueResp: 获取数据
        Driver->>Driver: 拼接 Buffer
        Driver->>Driver: 检测到 "OK"
    End
    
    Driver->>Thread: **Set Sync Mode = False**
    Driver-->>LLM: 返回响应数据 (包含乱入的半截URC*)
    
    %% *注：此处设计权衡。
    %% 为了保证指令响应的实时性，同步期间的所有数据都视为响应。
    %% 大模型收到 "+CSQ..." 里夹杂了 "SM,1"，模型有能力识别并忽略它。
    
    %% 6. 后续 URC 处理
    Note over Thread: 回到 Idle Mode
    HW->>Thread: 收到心跳包
    Thread->>Thread: 存入 URC Buffer...
```

## 4. 核心算法逻辑详述

### 4.1 空闲分包算法 (Idle Slicing Algorithm)

由于串口数据没有标准的"包头包尾"，我们使用时间作为分包依据。

**逻辑：**
1. 定义常量 IDLE_THRESHOLD = 0.1s (100ms)。
2. 每当从硬件收到一个字节，更新变量 last_received_time = current_time。
3. 如果 URC_Buffer 不为空，且 current_time - last_received_time > IDLE_THRESHOLD：
   - 判定：上一包数据传输完毕。
   - 动作：将 URC_Buffer 的内容深拷贝，封装成 URC_Message 对象，放入 URC_Queue。
   - 清理：清空 URC_Buffer。

### 4.2 混合数据流处理策略 (Mixed Stream Handling)

当"同步指令"与"异步URC"发生冲突（如时序图中所示）时，遵循以下设计权衡：

**原则：** 指令响应优先级 > URC 数据完整性。  
**理由：** LLM 正在等待回答，延迟是不可接受的。而 URC 晚一点处理没关系。  
**副作用：** 在极少数并发情况下，同步响应的数据包里可能会夹杂一部分 URC 数据（如 +CMTI... OK）。  
**解决方案：** 依靠 LLM 强大的文本清洗能力。我们在 System Prompt 中会指示模型："如果你在响应中看到了非预期的 URC 文本，请忽略它，并在后续通过 read_urc 工具查阅。"

### 4.3 编码自适应逻辑 (Encoding Adaptation)

为了防止二进制数据导致程序崩溃，底层驱动不应抛出解码异常。

**逻辑：**
1. 获取原始字节 raw_bytes。
2. 尝试 raw_bytes.decode('utf-8')。
3. 如果成功：返回 (string, format='utf8')。
4. 如果抛出 UnicodeDecodeError：
   - 捕捉异常。
   - 执行 raw_bytes.hex(' ') (转换为 "AA BB CC")。
   - 返回 (hex_string, format='hex')。

## 5. 接口定义 (Class Methods Abstract)

开发时需实现以下方法的具体逻辑：

- **connect(port, baudrate):** 初始化资源，启动 Reader 线程。
- **disconnect():** 设置停止事件，等待线程 Join，释放资源。
- **write(bytes):** 纯粹的硬件写入。
- **read_sync(wait_policy, parameter):** 封装了"进入Sync模式 -> 循环读取 -> 退出Sync模式"的完整生命周期。这是暴露给 MCP 工具层的唯一读取接口。
- **read_urc():** 简单的从 URC_Queue 中 get_all。