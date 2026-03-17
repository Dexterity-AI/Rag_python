"""
采集管理器

统一调度多个采集引擎，管理采集任务和数据落盘。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base import BaseCollector, CollectionResult
from .utils import generate_filename, ensure_dir
from config.config import PROJECT_ROOT

logger = logging.getLogger(__name__)


class CollectionManager:
    """
    采集管理器

    统一管理多个采集引擎，提供统一的采集入口。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化采集管理器

        Args:
            config: 全局配置
        """
        self.config = config or {}
        self.collectors: Dict[str, BaseCollector] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

        # 数据目录配置
        self.data_root = Path(PROJECT_ROOT) / 'data'
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要目录存在"""
        dirs = [
            self.data_root / 'toolbbrowser' / 'fetch',
            self.data_root / 'toolbbrowser' / 'normalized',
            self.data_root / 'scrapling' / 'raw',
            self.data_root / 'scrapling' / 'normalized',
            self.data_root / 'processed',
            self.data_root / 'logs',
        ]
        for d in dirs:
            ensure_dir(d)

    def register_collector(self, name: str, collector: BaseCollector):
        """
        注册采集器

        Args:
            name: 采集器名称
            collector: 采集器实例
        """
        self.collectors[name] = collector
        self.logger.info(f"注册采集器: {name}")

    def get_collector(self, name: str) -> Optional[BaseCollector]:
        """
        获取采集器

        Args:
            name: 采集器名称

        Returns:
            采集器实例或None
        """
        return self.collectors.get(name)

    def list_collectors(self) -> List[str]:
        """列出所有可用的采集器"""
        return list(self.collectors.keys())

    def collect(
        self,
        engine: str,
        task_config: Dict[str, Any],
        save_raw: bool = True,
        save_normalized: bool = True,
        output_dir: Optional[str] = None
    ) -> CollectionResult:
        """
        执行采集任务

        Args:
            engine: 采集引擎名称
            task_config: 任务配置
            save_raw: 是否保存原始数据
            save_normalized: 是否保存标准化数据
            output_dir: 自定义输出目录

        Returns:
            CollectionResult: 采集结果
        """
        collector = self.get_collector(engine)
        if not collector:
            result = CollectionResult(
                source_project=engine,
                source_site=task_config.get('source_site', 'unknown'),
                task_type=task_config.get('task_type', 'unknown'),
                status='failed',
                error_message=f"未找到采集引擎: {engine}"
            )
            return result

        self.logger.info(f"开始采集: engine={engine}, task={task_config}")

        try:
            # 执行采集
            result = collector.collect(task_config)

            # 确定输出目录
            if output_dir:
                base_dir = Path(output_dir)
            else:
                base_dir = self.data_root / engine.lower()

            source_site = task_config.get('source_site', 'unknown')
            task_type = task_config.get('task_type', 'unknown')

            # 保存原始数据
            if save_raw and result.raw_data_snapshot:
                raw_dir = base_dir / 'fetch' if engine == 'toolbbrowser' else base_dir / 'raw'
                raw_filename = generate_filename(source_site, task_type, stage='raw')
                raw_path = raw_dir / raw_filename

                if self._save_raw_data(result.raw_data_snapshot, raw_path):
                    result.raw_file_path = str(raw_path)
                    self.logger.info(f"原始数据已保存: {raw_path}")

            # 保存标准化数据
            if save_normalized:
                norm_dir = base_dir / 'normalized'
                norm_filename = generate_filename(source_site, task_type, stage='normalized')
                norm_path = norm_dir / norm_filename

                if result.save(norm_path):
                    result.normalized_file_path = str(norm_path)
                    self.logger.info(f"标准化数据已保存: {norm_path}")

            return result

        except Exception as e:
            self.logger.error(f"采集失败: {e}", exc_info=True)
            result = CollectionResult(
                source_project=engine,
                source_site=task_config.get('source_site', 'unknown'),
                task_type=task_config.get('task_type', 'unknown'),
                status='failed',
                error_message=str(e)
            )
            return result

    def _save_raw_data(self, data: Dict[str, Any], filepath: Path) -> bool:
        """保存原始数据"""
        try:
            ensure_dir(filepath.parent)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"保存原始数据失败: {e}")
            return False

    def batch_collect(
        self,
        tasks: List[Dict[str, Any]],
        continue_on_error: bool = True
    ) -> List[CollectionResult]:
        """
        批量执行采集任务

        Args:
            tasks: 任务列表，每个任务包含 'engine' 和 'task_config'
            continue_on_error: 出错时是否继续

        Returns:
            CollectionResult 列表
        """
        results = []

        for task in tasks:
            engine = task.get('engine')
            task_config = task.get('task_config', {})

            result = self.collect(engine, task_config)
            results.append(result)

            if result.status == 'failed' and not continue_on_error:
                self.logger.warning("任务失败，停止批量采集")
                break

        # 输出汇总
        success_count = sum(1 for r in results if r.status == 'success')
        failed_count = len(results) - success_count

        self.logger.info(f"批量采集完成: 成功 {success_count}, 失败 {failed_count}")

        return results

    def auto_select_engine(self, task_config: Dict[str, Any]) -> Optional[str]:
        """
        自动选择合适的采集引擎

        根据任务特征推荐最佳引擎。

        Args:
            task_config: 任务配置

        Returns:
            推荐的引擎名称或None
        """
        task_type = task_config.get('task_type', '')
        source_site = task_config.get('source_site', '')
        requires_login = task_config.get('requires_login', False)
        requires_browser = task_config.get('requires_browser', False)

        # 需要登录态或浏览器自动化的任务优先使用 ToolBbrowser
        if requires_login or requires_browser:
            if 'toolbbrowser' in self.collectors:
                return 'toolbbrowser'

        # 知乎热榜等需要浏览器渲染的站点
        if source_site in ['zhihu'] and task_type in ['hot_list']:
            if 'toolbbrowser' in self.collectors:
                return 'toolbbrowser'

        # 通用抓取任务优先使用 Scrapling
        if 'scrapling' in self.collectors:
            return 'scrapling'

        # 返回第一个可用的引擎
        return self.list_collectors()[0] if self.collectors else None

    def get_statistics(self) -> Dict[str, Any]:
        """获取采集统计信息"""
        stats = {
            'engines': self.list_collectors(),
            'data_directories': {}
        }

        # 统计各目录文件数
        for subdir in ['toolbbrowser/fetch', 'toolbbrowser/normalized',
                      'scrapling/raw', 'scrapling/normalized', 'processed']:
            dir_path = self.data_root / subdir
            if dir_path.exists():
                file_count = len(list(dir_path.glob('*.json')))
                stats['data_directories'][subdir] = file_count
            else:
                stats['data_directories'][subdir] = 0

        return stats
