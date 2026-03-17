"""
采集引擎适配器

提供 ToolBbrowser 和 Scrapling 的适配实现。
"""

from .toolbbrowser_adapter import ToolBbrowserAdapter
from .scrapling_adapter import ScraplingAdapter

__all__ = [
    'ToolBbrowserAdapter',
    'ScraplingAdapter',
]
