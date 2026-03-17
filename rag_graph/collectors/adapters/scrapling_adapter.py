"""
Scrapling 适配器

适配 Scrapling 爬虫框架。
Scrapling 是一个 Python 爬虫框架，直接导入使用。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.base import BaseCollector, CollectionResult, CollectionItem
from config.config import PROJECT_ROOT

logger = logging.getLogger(__name__)


class ScraplingAdapter(BaseCollector):
    """
    Scrapling 采集适配器

    Scrapling 主要用于通用页面抓取、批量采集、规则化抽取。

    前置要求:
    - Scrapling 已安装: cd Scrapling-main && pip install -e .
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化适配器

        Args:
            config: 配置项
                - scrapling_path: Scrapling 项目路径 (默认: PROJECT_ROOT/Scrapling-main)
                - default_fetcher: 默认获取器类型 (fetcher|stealth|dynamic)
                - timeout: 请求超时时间 (默认: 30秒)
                - retry_count: 重试次数 (默认: 3)
        """
        super().__init__(config)
        self.scrapling_path = Path(self.config.get('scrapling_path',
                                                   Path(PROJECT_ROOT) / 'Scrapling-main'))
        self.default_fetcher = self.config.get('default_fetcher', 'fetcher')
        self.timeout = self.config.get('timeout', 30)
        self.retry_count = self.config.get('retry_count', 3)

        # 初始化 Scrapling
        self._scrapling_module = None
        self._fetcher_class = None
        self._init_scrapling()

    def _init_scrapling(self):
        """初始化 Scrapling 模块"""
        try:
            import sys
            scrapling_path = str(self.scrapling_path)

            # 将 Scrapling 路径添加到 sys.path
            if scrapling_path not in sys.path:
                sys.path.insert(0, scrapling_path)

            # 尝试导入 Scrapling
            from scrapling import Fetcher, StealthyFetcher, DynamicFetcher

            self._scrapling_module = {
                'Fetcher': Fetcher,
                'StealthyFetcher': StealthyFetcher,
                'DynamicFetcher': DynamicFetcher,
            }

            # 设置默认获取器
            fetcher_map = {
                'fetcher': Fetcher,
                'stealth': StealthyFetcher,
                'dynamic': DynamicFetcher,
            }
            self._fetcher_class = fetcher_map.get(self.default_fetcher, Fetcher)

            logger.info("Scrapling 模块加载成功")

        except ImportError as e:
            logger.warning(f"Scrapling 模块加载失败: {e}")
            self._scrapling_module = None
            self._fetcher_class = None

    @property
    def source_project(self) -> str:
        return 'scrapling'

    @property
    def is_available(self) -> bool:
        """检查 Scrapling 是否可用"""
        return self._scrapling_module is not None

    def collect(self, task_config: Dict[str, Any]) -> CollectionResult:
        """
        执行采集任务

        Args:
            task_config: 任务配置
                - source_site: 来源站点 (必需)
                - task_type: 任务类型 (必需)
                - url: 目标URL (必需)
                - fetcher: 获取器类型 (fetcher|stealth|dynamic)
                - selector: CSS选择器或XPath（用于提取内容）
                - extract_rules: 提取规则字典
                - headers: 自定义请求头
                - proxy: 代理设置

        Returns:
            CollectionResult: 采集结果
        """
        # 验证配置
        valid, error = self.validate_task(task_config)
        if not valid:
            result = CollectionResult(
                source_project=self.source_project,
                source_site=task_config.get('source_site', 'unknown'),
                task_type=task_config.get('task_type', 'unknown'),
                status='failed',
                error_message=error
            )
            return result

        # 检查 Scrapling 可用性
        if not self.is_available:
            logger.warning("Scrapling 不可用，使用模拟模式")
            return self._mock_collect(task_config)

        source_site = task_config['source_site']
        task_type = task_config['task_type']
        url = task_config.get('url')

        if not url:
            return CollectionResult(
                source_project=self.source_project,
                source_site=source_site,
                task_type=task_type,
                status='failed',
                error_message='缺少必需参数: url'
            )

        self.logger.info(f"开始采集: {source_site} / {task_type} / {url}")

        try:
            # 选择获取器
            fetcher_type = task_config.get('fetcher', self.default_fetcher)
            fetcher_class = self._get_fetcher_class(fetcher_type)

            # 创建获取器实例
            fetcher = fetcher_class()

            # 执行请求
            response = self._do_fetch(fetcher, url, task_config)

            # 提取数据
            raw_data = self._extract_data(response, task_config, url)

            # 标准化结果
            result = self.normalize_result(raw_data, task_config)
            result.request_url = url
            result.raw_data_snapshot = raw_data
            result.mark_success()

            self.logger.info(f"采集成功: {result.item_count} 条数据")
            return result

        except Exception as e:
            self.logger.error(f"采集失败: {e}", exc_info=True)
            result = CollectionResult(
                source_project=self.source_project,
                source_site=source_site,
                task_type=task_type,
                status='failed',
                request_url=url,
                error_message=str(e)
            )
            return result

    def _get_fetcher_class(self, fetcher_type: str):
        """获取获取器类"""
        if not self._scrapling_module:
            raise RuntimeError("Scrapling 未初始化")

        fetcher_map = {
            'fetcher': 'Fetcher',
            'stealth': 'StealthyFetcher',
            'dynamic': 'DynamicFetcher',
        }

        class_name = fetcher_map.get(fetcher_type, 'Fetcher')
        return self._scrapling_module[class_name]

    def _do_fetch(self, fetcher, url: str, task_config: Dict[str, Any]):
        """执行请求"""
        # 构建请求参数
        kwargs = {
            'timeout': task_config.get('timeout', self.timeout),
        }

        # 添加请求头
        if 'headers' in task_config:
            kwargs['headers'] = task_config['headers']

        # 添加代理
        if 'proxy' in task_config:
            kwargs['proxy'] = task_config['proxy']

        # 执行请求
        return fetcher.get(url, **kwargs)

    def _extract_data(self, response, task_config: Dict[str, Any], url: str) -> Dict[str, Any]:
        """从响应中提取数据"""
        source_site = task_config['source_site']
        task_type = task_config['task_type']

        # 获取提取规则
        extract_rules = task_config.get('extract_rules', {})

        # 如果没有指定规则，使用默认规则
        if not extract_rules:
            extract_rules = self._get_default_rules(source_site, task_type)

        # 执行提取
        extracted_items = []

        if extract_rules:
            # 使用规则提取
            for rule_name, rule_config in extract_rules.items():
                selector = rule_config.get('selector', '')
                extract_type = rule_config.get('type', 'text')

                if selector:
                    elements = response.find(selector)

                    for elem in elements:
                        item = {'_rule': rule_name}

                        if extract_type == 'text':
                            item['text'] = elem.text
                        elif extract_type == 'html':
                            item['html'] = elem.html
                        elif extract_type == 'attr':
                            attr_name = rule_config.get('attr', 'href')
                            item['value'] = elem.attrs.get(attr_name)

                        # 添加其他字段
                        for field_name, field_selector in rule_config.get('fields', {}).items():
                            field_elem = elem.find(field_selector)
                            if field_elem:
                                item[field_name] = field_elem.text

                        extracted_items.append(item)
        else:
            # 无规则时提取页面基本信息
            extracted_items = [{
                'title': response.title if hasattr(response, 'title') else '',
                'url': url,
                'content': response.text if hasattr(response, 'text') else str(response)[:1000]
            }]

        return {
            'source': source_site,
            'task_type': task_type,
            'url': url,
            'fetch_time': self._now_iso(),
            'count': len(extracted_items),
            'data': extracted_items
        }

    def _get_default_rules(self, source_site: str, task_type: str) -> Dict[str, Any]:
        """获取默认提取规则"""
        # 知乎热榜规则示例
        if source_site == 'zhihu' and task_type == 'hot_list':
            return {
                'hot_item': {
                    'selector': '.HotList-item',
                    'type': 'text',
                    'fields': {
                        'title': '.HotList-itemTitle',
                        'heat': '.HotList-itemMetrics',
                    }
                }
            }

        # 新闻列表规则示例
        if task_type == 'article' or task_type == 'list':
            return {
                'article': {
                    'selector': 'article, .article, .post, .news-item',
                    'type': 'text',
                    'fields': {
                        'title': 'h1, h2, .title',
                        'summary': 'p, .summary, .excerpt',
                    }
                }
            }

        return {}

    def _mock_collect(self, task_config: Dict[str, Any]) -> CollectionResult:
        """
        模拟采集（当 Scrapling 不可用时使用）
        """
        source_site = task_config.get('source_site', 'unknown')
        task_type = task_config.get('task_type', 'unknown')
        url = task_config.get('url', '')

        self.logger.info(f"模拟采集: {source_site} / {task_type}")

        # 生成模拟数据
        mock_data = {
            'source': source_site,
            'task_type': task_type,
            'url': url,
            'fetch_time': self._now_iso(),
            'count': 3,
            'data': [
                {
                    'title': f'模拟文章 1 - {source_site}',
                    'url': f'{url}/article/1' if url else 'http://example.com/1',
                    'content': '这是模拟文章内容...',
                    'author': '模拟作者',
                },
                {
                    'title': f'模拟文章 2 - {source_site}',
                    'url': f'{url}/article/2' if url else 'http://example.com/2',
                    'content': '这是另一篇模拟文章内容...',
                    'author': '模拟作者',
                },
                {
                    'title': f'模拟文章 3 - {source_site}',
                    'url': f'{url}/article/3' if url else 'http://example.com/3',
                    'content': '这是第三篇模拟文章内容...',
                    'author': '模拟作者',
                },
            ]
        }

        result = self.normalize_result(mock_data, task_config)
        result.request_url = url
        result.raw_data_snapshot = mock_data
        result.mark_success()
        result.error_message = "MOCK_MODE: 返回模拟数据"
        return result

    def _now_iso(self) -> str:
        """获取当前ISO格式时间"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'

    def normalize_item(self, raw_item: Dict[str, Any], source_site: str) -> CollectionItem:
        """标准化条目（针对 Scrapling 数据优化）"""
        # 提取标题
        title = raw_item.get('title', '')
        if not title:
            title = raw_item.get('text', '')[:100]  # 取前100字符作为标题

        # 提取URL
        url = raw_item.get('url', '')
        if not url:
            url = raw_item.get('link', '')

        # 提取内容
        content = raw_item.get('content', '')
        if not content:
            content = raw_item.get('text', '')
            if len(content) > 200:
                content = content[200:]  # text已用作标题时，取剩余部分

        # 提取作者
        author = raw_item.get('author', '')
        if not author:
            author = raw_item.get('byline', '')

        # 提取发布时间
        publish_time = raw_item.get('publish_time') or raw_item.get('date') or raw_item.get('time')

        return CollectionItem(
            title=title,
            url=url,
            content=content,
            summary=raw_item.get('summary', '')[:200] if len(content) > 200 else content,
            author=author,
            publish_time=publish_time,
            source=source_site,
            tags=raw_item.get('tags', []),
            extra={k: v for k, v in raw_item.items()
                   if k not in ['title', 'url', 'content', 'text', 'summary',
                               'author', 'byline', 'publish_time', 'date', 'time', 'tags']}
        )

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'module_available': self.is_available,
            'scrapling_path': str(self.scrapling_path),
            'default_fetcher': self.default_fetcher,
            'available_fetchers': list(self._scrapling_module.keys()) if self._scrapling_module else [],
        }
