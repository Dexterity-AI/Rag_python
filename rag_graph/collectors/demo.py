#!/usr/bin/env python3
"""
采集模块演示脚本

展示如何使用统一采集模块进行数据采集。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rag_graph.collectors import (
    CollectionManager,
    ToolBbrowserAdapter,
    ScraplingAdapter,
    CollectionProcessor,
)
from config.config import PROJECT_ROOT


def demo_basic_collection():
    """基础采集演示"""
    print("=" * 60)
    print("演示 1: 基础采集")
    print("=" * 60)

    # 创建管理器
    manager = CollectionManager()

    # 注册适配器
    manager.register_collector('toolbbrowser', ToolBbrowserAdapter())
    manager.register_collector('scrapling', ScraplingAdapter())

    print(f"已注册引擎: {manager.list_collectors()}")

    # 执行采集 - 知乎热榜
    result = manager.collect(
        engine='toolbbrowser',
        task_config={
            'source_site': 'zhihu',
            'task_type': 'hot_list',
        }
    )

    print(f"\n采集结果:")
    print(f"  状态: {result.status}")
    print(f"  引擎: {result.source_project}")
    print(f"  来源: {result.source_site}")
    print(f"  任务: {result.task_type}")
    print(f"  条数: {result.item_count}")
    print(f"  原始文件: {result.raw_file_path}")
    print(f"  标准化文件: {result.normalized_file_path}")

    if result.items:
        print(f"\n  数据预览:")
        for i, item in enumerate(result.items[:3], 1):
            print(f"    {i}. {item.title[:40]}...")

    return result


def demo_auto_engine_selection():
    """自动引擎选择演示"""
    print("\n" + "=" * 60)
    print("演示 2: 自动引擎选择")
    print("=" * 60)

    manager = CollectionManager()
    manager.register_collector('toolbbrowser', ToolBbrowserAdapter())
    manager.register_collector('scrapling', ScraplingAdapter())

    # 测试自动选择
    test_tasks = [
        {'source_site': 'zhihu', 'task_type': 'hot_list'},
        {'source_site': 'zhihu', 'task_type': 'hot_list', 'requires_login': True},
        {'source_site': 'news', 'task_type': 'article'},
    ]

    for task in test_tasks:
        engine = manager.auto_select_engine(task)
        print(f"  任务 {task} -> 推荐引擎: {engine}")


def demo_data_processing():
    """数据处理演示"""
    print("\n" + "=" * 60)
    print("演示 3: 数据处理")
    print("=" * 60)

    # 先执行采集
    manager = CollectionManager()
    manager.register_collector('toolbbrowser', ToolBbrowserAdapter())

    result = manager.collect(
        engine='toolbbrowser',
        task_config={
            'source_site': 'zhihu',
            'task_type': 'hot_list',
        }
    )

    if result.status == 'success':
        # 处理数据
        processor = CollectionProcessor({
            'chunk_size': 200,
            'chunk_overlap': 20,
            'output_format': 'jsonl'
        })

        output_dir = Path(PROJECT_ROOT) / 'data' / 'processed'
        output_path = processor.process(result, output_dir)

        print(f"  处理完成: {output_path}")

        # 显示处理后的内容
        if output_path.exists():
            with open(output_path) as f:
                lines = f.readlines()
            print(f"  生成记录数: {len(lines)}")


def demo_batch_collection():
    """批量采集演示"""
    print("\n" + "=" * 60)
    print("演示 4: 批量采集")
    print("=" * 60)

    manager = CollectionManager()
    manager.register_collector('toolbbrowser', ToolBbrowserAdapter())
    manager.register_collector('scrapling', ScraplingAdapter())

    # 批量任务
    tasks = [
        {
            'engine': 'toolbbrowser',
            'task_config': {'source_site': 'zhihu', 'task_type': 'hot_list'}
        },
        {
            'engine': 'scrapling',
            'task_config': {
                'source_site': 'example',
                'task_type': 'article',
                'url': 'https://example.com'
            }
        },
    ]

    results = manager.batch_collect(tasks)

    print(f"  任务总数: {len(results)}")
    print(f"  成功: {sum(1 for r in results if r.status == 'success')}")
    print(f"  失败: {sum(1 for r in results if r.status == 'failed')}")


def demo_health_check():
    """健康检查演示"""
    print("\n" + "=" * 60)
    print("演示 5: 健康检查")
    print("=" * 60)

    adapters = {
        'ToolBbrowser': ToolBbrowserAdapter(),
        'Scrapling': ScraplingAdapter(),
    }

    for name, adapter in adapters.items():
        health = adapter.health_check()
        available = health.get('cli_available') or health.get('module_available')
        status = "✅ 可用" if available else "⚠️ 不可用"
        print(f"  {name}: {status}")

        if not available:
            print(f"    提示: 该引擎当前处于模拟模式")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("统一采集模块演示")
    print("=" * 60)

    # 运行所有演示
    demo_basic_collection()
    demo_auto_engine_selection()
    demo_data_processing()
    demo_batch_collection()
    demo_health_check()

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print(f"\n数据输出目录: {Path(PROJECT_ROOT) / 'data'}")


if __name__ == '__main__':
    main()
