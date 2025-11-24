"""
异步消息处理工具
负责处理设备主动上报的消息
"""
from typing import Dict, Any
from .base import BaseTool


class AsyncMessageTool(BaseTool):
    """异步消息处理工具"""

    def read_async_messages(self) -> Dict[str, Any]:
        """
        读取后台缓冲区中积累的异步消息

        Returns:
            异步消息列表的字典
        """
        try:
            async_messages = self.driver.get_async_messages(clear=True)

            result = {
                'success': True,
                'data': async_messages,
                'count': len(async_messages)
            }

            self.logger.info(f"读取到 {len(async_messages)} 条异步消息")

            return result

        except Exception as e:
            self.logger.error(f"读取异步消息失败: {e}")
            return self.handle_exception(e)