"""
参数转换器
负责 MCP 工具参数与驱动方法参数之间的转换
"""
import re
from typing import Union, Dict, Any
from ..utils.logger import get_logger
from ..utils.exceptions import InvalidInputError
from ..driver.processor import DataProcessor


class ParameterConverter:
    """参数转换器，负责MCP工具参数与驱动方法参数之间的转换"""

    def __init__(self):
        """初始化参数转换器"""
        self.logger = get_logger("parameter_converter")
        self.data_processor = DataProcessor()
        self.data_processor.initialize()

    def convert_to_bytes(self, data: str, encoding: str = 'utf8') -> bytes:
        """
        将输入数据转换为字节

        Args:
            data: 输入数据（字符串形式）
            encoding: 编码格式 ('utf8', 'hex')

        Returns:
            转换后的字节数据
        """
        if not isinstance(data, str):
            raise InvalidInputError(f"数据必须是字符串类型，当前类型: {type(data)}")

        if not data:
            return b''

        encoding_lower = encoding.lower()

        if encoding_lower == 'utf8':
            try:
                # 处理常见的转义序列
                # 将 \\r\\n, \\n, \\r 等转换为实际的控制字符
                processed_data = data.replace('\\r\\n', '\r\n').replace('\\n', '\n').replace('\\r', '\r')
                return processed_data.encode('utf-8')
            except UnicodeEncodeError as e:
                self.logger.error(f"UTF-8编码失败: {e}")
                raise InvalidInputError(f"UTF-8编码失败: {e}")

        elif encoding_lower == 'hex':
            # 处理十六进制字符串
            # 移除可能的空格和其他非十六进制字符
            hex_str = re.sub(r'[^0-9a-fA-F]', '', data)

            # 如果长度为奇数，在前面补0
            if len(hex_str) % 2 != 0:
                self.logger.warning(f"十六进制字符串长度为奇数 ({len(hex_str)})，前面补0")
                hex_str = '0' + hex_str

            if not hex_str:
                self.logger.warning("十六进制字符串为空，返回空字节")
                return b''

            try:
                return bytes.fromhex(hex_str)
            except ValueError as e:
                self.logger.error(f"无效的十六进制字符串 '{data}': {e}")
                raise InvalidInputError(f"无效的十六进制字符串: {e}")

        else:
            raise InvalidInputError(f"不支持的编码格式: {encoding}，支持的格式: utf8, hex")

    def convert_from_bytes(self, data: bytes, encoding: str = 'utf8') -> str:
        """
        将字节数据转换为字符串

        Args:
            data: 字节数据
            encoding: 目标编码格式 ('utf8', 'hex')

        Returns:
            转换后的字符串
        """
        if not isinstance(data, bytes):
            raise InvalidInputError(f"数据必须是字节类型，当前类型: {type(data)}")

        if not data:
            return ''

        encoding_lower = encoding.lower()

        if encoding_lower == 'utf8':
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，返回十六进制表示
                self.logger.warning("UTF-8解码失败，返回十六进制表示")
                return data.hex()

        elif encoding_lower == 'hex':
            # 返回十六进制字符串，每两个字符之间用空格分隔以提高可读性
            hex_str = data.hex()
            return ' '.join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))

        else:
            raise InvalidInputError(f"不支持的编码格式: {encoding}，支持的格式: utf8, hex")

    def validate_port_name(self, port: str) -> bool:
        """
        验证串口名称是否有效

        Args:
            port: 串口名称

        Returns:
            验证结果
        """
        if not isinstance(port, str) or not port.strip():
            return False

        # 常见的串口命名模式验证
        import re
        # Windows: COM1, COM2, etc. | Linux: /dev/ttyUSB0, /dev/ttyACM0, etc. | macOS: /dev/cu.usbserial, /dev/tty.usbserial, etc.
        port_pattern = r'^(COM\d+|/dev/(ttyUSB|ttyACM|cu\..+|tty\..+|serial/.+))$'
        return bool(re.match(port_pattern, port.strip(), re.IGNORECASE))

    def parse_baudrate(self, baudrate_input: Union[str, int, float]) -> int:
        """
        解析波特率参数

        Args:
            baudrate_input: 波特率输入值

        Returns:
            解析后的波特率整数值
        """
        if isinstance(baudrate_input, (int, float)):
            baudrate = int(baudrate_input)
        elif isinstance(baudrate_input, str):
            try:
                baudrate = int(baudrate_input.strip())
            except ValueError:
                raise InvalidInputError(f"无效的波特率值: {baudrate_input}")
        else:
            raise InvalidInputError(f"波特率必须是数字类型，当前类型: {type(baudrate_input)}")

        # 常见的有效波特率范围验证
        if baudrate <= 0 or baudrate > 1500000:  # 通常波特率不会超过1.5Mbps
            raise InvalidInputError(f"波特率值超出合理范围 (0 < baudrate <= 1500000): {baudrate}")

        return baudrate

    def parse_timeout(self, timeout_input: Union[str, int, float, None]) -> float:
        """
        解析超时参数

        Args:
            timeout_input: 超时输入值（秒）

        Returns:
            解析后的超时浮点数值
        """
        if timeout_input is None:
            return 5.0  # 默认5秒

        if isinstance(timeout_input, (int, float)):
            timeout = float(timeout_input)
        elif isinstance(timeout_input, str):
            try:
                timeout = float(timeout_input.strip())
            except ValueError:
                raise InvalidInputError(f"无效的超时值: {timeout_input}")
        else:
            raise InvalidInputError(f"超时值必须是数字类型，当前类型: {type(timeout_input)}")

        # 超时值合理性检查
        if timeout <= 0 or timeout > 300:  # 最大5分钟
            raise InvalidInputError(f"超时值超出合理范围 (0 < timeout <= 300秒): {timeout}")

        return timeout

    def convert_wait_policy(self, wait_policy: str) -> str:
        """
        转换和验证等待策略

        Args:
            wait_policy: 等待策略字符串

        Returns:
            标准化的等待策略字符串
        """
        if not isinstance(wait_policy, str):
            raise InvalidInputError(f"等待策略必须是字符串类型，当前类型: {type(wait_policy)}")

        normalized_policy = wait_policy.lower().strip()

        valid_policies = ['keyword', 'timeout', 'none']
        if normalized_policy not in valid_policies:
            raise InvalidInputError(f"无效的等待策略: {wait_policy}，有效的策略: {', '.join(valid_policies)}")

        return normalized_policy

    def convert_encoding(self, encoding: str) -> str:
        """
        转换和验证编码格式

        Args:
            encoding: 编码格式字符串

        Returns:
            标准化的编码格式字符串
        """
        if not isinstance(encoding, str):
            raise InvalidInputError(f"编码格式必须是字符串类型，当前类型: {type(encoding)}")

        normalized_encoding = encoding.lower().strip()

        valid_encodings = ['utf8', 'hex']
        if normalized_encoding not in valid_encodings:
            raise InvalidInputError(f"无效的编码格式: {encoding}，有效的格式: {', '.join(valid_encodings)}")

        return normalized_encoding

    def validate_stop_pattern(self, stop_pattern: str) -> bool:
        """
        验证停止模式

        Args:
            stop_pattern: 停止模式字符串

        Returns:
            验证结果
        """
        if not isinstance(stop_pattern, str):
            return False

        # 停止模式不能为空
        if not stop_pattern.strip():
            return False

        # 检查是否包含不可打印字符（除了常见的换行符和回车符）
        import string
        allowed_control_chars = {'\n', '\r', '\t'}
        all_chars_printable = all(c in string.printable or c in allowed_control_chars for c in stop_pattern)

        return all_chars_printable

    def normalize_hex_payload(self, payload: str) -> str:
        """
        标准化十六进制负载字符串

        Args:
            payload: 十六进制负载字符串

        Returns:
            标准化后的十六进制字符串
        """
        if not isinstance(payload, str):
            raise InvalidInputError(f"负载必须是字符串类型，当前类型: {type(payload)}")

        # 移除空格和分隔符，只保留十六进制字符
        hex_part = re.sub(r'[^0-9a-fA-F]', '', payload)

        # 如果长度为奇数，前面补0
        if len(hex_part) % 2 != 0:
            hex_part = '0' + hex_part

        # 按字节分组（每两个字符一组）并用空格分隔
        grouped_hex = ' '.join(hex_part[i:i+2] for i in range(0, len(hex_part), 2))

        return grouped_hex

    def validate_parameters(self, **params) -> Dict[str, Any]:
        """
        验证一组参数

        Args:
            **params: 参数字典

        Returns:
            验证后的参数字典
        """
        validated_params = {}

        # 验证端口
        if 'port' in params and params['port'] is not None:
            if not self.validate_port_name(params['port']):
                raise InvalidInputError(f"无效的串口名称: {params['port']}")
            validated_params['port'] = params['port']

        # 验证波特率
        if 'baudrate' in params and params['baudrate'] is not None:
            validated_params['baudrate'] = self.parse_baudrate(params['baudrate'])

        # 验证超时
        if 'timeout_ms' in params and params['timeout_ms'] is not None:
            # 将毫秒转换为秒
            timeout_seconds = self.parse_timeout(params['timeout_ms']) / 1000.0
            validated_params['timeout_seconds'] = timeout_seconds

        # 验证等待策略
        if 'wait_policy' in params and params['wait_policy'] is not None:
            validated_params['wait_policy'] = self.convert_wait_policy(params['wait_policy'])

        # 验证编码格式
        if 'encoding' in params and params['encoding'] is not None:
            validated_params['encoding'] = self.convert_encoding(params['encoding'])

        # 验证停止模式
        if 'stop_pattern' in params and params['stop_pattern'] is not None:
            if not self.validate_stop_pattern(params['stop_pattern']):
                raise InvalidInputError(f"无效的停止模式: {params['stop_pattern']}")
            validated_params['stop_pattern'] = params['stop_pattern']

        # 验证操作类型
        if 'action' in params and params['action'] is not None:
            action = params['action'].lower().strip()
            if action not in ['open', 'close']:
                raise InvalidInputError(f"无效的操作类型: {params['action']}, 支持的操作: open, close")
            validated_params['action'] = action

        return validated_params