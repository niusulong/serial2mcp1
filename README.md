# Serial-Agent-MCP

**版本号:** V1.2
**项目代号:** Serial-Agent-MCP

基于 MCP (Model Context Protocol) 的智能串口交互工具，作为大语言模型与物理硬件之间的桥梁。

## 项目说明

此项目实现了一个智能串口工具，可通过 MCP 协议与大语言模型集成，实现无业务逻辑、线程安全、支持"同步指令"与"异步消息"自动分流的串口 I/O 引擎。

## 核心特性

- 智能数据分流（响应 vs 异步消息）：采用单生产者-双消费者模型，实现同步响应和异步消息的自动分流
- 零数据丢失保证：通过智能缓冲机制，确保所有数据被正确处理
- 多协议支持（AT指令、HEX数据）：支持多种编码格式和等待策略
- 实时性能监控：内置性能指标收集和监控功能
- 完整的错误处理机制：分层异常处理，提供清晰的错误信息
- 线程安全设计：使用队列和事件机制确保多线程环境下的数据安全

## 技术栈

- **核心语言:** Python 3.8+
- **通信协议:** MCP (Model Context Protocol)
- **串口通信:** pyserial
- **并发处理:** threading, queue
- **测试框架:** pytest
- **配置管理:** TOML-based 配置管理器
- **日志系统:** 结构化日志记录

## 架构设计

### 分层架构

该项目采用清晰的分层架构设计：

```
┌─────────────────────────────────────────┐
│              MCP 接口层                  │
│        (main.py, server.py)             │
├─────────────────────────────────────────┤
│              适配层                      │
│    (adapter/wrapper.py, converter.py)   │
├─────────────────────────────────────────┤
│             核心驱动层                    │
│ (driver/serial_driver.py, reader.py,    │
│  connection_manager.py, processor.py)   │
├─────────────────────────────────────────┤
│              工具类                       │
│      (utils/logger.py, config.py)       │
└─────────────────────────────────────────┘
```

#### 1. MCP 接口层
- **职责**: 提供标准MCP工具接口，处理JSON-RPC请求和响应
- **主要组件**:
  - `main.py`: MCP服务器入口点，定义和注册可用工具
  - `server.py`: (预留) MCP服务器主类

#### 2. 门面层
- **职责**: 为MCP协议提供统一的工具接口，协调和管理工具模块，处理参数验证和异常转换
- **主要组件**:
  - `facade/tool_facade.py`: SerialToolFacade - 串口工具门面
  - `facade/parameter_converter.py`: ParameterConverter - 参数转换器
  - `facade/exception_handler.py`: ExceptionHandler - 异常处理器

#### 3. 核心驱动层
- **职责**: 串口连接管理、数据收发、并发控制
- **主要组件**:
  - `driver/serial_driver.py`: SerialDriver - 串口驱动主类
  - `driver/reader.py`: (预留) BackgroundReader - 后台数据接收线程
  - `driver/connection_manager.py`: (预留) ConnectionManager - 连接管理器
  - `driver/processor.py`: (预留) DataProcessor - 数据处理器

#### 4. 工具类
- **职责**: 日志记录、配置管理、异常定义等通用功能
- **主要组件**:
  - `utils/logger.py`: 日志配置和管理
  - `utils/config.py`: 配置管理
  - `utils/exceptions.py`: 自定义异常定义

### 并发模型

系统采用单生产者-双消费者模型处理串口数据流：

```
串口硬件 → 后台接收线程 (生产者) → 数据分流器 → 同步响应队列 (消费者A)
                                              → 异步消息缓冲区 (消费者B)
```

- **生产者**: 后台接收线程持续读取串口数据
- **同步响应通道**: 处理主动指令的响应数据，实时性优先
- **异步消息通道**: 处理设备主动上报的数据，基于空闲时间进行分包，完整性优先

## MCP 工具接口

此工具实现了以下标准 MCP 工具：

