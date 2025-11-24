"""
URC（未请求结果码）处理工具
负责处理设备主动上报的消息
"""
from typing import Dict, Any
from .base import BaseTool


class URCTool(BaseTool):
    """URC（未请求结果码）处理工具"""

    def read_urc(self) -> Dict[str, Any]:
        """
        读取后台缓冲区中积累的未处理消息（URC）

        Returns:
            URC消息列表的字典
        """
        try:
            urc_messages = self.driver.get_urc_messages(clear=True)

            result = {
                'success': True,
                'data': urc_messages,
                'count': len(urc_messages)
            }

            self.logger.info(f"读取到 {len(urc_messages)} 条URC消息")

            return result

        except Exception as e:
            self.logger.error(f"读取URC失败: {e}")
            return self.handle_exception(e)