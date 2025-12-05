"""
通信工具
负责串口数据的发送和接收操作
"""
from typing import Dict, Any
from .base import BaseTool
from ..utils.exceptions import InvalidInputError


class CommunicationTool(BaseTool):
    """串口数据通信工具"""

    def send_data(self, **kwargs) -> Dict[str, Any]:
        """
        核心函数：发送数据并根据策略获取响应

        Args:
            **kwargs: 发送参数，包括 payload, encoding, wait_policy, stop_pattern, timeout_ms等

        Returns:
            发送结果和响应数据的字典
        """
        try:
            # 解析参数
            payload = kwargs.get('payload', '')
            encoding = kwargs.get('encoding', 'utf8')
            wait_policy = kwargs.get('wait_policy', 'none')
            stop_pattern = kwargs.get('stop_pattern')
            timeout_ms = kwargs.get('timeout_ms', 5000)  # 默认5秒

            if not payload:
                raise InvalidInputError("必须指定要发送的数据 (payload)")

            if wait_policy not in ['keyword', 'timeout', 'none']:
                raise InvalidInputError(f"无效的等待策略: {wait_policy}，支持的策略: keyword, timeout, none")

            if not self.driver.is_connected():
                raise InvalidInputError("串口未连接")

            # 编码数据
            data_bytes = self.converter.convert_to_bytes(payload, encoding)

            # 根据等待策略执行相应操作
            if wait_policy == 'none':
                # 射后不理模式
                result = self.driver.send_data(data_bytes, wait_policy='none')

            elif wait_policy == 'keyword':
                # 关键字等待模式
                if not stop_pattern:
                    raise InvalidInputError("关键字等待模式必须指定停止模式 (stop_pattern)")

                # 使用驱动内置的关键词等待功能
                result = self.driver.send_data(
                    data_bytes,
                    wait_policy='keyword',
                    stop_pattern=stop_pattern,
                    timeout=timeout_ms/1000.0
                )

            elif wait_policy == 'timeout':
                # 纯时间等待模式
                # 使用驱动内置的时间等待功能
                result = self.driver.send_data(
                    data_bytes,
                    wait_policy='timeout',
                    timeout=timeout_ms/1000.0
                )


            if result is None:
                result = {
                    'data': '',
                    'raw_data': b'',
                    'is_hex': False,
                    'bytes_received': 0
                }

            # 添加待处理异步消息计数
            result['pending_async_count'] = self.driver.get_pending_async_count()

            # 标记操作成功
            result['success'] = True

            self.logger.info(f"数据发送成功，等待策略: {wait_policy}")

            return result

        except Exception as e:
            self.logger.error(f"发送数据失败: {e}")
            return self.handle_exception(e)