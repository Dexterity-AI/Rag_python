"""
Thinking Indicator - 闪烁的星动态图标
参考 Claude Code / Kode-cli 的设计

在固定位置显示闪烁的星，不会重复打印
"""

import time
import threading
from typing import Optional, List
from dataclasses import dataclass
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.align import Align
from .theme import get_theme


# 闪烁的星动画帧 - 模拟星星闪烁效果
TWINKLE_FRAMES: List[str] = [
    "✦",
    "✧",
    "✦",
    "✶",
    "✦",
    "✸",
    "✦",
    "✹",
    "✦",
    "✺",
    "✦",
    "✻",
    "✦",
    "✼",
    "✦",
    "✽",
]

# 脉冲星星动画 - 更明显的闪烁效果
PULSE_FRAMES: List[str] = [
    "✦",
    "✧",
    "•",
    "✧",
    "✦",
    "✸",
    "✷",
    "✸",
    "✦",
]

# 旋转星星动画
ROTATING_FRAMES: List[str] = [
    "◐",
    "◓",
    "◑",
    "◒",
]


@dataclass
class ThinkingState:
    """思考状态数据"""
    message: str = "Thinking"
    detail: str = ""
    start_time: float = 0.0
    frame_index: int = 0

    @property
    def elapsed(self) -> float:
        """获取已用时间"""
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time


class ThinkingIndicator:
    """
    思考状态指示器 - 闪烁的星

    特点：
    1. 在固定位置显示，不会重复打印
    2. 使用 rich.Live 实现动态刷新
    3. transient=True 确保完成后清除
    4. 多种动画模式可选
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        message: str = "Thinking",
        frames: Optional[List[str]] = None,
        refresh_rate: float = 12.0,
        show_elapsed: bool = True,
        show_detail: bool = True,
    ):
        self.console = console or Console()
        self.theme = get_theme()
        self.frames = frames or TWINKLE_FRAMES
        self.refresh_rate = refresh_rate
        self.show_elapsed = show_elapsed
        self.show_detail = show_detail

        self.state = ThinkingState(message=message)
        self._live: Optional[Live] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _get_frame(self) -> str:
        """获取当前动画帧"""
        frame = self.frames[self.state.frame_index % len(self.frames)]
        self.state.frame_index += 1
        return frame

    def _format_elapsed(self) -> str:
        """格式化已用时间"""
        elapsed = self.state.elapsed
        if elapsed < 60:
            return f"{elapsed:.1f}s"
        else:
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            return f"{minutes}m {seconds}s"

    def _render(self) -> Text:
        """渲染闪烁的星指示器"""
        text = Text()

        # 闪烁的星
        star = self._get_frame()
        text.append(star + " ", style=f"bold {self.theme.primary}")

        # 主消息
        text.append(self.state.message, style=f"bold {self.theme.primary}")

        # 已用时间
        if self.show_elapsed:
            text.append(" for ", style=self.theme.secondary_text)
            text.append(self._format_elapsed(), style=self.theme.primary)

        # 详细状态
        if self.show_detail and self.state.detail:
            text.append(f" — {self.state.detail}", style=f"italic {self.theme.secondary_text}")

        return text

    def start(self, detail: str = "") -> "ThinkingIndicator":
        """开始显示思考指示器"""
        self.state.start_time = time.time()
        self.state.frame_index = 0
        if detail:
            self.state.detail = detail

        self._running = True

        # 创建 Live 显示 - transient=True 确保完成后清除
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=self.refresh_rate,
            transient=True,  # 关键：完成后自动清除，不会重复打印
        )
        self._live.start()

        # 启动更新线程
        def update_loop():
            while self._running and self._live:
                self._live.update(self._render())
                time.sleep(1.0 / self.refresh_rate)

        self._thread = threading.Thread(target=update_loop, daemon=True)
        self._thread.start()

        return self

    def stop(self) -> None:
        """停止思考指示器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
        if self._live:
            self._live.stop()
            self._live = None

    def update(self, message: Optional[str] = None, detail: Optional[str] = None) -> None:
        """更新消息和详情"""
        if message is not None:
            self.state.message = message
        if detail is not None:
            self.state.detail = detail

    def success(self, message: str = "Done") -> None:
        """标记成功并停止"""
        final_text = Text()
        final_text.append("✓ ", style=f"bold {self.theme.success}")
        final_text.append(message, style=self.theme.success)
        if self.show_elapsed:
            final_text.append(f" ({self._format_elapsed()})", style=self.theme.secondary_text)

        if self._live:
            self._live.update(final_text)
            time.sleep(0.3)  # 短暂显示成功状态
        self.stop()

    def error(self, message: str = "Failed") -> None:
        """标记错误并停止"""
        final_text = Text()
        final_text.append("✗ ", style=f"bold {self.theme.error}")
        final_text.append(message, style=self.theme.error)

        if self._live:
            self._live.update(final_text)
            time.sleep(0.3)
        self.stop()

    def __enter__(self) -> "ThinkingIndicator":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self.success()
        else:
            self.error(str(exc_val) if exc_val else "Error")


