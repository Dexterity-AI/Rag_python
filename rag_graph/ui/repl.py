"""
REPL 交互界面 - 参考 Kode-cli 的设计
"""

import os
import sys
import time
import signal
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.live import Live
from rich import box

# 使用 prompt_toolkit 替代 rich.prompt，更好地支持中文
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.formatted_text import HTML

from .theme import get_theme
from .logo import Logo, PRODUCT_NAME
from .thinking import ThinkingIndicator, StepThinkingIndicator


@dataclass
class Command:
    """命令定义"""
    name: str
    description: str
    handler: Callable
    hidden: bool = False


class REPL:
    """交互式 REPL 界面"""
    
    def __init__(
        self,
        console: Console = None,
        on_query: Callable[[str], Any] = None,
        on_command: Callable[[str, List[str]], Any] = None,
        commands: List[Command] = None,
    ):
        self.console = console or Console()
        self.theme = get_theme()
        self.on_query = on_query
        self.on_command = on_command
        self.commands = commands or []
        
        # 状态
        self._running = False
        self._loading = False
        self._history = InMemoryHistory()  # 使用 prompt_toolkit 的历史记录
        
        # 中断处理
        self._interrupt_count = 0
        self._last_interrupt_time = 0
        self._double_interrupt_window = 1.5
        
        # prompt_toolkit 样式 (使用 ANSI 颜色名)
        self._pt_style = PTStyle.from_dict({
            'prompt': 'ansibrightcyan',
        })
        
        # 内置命令
        self._setup_builtin_commands()
    
    def _setup_builtin_commands(self) -> None:
        """设置内置命令"""
        builtin = [
            Command("help", "显示帮助信息", self._cmd_help),
            Command("stats", "查看系统统计", self._cmd_stats),
            Command("clear", "清空屏幕", self._cmd_clear),
            Command("quit", "退出系统", self._cmd_quit),
            Command("exit", "退出系统", self._cmd_quit, hidden=True),
        ]
        self.commands = builtin + self.commands
    
    def _cmd_help(self, args: List[str] = None) -> None:
        """显示帮助信息"""
        self.console.print()
        
        help_text = []
        help_text.append(f"[{self.theme.primary}]📖 {PRODUCT_NAME} 使用指南[/]")
        help_text.append("=" * 40)
        help_text.append("")
        help_text.append(f"[{self.theme.info}]🎯 主要功能:[/]")
        help_text.append("   • 智能问答：输入旅游相关问题")
        help_text.append("   • 图结构推理：复杂关系分析")
        help_text.append("   • 自适应检索：自动选择最佳策略")
        help_text.append("")
        help_text.append(f"[{self.theme.info}]💡 使用技巧:[/]")
        help_text.append("   • 简单问题：'故宫门票多少钱？'")
        help_text.append("   • 复杂查询：'北京三日游最佳路线'")
        help_text.append("   • 关系推理：'川菜和湘菜的区别'")
        help_text.append("")
        help_text.append(f"[{self.theme.info}]🔧 系统命令:[/]")
        
        for cmd in self.commands:
            if not cmd.hidden:
                help_text.append(f"   • /{cmd.name} - {cmd.description}")
        
        help_text.append("")
        help_text.append(f"[{self.theme.warning}]⚠️ 快捷键:[/]")
        help_text.append("   • Ctrl+C: 中断当前操作")
        help_text.append("   • 连续两次 Ctrl+C: 退出系统")
        help_text.append("=" * 40)
        
        self.console.print("\n".join(help_text))
    
    def _cmd_stats(self, args: List[str] = None) -> None:
        """显示系统统计 - 由外部实现"""
        if self.on_command:
            self.on_command("stats", args or [])
    
    def _cmd_clear(self, args: List[str] = None) -> None:
        """清空屏幕"""
        self.console.clear()
    
    def _cmd_quit(self, args: List[str] = None) -> None:
        """退出系统"""
        self._running = False
    
    def _handle_command(self, input_text: str) -> bool:
        """处理命令输入，返回是否已处理"""
        if not input_text.startswith("/"):
            return False
        
        parts = input_text[1:].split()
        if not parts:
            return False
        
        cmd_name = parts[0].lower()
        args = parts[1:]
        
        for cmd in self.commands:
            if cmd.name == cmd_name:
                cmd.handler(args)
                return True
        
        self.console.print(f"[{self.theme.error}]未知命令: /{cmd_name}[/]")
        self.console.print(f"[{self.theme.secondary_text}]输入 /help 查看可用命令[/]")
        return True
    
    def _get_prompt_message(self):
        """获取 prompt_toolkit 格式的提示符"""
        return HTML(f'<style fg="cyan">&gt;</style> ')
    
    def _render_user_message(self, text: str) -> None:
        """渲染用户消息"""
        self.console.print()
        self.console.print(f"[{self.theme.user_input}]❓ 您的问题:[/] {text}")
    
    def _render_assistant_message(self, text: str, streaming: bool = False) -> None:
        """渲染助手回复"""
        if streaming:
            # 流式输出直接打印
            self.console.print(text, end="")
        else:
            # 完整回复使用 Markdown 渲染
            self.console.print()
            md = Markdown(text)
            self.console.print(md)
    
    def _render_status(self, text: str, status: str = "info") -> None:
        """渲染状态信息"""
        style_map = {
            "info": self.theme.info,
            "success": self.theme.success,
            "warning": self.theme.warning,
            "error": self.theme.error,
        }
        style = style_map.get(status, self.theme.info)
        self.console.print(f"[{style}]{text}[/]")
    
    def show_logo(
        self,
        neo4j_status: str = "未连接",
        milvus_status: str = "未连接",
        model_name: str = "未配置",
    ) -> None:
        """显示 Logo"""
        logo = Logo(self.console)
        logo.render(
            neo4j_status=neo4j_status,
            milvus_status=milvus_status,
            model_name=model_name,
            cwd=os.getcwd(),
        )
    
    def print_hints(self) -> None:
        """打印操作提示"""
        hints = [
            f"[{self.theme.secondary_text}]💡 提示:[/]",
            f"[{self.theme.secondary_text}]   • 输入问题开始对话[/]",
            f"[{self.theme.secondary_text}]   • /help 查看帮助[/]",
            f"[{self.theme.secondary_text}]   • /quit 退出系统[/]",
        ]
        for hint in hints:
            self.console.print(hint)
        self.console.print()
    
    def run(self) -> None:
        """运行 REPL 循环"""
        self._running = True
        
        while self._running:
            try:
                # 使用 prompt_toolkit 获取用户输入 - 更好的中文支持
                user_input = pt_prompt(
                    self._get_prompt_message(),
                    history=self._history,
                    style=self._pt_style,
                    enable_history_search=True,
                )
                
                if not user_input or not user_input.strip():
                    continue
                
                user_input = user_input.strip()
                
                # 处理命令
                if self._handle_command(user_input):
                    continue
                
                # 处理查询
                if self.on_query:
                    self._render_user_message(user_input)
                    self._loading = True

                    try:
                        # 使用闪烁的星指示器显示思考状态
                        with ThinkingIndicator(
                            console=self.console,
                            message="Thinking",
                            show_elapsed=True,
                            show_detail=True,
                        ) as thinking:
                            thinking.update(detail="分析查询意图...")
                            result = self.on_query(user_input)

                        if result:
                            self._render_assistant_message(str(result))
                    except KeyboardInterrupt:
                        self._render_status("\n⏹️ 操作已中断", "warning")
                    except Exception as e:
                        self._render_status(f"\n❌ 处理错误: {e}", "error")
                    finally:
                        self._loading = False
            
            except KeyboardInterrupt:
                # Ctrl+C 处理
                current_time = time.time()
                if current_time - self._last_interrupt_time < self._double_interrupt_window:
                    self._interrupt_count += 1
                    if self._interrupt_count >= 2:
                        self.console.print(f"\n\n[{self.theme.warning}]👋 检测到连续两次 Ctrl+C，正在退出系统...[/]")
                        self._running = False
                        break
                    else:
                        self.console.print(f"\n[{self.theme.warning}]⚠️ Ctrl+C ({self._interrupt_count}/2) - 再按一次退出系统[/]")
                else:
                    self._interrupt_count = 1
                    self.console.print(f"\n[{self.theme.info}]💡 提示: 连续按两次 Ctrl+C 退出系统[/]")
                
                self._last_interrupt_time = current_time
                continue
            
            except EOFError:
                break
            except Exception as e:
                self._render_status(f"⚠️ 错误: {e}", "error")
        
        self.console.print(f"\n[{self.theme.success}]👋 感谢使用 {PRODUCT_NAME}！[/]")


