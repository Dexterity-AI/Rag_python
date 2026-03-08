"""
动态进度显示组件 - 用于展示查询处理各阶段状态
"""

import time
import random
from typing import Optional, List
from dataclasses import dataclass
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from .theme import get_theme


# 动态spinner字符集
SPINNER_FRAMES = ['✻', '✳', '∗', '✽', '✾', '◐', '◓', '◑', '◒']

# 处理动词 - 类似 Sautéed 的设计
PROCESSING_VERBS = [
    "思考中",
    "分析中",
    "检索中",
    "推理中",
    "联想中",
    "整合中",
    "生成中",
    "构建中",
    "探索中",
    "匹配中",
    "优化中",
    "理解中",
]


@dataclass
class Stage:
    """处理阶段"""
    name: str
    status: str = "pending"  # pending, running, completed, error
    message: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    verb: str = ""

    @property
    def duration(self) -> float:
        """获取阶段耗时"""
        if self.start_time == 0:
            return 0.0
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time

    def get_formatted_duration(self) -> str:
        """获取格式化的时间字符串"""
        duration = self.duration
        if duration < 60:
            return f"{duration:.1f}s"
        else:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            return f"{minutes}m {seconds}s"


class QueryProgress:
    """
    查询处理进度显示组件
    展示从查询接收到回答生成的完整流程
    类似 "✻ Sautéed for 4m 15s" 的设计
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.theme = get_theme()
        self.stages: List[Stage] = []
        self.current_stage_index = -1
        self._live: Optional[Live] = None
        self._start_time = 0.0
        self._frame_index = 0
        self._current_verb = ""

    def _get_spinner(self) -> str:
        """获取当前spinner字符"""
        frame = SPINNER_FRAMES[self._frame_index % len(SPINNER_FRAMES)]
        self._frame_index += 1
        return frame

    def _get_verb(self) -> str:
        """获取当前处理动词"""
        if not self._current_verb:
            self._current_verb = random.choice(PROCESSING_VERBS)
        return self._current_verb

    def add_stage(self, name: str) -> Stage:
        """添加处理阶段"""
        stage = Stage(name=name, verb=random.choice(PROCESSING_VERBS))
        self.stages.append(stage)
        return stage

    def start_stage(self, name: str, message: str = ""):
        """开始某个阶段"""
        for i, stage in enumerate(self.stages):
            if stage.name == name:
                self.current_stage_index = i
                stage.status = "running"
                stage.message = message
                stage.start_time = time.time()
                stage.verb = random.choice(PROCESSING_VERBS)
                self._current_verb = stage.verb
                break
        self._update_display()

    def complete_stage(self, name: str, message: str = ""):
        """完成某个阶段"""
        for stage in self.stages:
            if stage.name == name:
                stage.status = "completed"
                stage.message = message or stage.message
                stage.end_time = time.time()
                break
        self._update_display()

    def error_stage(self, name: str, message: str = ""):
        """标记阶段出错"""
        for stage in self.stages:
            if stage.name == name:
                stage.status = "error"
                stage.message = message or "出错"
                stage.end_time = time.time()
                break
        self._update_display()

    def _render(self) -> Panel:
        """渲染进度面板 - 类似 ✻ Sautéed for 4m 15s 的设计"""
        content = []
        total_elapsed = time.time() - self._start_time if self._start_time > 0 else 0

        # 标题行 - 带动态spinner和总耗时
        header = Text()
        header.append(self._get_spinner() + " ", style=f"bold {self.theme.primary}")
        header.append(self._get_verb(), style=f"bold {self.theme.primary}")
        header.append(" for ", style=self.theme.secondary_text)
        header.append(self._format_duration(total_elapsed), style=self.theme.primary)
        content.append(header)
        content.append("")

        # 各阶段状态
        for i, stage in enumerate(self.stages):
            line = Text()

            # 状态图标和装饰
            if stage.status == "pending":
                line.append("  ○ ", style=self.theme.secondary_text)
            elif stage.status == "running":
                # 当前运行的阶段有动态spinner
                spinner = self._get_spinner()
                line.append(f"  {spinner} ", style=f"bold {self.theme.warning}")
            elif stage.status == "completed":
                line.append("  ✓ ", style=self.theme.success)
            elif stage.status == "error":
                line.append("  ✗ ", style=self.theme.error)

            # 阶段名称
            name_style = {
                "pending": self.theme.secondary_text,
                "running": f"bold {self.theme.primary}",
                "completed": self.theme.success,
                "error": self.theme.error,
            }.get(stage.status, self.theme.secondary_text)
            line.append(f"{stage.name} ", style=name_style)

            # 阶段耗时
            if stage.duration > 0:
                line.append(f"({stage.get_formatted_duration()})", style=self.theme.secondary_text)

            # 消息（斜体显示）
            if stage.message:
                line.append(f" — {stage.message}", style=f"italic {self.theme.secondary_text}")

            content.append(line)

        # 底部动态提示
        if self.current_stage_index >= 0:
            current_stage = self.stages[self.current_stage_index]
            if current_stage.status == "running":
                content.append("")
                dots = int(time.time() * 4) % 4
                anim_line = Text()
                anim_line.append("  " + "  " * dots + "▸", style=self.theme.warning)
                content.append(anim_line)

        return Panel(
            "\n".join(str(line) for line in content),
            title="[bold cyan]GraphRAG[/bold cyan]",
            border_style=self.theme.primary,
            padding=(1, 2),
        )

    def _format_duration(self, seconds: float) -> str:
        """格式化时间显示"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"

    def _update_display(self):
        """更新显示"""
        if self._live:
            self._live.update(self._render())

    def start(self):
        """开始显示进度"""
        self._start_time = time.time()
        self._current_verb = random.choice(PROCESSING_VERBS)
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=10,
            transient=True,
        )
        self._live.start()

    def stop(self):
        """停止显示进度"""
        if self._live:
            self._live.stop()
            self._live = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class SimpleProgress:
    """
    简单进度指示器 - 类似 ✻ Sautéed for 4m 15s 的设计
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        message: str = None,
        show_spinner: bool = True,
    ):
        self.console = console or Console()
        self.theme = get_theme()
        self.message = message or random.choice(PROCESSING_VERBS)
        self.show_spinner = show_spinner
        self._live: Optional[Live] = None
        self._start_time = 0.0
        self._frame_index = 0

    def _get_spinner(self) -> str:
        """获取spinner字符"""
        frame = SPINNER_FRAMES[self._frame_index % len(SPINNER_FRAMES)]
        self._frame_index += 1
        return frame

    def _format_duration(self, seconds: float) -> str:
        """格式化时间"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"

    def _render(self) -> Text:
        """渲染进度文本 - ✻ Sautéed for 4m 15s 风格"""
        text = Text()

        # Spinner图标
        if self.show_spinner:
            text.append(self._get_spinner() + " ", style=f"bold {self.theme.primary}")

        # 动词（如 Sautéed）
        text.append(self.message, style=f"bold {self.theme.primary}")

        # 连接词
        text.append(" for ", style=self.theme.secondary_text)

        # 已用时间
        elapsed = time.time() - self._start_time
        text.append(self._format_duration(elapsed), style=self.theme.primary)

        return text

    def update_message(self, message: str):
        """更新消息"""
        self.message = message
        self._update()

    def _update(self):
        """更新显示"""
        if self._live:
            self._live.update(self._render())

    def start(self):
        """开始显示"""
        self._start_time = time.time()
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=12,
            transient=True,
        )
        self._live.start()

        # 启动更新循环
        import threading

        def update_loop():
            while self._live:
                self._update()
                time.sleep(0.08)

        self._update_thread = threading.Thread(target=update_loop, daemon=True)
        self._update_thread.start()

    def stop(self):
        """停止显示"""
        if self._live:
            self._live.stop()
            self._live = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class AnimatedProgress:
    """
    带动态效果的进度条
    用于显示处理中的视觉反馈
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        message: str = None,
    ):
        self.console = console or Console()
        self.theme = get_theme()
        self.message = message or random.choice(PROCESSING_VERBS)
        self._live: Optional[Live] = None
        self._start_time = 0.0
        self._frame_index = 0

    def _get_wave(self, width: int = 20) -> str:
        """生成波浪动画"""
        wave_chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂"]
        offset = self._frame_index % len(wave_chars)
        self._frame_index += 1

        result = []
        for i in range(width):
            char_index = (offset + i) % len(wave_chars)
            result.append(wave_chars[char_index])
        return "".join(result)

    def _render(self) -> Panel:
        """渲染动态进度面板"""
        elapsed = time.time() - self._start_time

        # 构建内容
        content = Text()

        # 第一行：spinner + 动词 + 时间
        content.append(self._get_spinner() + " ", style=f"bold {self.theme.primary}")
        content.append(self.message, style=f"bold {self.theme.primary}")
        content.append(" for ", style=self.theme.secondary_text)
        content.append(self._format_duration(elapsed), style=f"bold {self.theme.primary}")
        content.append("\n\n")

        # 第二行：波浪动画
        content.append(self._get_wave(30), style=self.theme.primary)

        return Panel(
            Align.center(content),
            border_style=self.theme.primary,
            padding=(1, 2),
        )

    def _get_spinner(self) -> str:
        return SPINNER_FRAMES[self._frame_index % len(SPINNER_FRAMES)]

    def _format_duration(self, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"

    def _update(self):
        if self._live:
            self._live.update(self._render())

    def start(self):
        self._start_time = time.time()
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=15,
            transient=True,
        )
        self._live.start()

        import threading

        def update_loop():
            while self._live:
                self._update()
                time.sleep(0.06)

        self._update_thread = threading.Thread(target=update_loop, daemon=True)
        self._update_thread.start()

    def stop(self):
        if self._live:
            self._live.stop()
            self._live = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