class CompactThinkingIndicator(ThinkingIndicator):
    """
    紧凑型思考指示器 - 单行显示，更简洁
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        message: str = "Thinking",
        **kwargs
    ):
        super().__init__(
            console=console,
            message=message,
            frames=PULSE_FRAMES,
            show_elapsed=True,
            show_detail=False,
            **kwargs
        )

    def _render(self) -> Text:
        """渲染紧凑格式"""
        text = Text()

        # 闪烁的星
        star = self._get_frame()
        text.append(star, style=f"bold {self.theme.primary}")

        # 消息和时间在一行
        if self.show_elapsed:
            text.append(f" {self.state.message}... ", style=self.theme.secondary_text)
            text.append(self._format_elapsed(), style=self.theme.primary)
        else:
            text.append(f" {self.state.message}...", style=self.theme.secondary_text)

        return text


class MinimalThinkingIndicator(ThinkingIndicator):
    """
    极简思考指示器 - 只有闪烁的星
    适合在已有输出行上使用
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        **kwargs
    ):
        super().__init__(
            console=console,
            message="",
            frames=TWINKLE_FRAMES,
            show_elapsed=False,
            show_detail=False,
            **kwargs
        )

    def _render(self) -> Text:
        """渲染极简格式 - 只有闪烁的星"""
        star = self._get_frame()
        return Text(star, style=f"bold {self.theme.primary}")


class StepThinkingIndicator(ThinkingIndicator):
    """
    带步骤的思考指示器
    显示多个步骤的进度，每个步骤有自己的闪烁星
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        steps: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(console=console, **kwargs)
        self.steps = steps or []
        self.current_step = 0
        self.completed_steps: List[bool] = []

    def start(self, detail: str = "") -> "StepThinkingIndicator":
        """开始显示步骤指示器"""
        self.completed_steps = [False] * len(self.steps)
        self.current_step = 0
        return super().start(detail)

    def next_step(self, detail: str = "") -> None:
        """进入下一步"""
        if self.current_step < len(self.steps):
            self.completed_steps[self.current_step] = True
            self.current_step += 1
        if detail:
            self.state.detail = detail

    def _render(self) -> Text:
        """渲染带步骤的指示器"""
        lines = []

        for i, step in enumerate(self.steps):
            line = Text()

            if i < self.current_step:
                # 已完成步骤
                line.append("  ✓ ", style=self.theme.success)
                line.append(step, style=self.theme.success)
            elif i == self.current_step:
                # 当前步骤 - 闪烁的星
                star = self._get_frame()
                line.append(f"  {star} ", style=f"bold {self.theme.primary}")
                line.append(step, style=f"bold {self.theme.primary}")
                if self.state.detail:
                    line.append(f" — {self.state.detail}", style=f"italic {self.theme.secondary_text}")
            else:
                # 待处理步骤
                line.append("  ○ ", style=self.theme.secondary_text)
                line.append(step, style=self.theme.secondary_text)

            lines.append(line)

        # 合并所有行
        result = Text("\n").join(lines)
        return result
