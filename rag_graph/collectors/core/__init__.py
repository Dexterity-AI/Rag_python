"""
采集核心模块

包含数据模型、基类和通用工具。
"""

from .base import BaseCollector, CollectionResult, CollectionItem
from .utils import generate_filename, timestamp_now, ensure_dir

__all__ = [
    'BaseCollector',
    'CollectionResult',
    'CollectionItem',
    'generate_filename',
    'timestamp_now',
    'ensure_dir',
]
