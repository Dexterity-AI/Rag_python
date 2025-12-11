#!/usr/bin/env python3
"""
GraphRAG - 智能图RAG旅游助手

主入口文件 - 类似 Kode-cli 的启动方式

使用方法:
    python main.py                    # 启动交互式界面 (默认)
    python main.py --help             # 显示帮助
    python main.py query "问题"        # 单次查询模式
    python main.py config list        # 配置管理
    python main.py doctor             # 系统健康检查

快捷键:
    Ctrl+C (连续两次): 退出系统
    /help: 显示帮助信息
    /stats: 查看系统统计
    /quit: 退出系统
"""

import sys
import os

# 确保正确的中文编码环境
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
os.environ.setdefault('LANG', 'zh_CN.UTF-8')
os.environ.setdefault('LC_ALL', 'zh_CN.UTF-8')


def check_dependencies():
    """检查必要依赖是否安装"""
    missing = []
    
    try:
        import typer
    except ImportError:
        missing.append("typer")
    
    try:
        import rich
    except ImportError:
        missing.append("rich")
    
    if missing:
        print(f"缺少必要依赖: {', '.join(missing)}")
        print("请运行: pip install " + " ".join(missing))
        sys.exit(1)

def print_help_info_and_exit():
    print("""GraphRAG - 智能图RAG旅游助手

用法: python main.py [命令] [选项]

常用命令:
start          启动交互式界面 (默认)
query <问题>   单次查询模式
config list    列出配置
doctor         系统健康检查

选项:
-h, --help     显示帮助信息
-v, --version  显示版本信息
-V, --verbose  详细输出模式
-d, --debug    调试模式

示例:
python main.py                      # 启动交互式界面
python main.py query "北京有什么好玩的"  # 单次查询
python main.py doctor               # 检查系统状态
        """)
    sys.exit(0)

def start_app():
    # 导入并运行 CLI
    from cli import app
    # 注入start命令
    sys.argv.insert(1, 'start')
    # 启动应用
    app()

def process_cli_args():

    args = sys.argv[1:]
    if ('--help' in args or '-h' in args) and len(args) == 1:
        print_help_info_and_exit()
    elif not args or (len(args) == 1 and args[0] in ['-V', '--verbose', '-d', '--debug']):
        start_app()

def main():
    """主入口函数"""
    # 检查依赖
    check_dependencies()
   
    # 处理命令行参数,调用对应功能
    process_cli_args()

if __name__ == "__main__":
    main()
