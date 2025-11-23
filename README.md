# Serial-Agent-MCP

基于 MCP (Model Context Protocol) 的智能串口交互工具，作为大语言模型与物理硬件之间的桥梁。

## 项目说明

此项目实现了一个智能串口工具，可通过 MCP 协议与大语言模型集成，实现无业务逻辑、线程安全、支持"同步指令"与"异步URC"自动分流的串口 I/O 引擎。

## 核心特性

- 智能数据分流（响应 vs URC）
- 零数据丢失保证
- 多协议支持（AT指令、HEX数据）
- 实时性能监控
- 完整的错误处理机制

## 技术栈

- **核心语言:** Python 3.8+
- **通信协议:** MCP (Model Context Protocol)
- **串口通信:** pyserial
- **并发处理:** threading, queue
- **测试框架:** pytest

## 项目目录结构

```
serial2mcp/
├── README.md                    # 项目说明文档
├── requirements.txt             # Python 依赖列表
├── setup.py                     # 包安装配置
├── pyproject.toml              # 现代Python项目配置
├── .gitignore                  # Git忽略文件
├── .github/                    # GitHub Actions CI/CD
│   └── workflows/
│       └── test.yml
├── src/                        # 源代码目录
│   └── serial2mcp/
│       ├── __init__.py
│       ├── main.py             # MCP服务器入口点
│       ├── server.py           # MCP服务器主类
│       ├── tools/              # MCP工具实现
│       │   ├── __init__.py
│       │   ├── base.py         # 基础工具类
│       │   ├── connection.py   # 连接管理工具
│       │   ├── communication.py # 通信工具
│       │   └── urc.py          # URC处理工具
│       ├── driver/             # 核心驱动层
│       │   ├── __init__.py
│       │   ├── serial_driver.py # 串口驱动主类
│       │   ├── reader.py       # 后台接收线程
│       │   ├── processor.py    # 数据处理器
│       │   └── connection_manager.py # 连接管理
│       ├── adapter/            # 适配层
│       │   ├── __init__.py
│       │   ├── wrapper.py      # 工具包装器
│       │   ├── converter.py    # 参数转换器
│       │   └── exception_handler.py # 异常处理器
│       └── utils/              # 工具类
│           ├── __init__.py
│           ├── logger.py       # 日志配置
│           ├── config.py       # 配置管理
│           └── exceptions.py   # 自定义异常
├── tests/                      # 测试代码
│   ├── __init__.py
│   ├── conftest.py            # pytest配置
│   ├── unit/                  # 单元测试
│   │   ├── test_driver/
│   │   ├── test_adapter/
│   │   └── test_tools/
│   ├── integration/           # 集成测试
│   │   ├── test_mcp_server.py
│   │   └── test_serial_flow.py
│   └── fixtures/              # 测试数据
│       └── mock_serial.py
├── docs/                      # 文档目录
│   ├── architecture/          # 架构文档
│   ├── api/                   # API文档
│   └── examples/              # 使用示例
├── examples/                  # 示例代码
│   ├── basic_usage.py
│   └── advanced_scenarios.py
└── scripts/                   # 辅助脚本
    ├── setup_dev_env.sh
    └── run_tests.sh
```