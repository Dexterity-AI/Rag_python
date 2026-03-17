"""
采集基类与数据模型

定义统一的采集接口和数据结构。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class CollectionStatus(Enum):
    """采集状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"  # 部分成功
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    """任务类型枚举"""
    HOT_LIST = "hot_list"           # 热榜
    SEARCH = "search"               # 搜索
    ARTICLE = "article"             # 文章/内容
    TOPIC = "topic"                 # 话题
    PROFILE = "profile"             # 用户/实体资料
    LIST = "list"                   # 列表
    CUSTOM = "custom"               # 自定义


@dataclass
class CollectionItem:
    """
    采集条目标准格式

    所有采集引擎的原始数据都应转换为这种统一格式，便于后续处理。
    """
    # 必需字段
    title: str = ""                     # 标题
    url: str = ""                       # 来源URL

    # 可选字段
    content: str = ""                   # 正文/摘要
    summary: str = ""                   # 摘要（优先于content用于短内容）
    author: str = ""                    # 作者
    publish_time: Optional[str] = None  # 发布时间 (ISO格式)
    source: str = ""                    # 来源站点
    tags: List[str] = field(default_factory=list)  # 标签
    heat: Optional[str] = None          # 热度/排名（如"5802万热度"）
    rank: Optional[int] = None          # 排名

    # 扩展字段（保留原始数据）
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CollectionItem':
        """从字典创建实例"""
        # 处理extra字段中的其他字段
        known_fields = {'title', 'url', 'content', 'summary', 'author',
                       'publish_time', 'source', 'tags', 'heat', 'rank'}
        extra = {k: v for k, v in data.items() if k not in known_fields}

        return cls(
            title=data.get('title', ''),
            url=data.get('url', ''),
            content=data.get('content', ''),
            summary=data.get('summary', ''),
            author=data.get('author', ''),
            publish_time=data.get('publish_time'),
            source=data.get('source', ''),
            tags=data.get('tags', []),
            heat=data.get('heat'),
            rank=data.get('rank'),
            extra=extra
        )


@dataclass
class CollectionResult:
    """
    采集结果标准格式

    统一的采集结果封装，包含元数据、数据体和状态信息。
    """
    # 来源信息
    source_project: str = ""            # 采集引擎: toolbbrowser / scrapling
    source_site: str = ""               # 来源站点: zhihu / weibo / news 等
    task_type: str = ""                 # 任务类型: hot_list / search / article 等

    # 时间信息
    fetch_time: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    # 请求信息
    request_url: str = ""               # 请求URL
    keyword: Optional[str] = None       # 搜索关键词

    # 数据信息
    items: List[CollectionItem] = field(default_factory=list)
    item_count: int = 0                 # 条目数

    # 文件路径
    raw_file_path: Optional[str] = None         # 原始数据文件路径
    normalized_file_path: Optional[str] = None  # 标准化数据文件路径

    # 状态信息
    status: str = CollectionStatus.PENDING.value
    error_message: Optional[str] = None

    # 原始数据快照（可选，用于调试）
    raw_data_snapshot: Optional[Dict] = None

    def __post_init__(self):
        """后处理"""
        if self.items:
            self.item_count = len(self.items)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 转换items为字典列表
        data['items'] = [item.to_dict() for item in self.items]
        return data

    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def save(self, filepath: str) -> bool:
        """保存到文件"""
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.to_json())
            return True
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
            return False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CollectionResult':
        """从字典创建实例"""
        items = [CollectionItem.from_dict(item) for item in data.get('items', [])]

        # 移除items后创建实例
        data_copy = data.copy()
        data_copy.pop('items', None)

        result = cls(**data_copy)
        result.items = items
        result.item_count = len(items)
        return result

    @classmethod
    def from_file(cls, filepath: str) -> Optional['CollectionResult']:
        """从文件加载"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            logger.error(f"加载结果失败: {e}")
            return None

    def mark_success(self):
        """标记为成功"""
        self.status = CollectionStatus.SUCCESS.value
        self.end_time = datetime.utcnow().isoformat() + 'Z'
        self.item_count = len(self.items)

    def mark_failed(self, error: str):
        """标记为失败"""
        self.status = CollectionStatus.FAILED.value
        self.end_time = datetime.utcnow().isoformat() + 'Z'
        self.error_message = error

    def mark_partial(self, error: str = ""):
        """标记为部分成功"""
        self.status = CollectionStatus.PARTIAL.value
        self.end_time = datetime.utcnow().isoformat() + 'Z'
        self.item_count = len(self.items)
        if error:
            self.error_message = error


class BaseCollector(ABC):
    """
    采集器基类

    所有采集引擎适配器都应继承此类，实现统一的采集接口。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化采集器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(self.name)

    @property
    @abstractmethod
    def source_project(self) -> str:
        """返回采集引擎名称"""
        pass

    @abstractmethod
    def collect(self, task_config: Dict[str, Any]) -> CollectionResult:
        """
        执行采集任务

        Args:
            task_config: 任务配置
                - source_site: 来源站点
                - task_type: 任务类型
                - url: 目标URL
                - keyword: 搜索关键词
                - ... 其他引擎特定参数

        Returns:
            CollectionResult: 采集结果
        """
        pass

    def validate_task(self, task_config: Dict[str, Any]) -> tuple[bool, str]:
        """
        验证任务配置

        Args:
            task_config: 任务配置

        Returns:
            (是否有效, 错误信息)
        """
        required = ['source_site', 'task_type']
        for field in required:
            if field not in task_config:
                return False, f"缺少必需字段: {field}"
        return True, ""

    def normalize_item(self, raw_item: Dict[str, Any],
                      source_site: str) -> CollectionItem:
        """
        将原始数据条目标准化为 CollectionItem

        Args:
            raw_item: 原始数据条目
            source_site: 来源站点

        Returns:
            CollectionItem: 标准化条目
        """
        # 默认实现，子类应覆盖以提供站点特定的转换
        return CollectionItem(
            title=raw_item.get('title', ''),
            url=raw_item.get('url', ''),
            content=raw_item.get('content', ''),
            summary=raw_item.get('summary', ''),
            author=raw_item.get('author', ''),
            publish_time=raw_item.get('publish_time') or raw_item.get('time'),
            source=source_site,
            tags=raw_item.get('tags', []),
            heat=raw_item.get('heat'),
            rank=raw_item.get('rank'),
            extra={k: v for k, v in raw_item.items()
                   if k not in ['title', 'url', 'content', 'summary',
                               'author', 'publish_time', 'time', 'tags', 'heat', 'rank']}
        )

    def normalize_result(self, raw_data: Dict[str, Any],
                        task_config: Dict[str, Any]) -> CollectionResult:
        """
        将原始数据标准化为 CollectionResult

        Args:
            raw_data: 原始数据
            task_config: 任务配置

        Returns:
            CollectionResult: 标准化结果
        """
        source_site = task_config.get('source_site', 'unknown')
        task_type = task_config.get('task_type', 'unknown')

        # 提取条目列表
        items_data = raw_data.get('data', raw_data.get('items', []))
        items = [self.normalize_item(item, source_site) for item in items_data]

        return CollectionResult(
            source_project=self.source_project,
            source_site=source_site,
            task_type=task_type,
            request_url=task_config.get('url', ''),
            keyword=task_config.get('keyword'),
            items=items,
            raw_data_snapshot=raw_data if self.config.get('keep_raw_snapshot') else None
        )

    def get_default_output_dir(self) -> Path:
        """获取默认输出目录"""
        from config.config import PROJECT_ROOT
        return Path(PROJECT_ROOT) / 'data' / self.source_project.lower()