class StreamingREPL(REPL):
    """支持流式输出的 REPL"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_stream_query: Optional[Callable] = None

    def set_stream_handler(self, handler: Callable) -> None:
        """设置流式查询处理器"""
        self.on_stream_query = handler

    def handle_streaming_response(self, user_input: str) -> None:
        """处理流式响应"""
        if not self.on_stream_query:
            return

        self._render_user_message(user_input)
        self.console.print()
        self.console.print(f"[{self.theme.assistant}]🎯 回答:[/]")
        self.console.print()

        interrupted = False

        try:
            # 流式输出回答
            for chunk in self.on_stream_query(user_input):
                if chunk:
                    self.console.print(chunk, end="")

            self.console.print()  # 换行

        except KeyboardInterrupt:
            interrupted = True
            self.console.print(f"\n\n[{self.theme.warning}]⏹️ 回答已被中断[/]")
        except Exception as e:
            self.console.print(f"\n[{self.theme.error}]❌ 错误: {e}[/]")

        if not interrupted:
            self.console.print()


class ProgressREPL(REPL):
    """
    带详细进度显示的 REPL
    展示查询处理的各个阶段
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_detailed_progress = True

    def run(self) -> None:
        """运行 REPL 循环 - 带详细进度显示"""
        self._running = True

        while self._running:
            try:
                # 使用 prompt_toolkit 获取用户输入
                user_input = pt_prompt(
                    self._get_prompt_message(),
                    history=self._history,
                    style=self._pt_style,
                    enable_history_search=True,
                )

                if not user_input or not user_input.strip():
                    continue

                user_input = user_input.strip()

                # 处理命令
                if self._handle_command(user_input):
                    continue

                # 处理查询 - 带详细进度显示
                if self.on_query:
                    self._render_user_message(user_input)
                    self._loading = True

                    try:
                        if self.show_detailed_progress:
                            # 使用详细进度显示
                            result = self._run_query_with_progress(user_input)
                        else:
                            # 使用闪烁的星指示器
                            with ThinkingIndicator(
                                console=self.console,
                                message="Thinking",
                                show_elapsed=True,
                            ) as thinking:
                                result = self.on_query(user_input)

                        if result:
                            self._render_assistant_message(str(result))
                    except KeyboardInterrupt:
                        self._render_status("\n⏹️ 操作已中断", "warning")
                    except Exception as e:
                        self._render_status(f"\n❌ 处理错误: {e}", "error")
                    finally:
                        self._loading = False

            except KeyboardInterrupt:
                # Ctrl+C 处理
                current_time = time.time()
                if current_time - self._last_interrupt_time < self._double_interrupt_window:
                    self._interrupt_count += 1
                    if self._interrupt_count >= 2:
                        self.console.print(f"\n\n[{self.theme.warning}]👋 检测到连续两次 Ctrl+C，正在退出系统...[/]")
                        self._running = False
                        break
                    else:
                        self.console.print(f"\n[{self.theme.warning}]⚠️ Ctrl+C ({self._interrupt_count}/2) - 再按一次退出系统[/]")
                else:
                    self._interrupt_count = 1
                    self.console.print(f"\n[{self.theme.info}]💡 提示: 连续按两次 Ctrl+C 退出系统[/]")

                self._last_interrupt_time = current_time
                continue

            except EOFError:
                break
            except Exception as e:
                self._render_status(f"⚠️ 错误: {e}", "error")

        self.console.print(f"\n[{self.theme.success}]👋 感谢使用 {PRODUCT_NAME}！[/]")

    def _run_query_with_progress(self, user_input: str) -> Any:
        """运行查询并显示详细进度"""
        # 创建进度显示器
        progress = QueryProgress(self.console)

        # 添加处理阶段
        progress.add_stage("查询分析")
        progress.add_stage("路由决策")
        progress.add_stage("检索执行")
        progress.add_stage("结果生成")

        result = None

        with progress:
            # 阶段1: 查询分析
            progress.start_stage("查询分析", "理解用户意图...")
            time.sleep(0.3)  # 给用户视觉反馈
            progress.complete_stage("查询分析", f"'{user_input[:30]}...'")

            # 阶段2: 路由决策
            progress.start_stage("路由决策", "选择检索策略...")
            time.sleep(0.2)
            progress.complete_stage("路由决策", "混合检索")

            # 阶段3: 检索执行
            progress.start_stage("检索执行", "搜索知识库...")

            # 执行实际查询
            result = self.on_query(user_input)

            progress.complete_stage("检索执行", "完成")

            # 阶段4: 结果生成
            progress.start_stage("结果生成", "组织回答...")
            time.sleep(0.2)
            progress.complete_stage("结果生成", "完成")

        return result
