"""
统一信息采集模块

提供统一的采集入口，支持 ToolBbrowser 和 Scrapling 两个采集引擎。
"""

from .core.base import BaseCollector, CollectionResult, CollectionItem
from .core.manager import CollectionManager
from .adapters.toolbbrowser_adapter import ToolBbrowserAdapter
from .adapters.scrapling_adapter import ScraplingAdapter
from .processor import CollectionProcessor, GraphRAGDataBuilder

__all__ = [
    'BaseCollector',
    'CollectionResult',
    'CollectionItem',
    'CollectionManager',
    'ToolBbrowserAdapter',
    'ScraplingAdapter',
    'CollectionProcessor',
    'GraphRAGDataBuilder',
]