1. **list_ports**: 列出当前系统所有可用的串口设备
   - 无输入参数
   - 返回设备列表(端口、描述、硬件ID)

2. **configure_connection**: 打开或关闭串口，配置参数
   - 输入: port(端口), baudrate(波特率), action(操作类型)
   - 返回: 连接状态信息

3. **send_data**: 发送数据并根据策略获取响应
   - 输入: payload(发送内容), encoding(编码格式), wait_policy(等待策略), stop_pattern(停止模式), timeout_ms(超时时间)
   - 支持多种等待策略: keyword(关键字模式), timeout(超时模式), none(射后不理), at_command(AT命令模式)
   - 返回: 发送结果和响应数据

4. **read_async_messages**: 读取后台缓冲区中积累的异步消息
   - 无输入参数
   - 返回: 异步消息列表

## 配置说明

在使用此MCP服务器时，需要在MCP客户端配置中添加如下配置：

```json
{
  "mcpServers": {
    "serial-agent-mcp": {
      "command": "python",
      "args": [
        "-m",
        "serial2mcp.main"
      ],
      "env": {
        "PYTHONPATH": "D:\\niusulong\\serial2mcp--1\\serial2mcp\\src",
        "SERIAL2MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## 项目目录结构

```
serial2mcp/
├── README.md                    # 项目说明文档
├── PROJECT_SUMMARY.md           # 项目概要说明
├── requirements.txt             # Python 依赖列表
├── setup.py                     # 包安装配置
├── pyproject.toml               # 现代Python项目配置
├── .gitignore                   # Git忽略文件
├── doc/                         # 详细设计文档
│   ├── 01-智能串口 MCP 工具需求规格说明书 (PRD).md
│   ├── 02-串口 MCP 工具接口定义契约 (Interface Schema).md
│   ├── 03-串口底层驱动设计规范 (Serial Driver Design Spec).md
│   ├── 04-系统集成与 AI 逻辑规范 (System Integration & AI Logic Spec).md
│   ├── 05-软件实现架构文档.md
│   └── 06-软件实现架构文档 - 实现细节.md
├── scripts/                     # 辅助脚本
│   ├── run_tests.sh             # 运行测试脚本
│   └── setup_dev_env.sh         # 开发环境设置脚本
├── src/                         # 源代码目录
│   └── serial2mcp/
│       ├── __init__.py
│       ├── main.py              # MCP服务器入口点
│       ├── server.py            # MCP服务器主类
│       ├── tools/               # MCP工具实现
│       │   ├── __init__.py
│       │   ├── base.py          # 基础工具类
│       │   ├── connection.py    # 连接管理工具
│       │   ├── communication.py # 通信工具
│       │   └── async_message.py # 异步消息处理工具
│       ├── driver/              # 核心驱动层
│       │   ├── __init__.py
│       │   ├── serial_driver.py # 串口驱动主类
│       │   ├── reader.py        # 后台接收线程
│       │   ├── processor.py     # 数据处理器
│       │   └── connection_manager.py # 连接管理
│       ├── adapter/             # 适配层
│       │   ├── __init__.py
│       │   ├── wrapper.py       # 工具包装器
│       │   ├── converter.py     # 参数转换器
│       │   └── exception_handler.py # 异常处理器
│       └── utils/               # 工具类
│           ├── __init__.py
│           ├── logger.py        # 日志配置
│           ├── config.py        # 配置管理
│           └── exceptions.py    # 自定义异常
├── tests/                       # 测试代码
│   ├── __init__.py
│   ├── conftest.py              # pytest配置
│   ├── unit/                    # 单元测试
│   │   ├── test_driver/
│   │   ├── test_adapter/
│   │   └── test_tools/
│   ├── integration/             # 集成测试
│   │   ├── test_mcp_server.py
│   │   └── test_serial_flow.py
│   └── fixtures/                # 测试数据
│       └── mock_serial.py
├── htmlcov/                     # 代码覆盖率报告
└── .pytest_cache/               # pytest缓存目录
```