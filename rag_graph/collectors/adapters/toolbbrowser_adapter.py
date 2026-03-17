"""
ToolBbrowser 适配器

适配 ToolBbrowser 浏览器自动化引擎。
ToolBbrowser 是一个 Node.js/TypeScript 项目，通过 CLI 调用。
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.base import BaseCollector, CollectionResult, CollectionItem
from config.config import PROJECT_ROOT

logger = logging.getLogger(__name__)


class ToolBbrowserAdapter(BaseCollector):
    """
    ToolBbrowser 采集适配器

    ToolBbrowser 主要用于需要浏览器态、登录态、动态页面交互的任务。

    前置要求:
    - ToolBbrowser 已安装: cd ToolBbrowser && pnpm install && pnpm build
    - Chrome 浏览器已安装
    - bb-browser CLI 可用
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化适配器

        Args:
            config: 配置项
                - toolbbrowser_path: ToolBbrowser 项目路径 (默认: PROJECT_ROOT/ToolBbrowser)
                - node_path: Node.js 可执行文件路径 (默认: 从 PATH 查找)
                - timeout: 命令超时时间 (默认: 60秒)
        """
        super().__init__(config)
        self.toolbbrowser_path = Path(self.config.get('toolbbrowser_path',
                                                      Path(PROJECT_ROOT) / 'ToolBbrowser'))
        self.node_path = self.config.get('node_path', 'node')
        self.timeout = self.config.get('timeout', 60)

        # 检查 CLI 是否可用
        self.cli_available = self._check_cli()

    @property
    def source_project(self) -> str:
        return 'toolbbrowser'

    def _check_cli(self) -> bool:
        """检查 ToolBbrowser CLI 是否可用"""
        cli_path = self.toolbbrowser_path / 'dist' / 'cli.js'
        if not cli_path.exists():
            logger.warning(f"ToolBbrowser CLI 未找到: {cli_path}")
            return False

        # 尝试执行 --help
        try:
            result = subprocess.run(
                [self.node_path, str(cli_path), '--help'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"ToolBbrowser CLI 检查失败: {e}")
            return False

    def _run_bb_command(self, args: List[str]) -> tuple[bool, str, str]:
        """
        运行 bb-browser 命令

        Args:
            args: 命令参数列表

        Returns:
            (是否成功, stdout, stderr)
        """
        cli_path = self.toolbbrowser_path / 'dist' / 'cli.js'
        cmd = [self.node_path, str(cli_path)] + args

        logger.debug(f"执行命令: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.toolbbrowser_path)
            )

            if result.returncode != 0:
                logger.error(f"命令执行失败: {result.stderr}")
                return False, result.stdout, result.stderr

            return True, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", f"命令执行超时 (>{self.timeout}s)"
        except Exception as e:
            return False, "", str(e)

    def collect(self, task_config: Dict[str, Any]) -> CollectionResult:
        """
        执行采集任务

        Args:
            task_config: 任务配置
                - source_site: 来源站点 (必需)
                - task_type: 任务类型 (必需)
                - url: 目标URL
                - keyword: 搜索关键词
                - selector: CSS选择器（用于提取内容）
                - wait_for: 等待条件
                - output_format: 输出格式 (json|html|text)

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

        source_site = task_config['source_site']
        task_type = task_config['task_type']

        self.logger.info(f"开始采集: {source_site} / {task_type}")

        # 检查 CLI 可用性和配置
        if self.config.get('mock') or not self.cli_available:
            logger.info("ToolBbrowser 使用模拟模式")
            return self._mock_collect(task_config)

        try:
            # 根据任务类型选择合适的采集策略
            if task_type == 'hot_list' and source_site == 'zhihu':
                raw_data = self._fetch_zhihu_hot(task_config)
            elif task_config.get('url'):
                raw_data = self._fetch_url(task_config)
            else:
                raise ValueError(f"不支持的任务配置: {task_config}")

            # 标准化结果
            result = self.normalize_result(raw_data, task_config)
            result.raw_data_snapshot = raw_data
            result.mark_success()

            self.logger.info(f"采集成功: {result.item_count} 条数据")
            return result

        except Exception as e:
            self.logger.error(f"采集失败: {e}", exc_info=True)
            # 失败后返回模拟数据（降级方案）
            logger.info("降级到模拟模式")
            return self._mock_collect(task_config)

    def _fetch_zhihu_hot(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取知乎热榜

        使用 ToolBbrowser 的 fetch 命令获取页面内容。
        注意：这是基础实现，实际需要解析 HTML 提取热榜数据。
        """
        url = "https://www.zhihu.com/hot"

        # 构建命令参数 - 使用 fetch 命令
        args = [
            'fetch',
            url
        ]

        # 执行命令
        success, stdout, stderr = self._run_bb_command(args)

        if not success:
            raise RuntimeError(f"获取失败: {stderr}")

        # 尝试解析返回的 JSON 数据
        # ToolBbrowser fetch 命令会将结果保存到文件并返回元信息
        try:
            # 首先尝试解析 stdout 为 JSON
            result = json.loads(stdout)
            return result
        except json.JSONDecodeError:
            pass

        # 检查是否有保存的文件引用
        # fetch 命令会将内容保存到 data/toolbbrowser/fetch/
        fetch_dir = Path(PROJECT_ROOT) / 'data' / 'toolbbrowser' / 'fetch'

        # 读取最近保存的文件
        if fetch_dir.exists():
            files = sorted(fetch_dir.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
            if files:
                try:
                    with open(files[0], 'r', encoding='utf-8') as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass

        # 如果无法解析，返回原始内容
        return {
            'source': 'zhihu',
            'endpoint': 'hot',
            'fetch_time': self._now_iso(),
            'count': 1,
            'data': [{'content': stdout[:2000] if stdout else '无内容', 'url': url}]
        }

    def _fetch_url(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """获取指定URL的内容"""
        url = task_config['url']
        output_format = task_config.get('output_format', 'html')

        args = [
            'fetch',
            '--url', url,
            '--format', output_format
        ]

        # 添加等待条件
        wait_for = task_config.get('wait_for')
        if wait_for:
            args.extend(['--wait-for', wait_for])

        success, stdout, stderr = self._run_bb_command(args)

        if not success:
            raise RuntimeError(f"获取失败: {stderr}")

        return {
            'source': task_config.get('source_site', 'unknown'),
            'url': url,
            'fetch_time': self._now_iso(),
            'format': output_format,
            'content': stdout,
            'count': 1,
            'data': [{'content': stdout, 'url': url}]
        }

    def _mock_collect(self, task_config: Dict[str, Any]) -> CollectionResult:
        """
        模拟采集（当 CLI 不可用时使用）

        返回示例数据用于测试和演示。
        """
        source_site = task_config.get('source_site', 'unknown')
        task_type = task_config.get('task_type', 'unknown')

        self.logger.info(f"模拟采集: {source_site} / {task_type}")

        # 返回模拟的知乎热榜数据
        if source_site == 'zhihu' and task_type == 'hot_list':
            mock_data = {
                "source": "zhihu",
                "endpoint": "hot",
                "fetch_time": self._now_iso(),
                "count": 5,
                "data": [
                    {"rank": 1, "title": "如何评价最新的技术趋势？", "heat": "5000万热度", "url": "https://zhihu.com/question/1"},
                    {"rank": 2, "title": "人工智能发展现状如何？", "heat": "4000万热度", "url": "https://zhihu.com/question/2"},
                    {"rank": 3, "title": "有哪些推荐的旅游目的地？", "heat": "3000万热度", "url": "https://zhihu.com/question/3"},
                    {"rank": 4, "title": "如何提高工作效率？", "heat": "2000万热度", "url": "https://zhihu.com/question/4"},
                    {"rank": 5, "title": "今年的流行色是什么？", "heat": "1000万热度", "url": "https://zhihu.com/question/5"},
                ]
            }

            result = self.normalize_result(mock_data, task_config)
            result.raw_data_snapshot = mock_data
            result.mark_success()
            result.error_message = "MOCK_MODE: 返回模拟数据"
            return result

        # 通用模拟数据
        mock_data = {
            "source": source_site,
            "task_type": task_type,
            "fetch_time": self._now_iso(),
            "count": 1,
            "data": [{"title": f"模拟数据: {source_site} {task_type}", "url": ""}]
        }

        result = self.normalize_result(mock_data, task_config)
        result.raw_data_snapshot = mock_data
        result.mark_success()
        result.error_message = "MOCK_MODE: 返回模拟数据"
        return result

    def _now_iso(self) -> str:
        """获取当前ISO格式时间"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'

    def normalize_item(self, raw_item: Dict[str, Any], source_site: str) -> CollectionItem:
        """标准化条目（针对 ToolBbrowser 数据优化）"""
        # 知乎热榜特殊处理
        if source_site == 'zhihu' and 'heat' in raw_item:
            return CollectionItem(
                title=raw_item.get('title', ''),
                url=raw_item.get('url', ''),
                heat=raw_item.get('heat'),
                rank=raw_item.get('rank'),
                source=source_site,
                extra={k: v for k, v in raw_item.items()
                       if k not in ['title', 'url', 'heat', 'rank']}
            )

        # 通用处理
        return super().normalize_item(raw_item, source_site)

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'cli_available': self.cli_available,
            'toolbbrowser_path': str(self.toolbbrowser_path),
            'cli_path': str(self.toolbbrowser_path / 'dist' / 'cli.js'),
            'node_path': self.node_path,
        }
