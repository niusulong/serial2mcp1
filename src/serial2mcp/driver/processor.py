"""
数据处理器
负责对接收到的数据进行解析和格式化
"""
import re
import time
from typing import Union, Dict, Any, List, Optional
from ..utils.logger import get_logger
from ..utils.exceptions import DataParsingError
from ..utils.config import config_manager
from ..utils.metrics import metrics_collector


class DataProcessor:
    """数据处理器，负责对接收到的数据进行解析、格式化和编码转换"""

    def __init__(self):
        """初始化数据处理器"""
        self.logger = get_logger("data_processor")
        self.config = config_manager.get_config()

        # 预编译常用的正则表达式
        self._patterns = {
            'whitespace': re.compile(r'\s+'),
            'hex_pattern': re.compile(r'^[0-9a-fA-F\s]+$'),
            'at_command_response': re.compile(r'^(OK|ERROR|FAIL|\+[^:]+:|C[MEGS][0-9]+:)', re.IGNORECASE),
        }

    def initialize(self) -> None:
        """初始化数据处理器"""
        self.logger.info("数据处理器初始化完成")

    def process_received_data(self, raw_data: bytes,
                            decode_utf8: bool = True,
                            auto_format: bool = True) -> Dict[str, Any]:
        """
        处理接收到的原始数据

        Args:
            raw_data: 原始字节数据
            decode_utf8: 是否尝试UTF-8解码
            auto_format: 是否自动格式化

        Returns:
            处理后的数据信息字典
        """
        result = {
            'raw_data': raw_data,
            'decoded_data': None,
            'is_hex': False,
            'encoding': None,
            'length': len(raw_data),
            'timestamp': time.time()
        }

        if not raw_data:
            result['decoded_data'] = ''
            result['encoding'] = 'utf-8'
            return result

        # 尝试UTF-8解码
        if decode_utf8:
            try:
                decoded_str = raw_data.decode('utf-8')
                result['decoded_data'] = decoded_str
                result['encoding'] = 'utf-8'

                # 如果需要自动格式化，对字符串进行处理
                if auto_format:
                    result['decoded_data'] = self._format_string_data(decoded_str)

            except UnicodeDecodeError:
                # 如果UTF-8解码失败，转换为十六进制表示
                result['decoded_data'] = raw_data.hex()
                result['is_hex'] = True
                result['encoding'] = 'hex'
        else:
            # 直接转换为十六进制表示
            result['decoded_data'] = raw_data.hex()
            result['is_hex'] = True
            result['encoding'] = 'hex'

        return result

    def _format_string_data(self, data: str) -> str:
        """
        格式化字符串数据

        Args:
            data: 原始字符串数据

        Returns:
            格式化后的字符串数据
        """
        # 移除首尾空白字符
        formatted = data.strip()

        # 将连续的空白字符替换为单个空格（可选）
        # formatted = self._patterns['whitespace'].sub(' ', formatted)

        return formatted

    def encode_to_bytes(self, data: Union[str, bytes], encoding: str = 'utf-8') -> bytes:
        """
        将数据编码为字节

        Args:
            data: 要编码的数据
            encoding: 编码格式，默认为utf-8

        Returns:
            编码后的字节数据
        """
        if isinstance(data, bytes):
            return data
        elif isinstance(data, str):
            if encoding.lower() == 'hex':
                # 处理十六进制字符串
                hex_str = re.sub(r'[^0-9a-fA-F]', '', data)  # 移除非十六进制字符
                if len(hex_str) % 2 != 0:
                    # 如果长度为奇数，前面补0
                    hex_str = '0' + hex_str
                try:
                    return bytes.fromhex(hex_str)
                except ValueError as e:
                    raise DataParsingError(f"无效的十六进制字符串: {e}")
            else:
                # 使用指定编码进行编码
                try:
                    return data.encode(encoding)
                except UnicodeEncodeError as e:
                    raise DataParsingError(f"编码错误: {e}")
        else:
            raise DataParsingError(f"不支持的数据类型: {type(data)}")

    def detect_data_type(self, data: Union[str, bytes]) -> str:
        """
        检测数据类型

        Args:
            data: 要检测的数据

        Returns:
            数据类型 ('text', 'hex', 'binary', 'at_command')
        """
        if isinstance(data, bytes):
            sample_str = data.decode('utf-8', errors='ignore')
        else:
            sample_str = data

        # 检查是否为AT命令响应
        if self._patterns['at_command_response'].search(sample_str):
            return 'at_command'

        # 检查是否为十六进制数据
        if isinstance(data, str) and self._patterns['hex_pattern'].match(data.replace(' ', '')):
            return 'hex'

        # 检查是否主要是可打印字符
        printable_chars = sum(1 for c in sample_str if c.isprintable() or c in '\n\r\t')
        if len(sample_str) > 0 and printable_chars / len(sample_str) > 0.7:
            return 'text'
        else:
            return 'binary'

    def split_data_packets(self, data: Union[str, bytes], delimiter: Union[str, bytes] = b'\n') -> List[Union[str, bytes]]:
        """
        根据分隔符拆分数据包

        Args:
            data: 要拆分的数据
            delimiter: 分隔符

        Returns:
            拆分后的数据包列表
        """
        if isinstance(data, bytes):
            if isinstance(delimiter, str):
                delimiter = delimiter.encode('utf-8')
            packets = data.split(delimiter)
        else:  # str
            if isinstance(delimiter, bytes):
                delimiter = delimiter.decode('utf-8')
            packets = data.split(delimiter)

        # 移除空的包
        return [pkt for pkt in packets if pkt]

    def validate_hex_string(self, hex_str: str) -> bool:
        """
        验证十六进制字符串格式

        Args:
            hex_str: 十六进制字符串

        Returns:
            是否为有效的十六进制字符串
        """
        clean_hex = re.sub(r'[^0-9a-fA-F]', '', hex_str)
        return len(clean_hex) % 2 == 0  # 十六进制字符串长度必须是偶数

    def format_for_display(self, raw_data: bytes, max_length: int = 100) -> str:
        """
        格式化数据显示（用于日志和调试）

        Args:
            raw_data: 原始数据
            max_length: 最大显示长度

        Returns:
            格式化的显示字符串
        """
        try:
            # 尝试UTF-8解码
            decoded = raw_data.decode('utf-8')
            if len(decoded) > max_length:
                return decoded[:max_length] + '...'
            return decoded
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，显示十六进制
            hex_str = raw_data.hex()
            if len(hex_str) > max_length:
                return hex_str[:max_length] + '...'
            return hex_str

    def normalize_line_endings(self, text: str) -> str:
        """
        标准化换行符

        Args:
            text: 输入文本

        Returns:
            标准化后的文本
        """
        return text.replace('\r\n', '\n').replace('\r', '\n')

    def extract_async_messages(self, data: str) -> List[str]:
        """
        从数据中提取异步消息

        Args:
            data: 输入数据

        Returns:
            异步消息列表
        """
        # 常见异步消息模式：以+开头的消息
        async_pattern = re.compile(r'\+[A-Za-z][A-Za-z0-9_-]*:.*?(?=\n|$)', re.MULTILINE)
        async_messages = async_pattern.findall(data)

        # 标准异步消息，如 ^、# 开头的
        standard_async_pattern = re.compile(r'[#^][A-Z][A-Z0-9_-]*:.*?(?=\n|$)', re.MULTILINE)
        async_messages.extend(standard_async_pattern.findall(data))

        return [self.normalize_line_endings(msg.strip()) for msg in async_messages if msg.strip()]

    def calculate_data_checksum(self, data: bytes, algorithm: str = 'crc16') -> str:
        """
        计算数据校验和

        Args:
            data: 输入数据
            algorithm: 校验算法，默认为crc16

        Returns:
            校验和字符串
        """
        if algorithm == 'crc16':
            # 简单的CRC16实现
            crc = 0xFFFF
            for byte in data:
                crc ^= byte
                for _ in range(8):
                    if crc & 0x0001:
                        crc >>= 1
                        crc ^= 0xA001  # CRC16-IBM 多项式反向表示
                    else:
                        crc >>= 1
            return f"{crc:04X}"
        elif algorithm == 'xor':
            # 异或校验
            checksum = 0
            for byte in data:
                checksum ^= byte
            return f"{checksum:02X}"
        else:
            raise DataParsingError(f"不支持的校验算法: {algorithm}")

    def validate_checksum(self, data: bytes, expected_checksum: str, algorithm: str = 'crc16') -> bool:
        """
        验证数据校验和

        Args:
            data: 输入数据
            expected_checksum: 期望的校验和
            algorithm: 校验算法

        Returns:
            校验是否通过
        """
        calculated_checksum = self.calculate_data_checksum(data, algorithm)
        return calculated_checksum.upper() == expected_checksum.upper()