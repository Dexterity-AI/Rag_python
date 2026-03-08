#!/usr/bin/env python3
"""
演示闪烁的星 ThinkingIndicator 效果
运行: python demo_thinking.py
"""

import time
from rich.console import Console
from ui.thinking import (
    ThinkingIndicator,
    CompactThinkingIndicator,
    MinimalThinkingIndicator,
    StepThinkingIndicator,
)

console = Console()


def demo_thinking_indicator():
    """标准闪烁的星指示器"""
    console.print("\n[bold cyan]1. 标准闪烁星指示器[/]")
    console.print("-" * 40)

    with ThinkingIndicator(
        console=console,
        message="Thinking",
        show_elapsed=True,
        show_detail=True,
    ) as thinking:
        # 模拟思考过程
        time.sleep(1.5)
        thinking.update(detail="分析查询意图...")
        time.sleep(1.5)
        thinking.update(detail="检索相关知识...")
        time.sleep(1.5)

    console.print("[green]✓ 思考完成！[/]\n")


def demo_compact_indicator():
    """紧凑型指示器"""
    console.print("\n[bold cyan]2. 紧凑型闪烁星指示器[/]")
    console.print("-" * 40)

    with CompactThinkingIndicator(
        console=console,
        message="分析中",
    ):
        time.sleep(3)

    console.print("[green]✓ 完成！[/]\n")


def demo_step_indicator():
    """带步骤的指示器"""
    console.print("\n[bold cyan]3. 步骤式闪烁星指示器[/]")
    console.print("-" * 40)

    steps = ["查询分析", "路由决策", "知识检索", "答案生成"]

    with StepThinkingIndicator(
        console=console,
        steps=steps,
    ) as thinking:
        for i, step in enumerate(steps):
            thinking.next_step(f"执行{step}...")
            time.sleep(1.2)

    console.print("[green]✓ 所有步骤完成！[/]\n")


def demo_manual_control():
    """手动控制指示器"""
    console.print("\n[bold cyan]4. 手动控制指示器[/]")
    console.print("-" * 40)

    thinking = ThinkingIndicator(
        console=console,
        message="Processing",
        show_elapsed=True,
    )

    thinking.start(detail="初始化...")
    time.sleep(1.5)

    thinking.update(detail="处理中...")
    time.sleep(1.5)

    thinking.success("处理完成")
    console.print()


def demo_error_handling():
    """错误处理演示"""
    console.print("\n[bold cyan]5. 错误处理演示[/]")
    console.print("-" * 40)

    try:
        with ThinkingIndicator(
            console=console,
            message="Processing",
        ):
            time.sleep(1.5)
            raise ValueError("模拟错误")
    except ValueError:
        console.print("[red]捕获到错误，指示器自动显示错误状态[/]\n")


def demo_multiple_queries():
    """多次查询场景"""
    console.print("\n[bold cyan]6. 多次查询场景演示[/]")
    console.print("-" * 40)

    queries = [
        "北京有什么好玩的？",
        "推荐一家川菜餐厅",
        "故宫开放时间",
    ]

    for query in queries:
        console.print(f"\n[yellow]❓ 问题:[/] {query}")

        with ThinkingIndicator(
            console=console,
            message="Thinking",
            show_elapsed=True,
        ):
            time.sleep(1.5)

        console.print(f"[green]✓[/] 回答: 这是关于 '{query}' 的回答...\n")


if __name__ == "__main__":
    console.print("\n[bold magenta]✦ 闪烁的星 ThinkingIndicator 演示 ✦[/]\n")
    console.print("观察每个演示中闪烁的星在固定位置动态显示，不会重复打印\n")

    demo_thinking_indicator()
    demo_compact_indicator()
    demo_step_indicator()
    demo_manual_control()
    demo_error_handling()
    demo_multiple_queries()

    console.print("\n[bold green]✦ 所有演示完成！[/]\n")
