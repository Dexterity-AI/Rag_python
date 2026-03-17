#!/usr/bin/env python3
"""
GraphRAG CLI - 类似 Kode-cli 风格的命令行界面
基于图RAG的智能旅游助手

使用方法:
    python cli.py                    # 启动交互式界面
    python cli.py --help             # 显示帮助
    python cli.py query "问题"        # 单次查询模式
    python cli.py config list        # 配置管理
"""

import os
import sys
import time
import logging
import warnings
from typing import Optional

# 禁用 urllib3 警告
warnings.filterwarnings('ignore', message='urllib3 .* or chardet .* doesn\'t match a supported version')
warnings.filterwarnings('ignore', category=DeprecationWarning)

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

# 设置路径 - 确保当前项目优先
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
sys.path.insert(0, _current_dir)
sys.path.insert(0, _project_root)

# 清理可能冲突的旧路径
_paths_to_remove = [
    '/Users/zeng/Desktop/all_in_rag/all-in-rag/code/C9',
    '/Users/zeng/Desktop/all_in_rag',
]
for _bad_path in _paths_to_remove:
    if _bad_path in sys.path:
        sys.path.remove(_bad_path)
    # 也检查带斜杠的变体
    _bad_path_slash = _bad_path.rstrip('/')
    if _bad_path_slash in sys.path:
        sys.path.remove(_bad_path_slash)

# 导入 UI 组件
from ui import get_theme, Logo, REPL, StreamingREPL

# 创建 Typer 应用
app = typer.Typer(
    name="graphrag",
    help="GraphRAG - 智能图RAG旅游助手",
    add_completion=False,
    rich_markup_mode="rich",
)

# 全局 Console
console = Console()
theme = get_theme()

# 版本信息
VERSION = "1.0.0"
PRODUCT_NAME = "GraphRAG"


def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """设置日志"""
    level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 禁用第三方库的详细日志
    for logger_name in ["neo4j", "neo4j.notifications", "httpx", "httpcore", "openai", "urllib3"]:
        logging.getLogger(logger_name).setLevel(logging.ERROR)


def get_rag_system():
    """懒加载 RAG 系统"""
    from config.config import DEFAULT_CONFIG
    from rag_modules import (
        GraphDataPreparationModule,
        MilvusIndexConstructionModule,
        GenerationIntegrationModule
    )
    from rag_modules.hybrid_retrieval import HybridRetrievalModule
    from rag_modules.graph_rag_retrieval import GraphRAGRetrieval
    from rag_modules.intelligent_query_router import IntelligentQueryRouter
    
    return {
        'config': DEFAULT_CONFIG,
        'GraphDataPreparationModule': GraphDataPreparationModule,
        'MilvusIndexConstructionModule': MilvusIndexConstructionModule,
        'GenerationIntegrationModule': GenerationIntegrationModule,
        'HybridRetrievalModule': HybridRetrievalModule,
        'GraphRAGRetrieval': GraphRAGRetrieval,
        'IntelligentQueryRouter': IntelligentQueryRouter,
    }


class GraphRAGApp:
    """GraphRAG 应用类 - 封装系统逻辑"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.theme = get_theme()
        self.system = None
        self.system_ready = False
        
        # 模块引用
        self.data_module = None
        self.index_module = None
        self.generation_module = None
        self.traditional_retrieval = None
        self.graph_rag_retrieval = None
        self.query_router = None
        self.config = None
    
    def initialize(self) -> bool:
        """初始化系统"""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            # 获取 RAG 系统组件
            modules = get_rag_system()
            self.config = modules['config']
            
            # 1. 数据准备模块
            self.console.print(f"[{self.theme.secondary_text}]初始化数据准备模块...[/]")
            self.data_module = modules['GraphDataPreparationModule'](
                uri=self.config.neo4j_uri,
                user=self.config.neo4j_user,
                password=self.config.neo4j_password,
                database=self.config.neo4j_database
            )
            
            # 2. 向量索引模块
            self.console.print(f"[{self.theme.secondary_text}]初始化Milvus向量索引...[/]")
            self.index_module = modules['MilvusIndexConstructionModule'](
                host=self.config.milvus_host,
                port=self.config.milvus_port,
                collection_name=self.config.milvus_collection_name,
                dimension=self.config.milvus_dimension,
                model_name=self.config.embedding_model
            )
            
            # 3. 生成模块
            self.console.print(f"[{self.theme.secondary_text}]初始化生成模块...[/]")
            self.generation_module = modules['GenerationIntegrationModule'](
                config=self.config,
                model_name=self.config.llm_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            # 4. 传统混合检索模块
            self.console.print(f"[{self.theme.secondary_text}]初始化传统混合检索...[/]")
            self.traditional_retrieval = modules['HybridRetrievalModule'](
                config=self.config,
                milvus_module=self.index_module,
                data_module=self.data_module,
                llm_client=self.generation_module.client
            )
            
            # 5. 图RAG检索模块
            self.console.print(f"[{self.theme.secondary_text}]初始化图RAG检索引擎...[/]")
            self.graph_rag_retrieval = modules['GraphRAGRetrieval'](
                config=self.config,
                llm_client=self.generation_module.client
            )
            
            # 6. 智能查询路由器
            self.console.print(f"[{self.theme.secondary_text}]初始化智能查询路由器...[/]")
            self.query_router = modules['IntelligentQueryRouter'](
                traditional_retrieval=self.traditional_retrieval,
                graph_rag_retrieval=self.graph_rag_retrieval,
                llm_client=self.generation_module.client,
                config=self.config
            )
            
            return True
            
        except Exception as e:
            self.console.print(f"[{self.theme.error}]❌ 系统初始化失败: {e}[/]")
            return False
    
    def build_knowledge_base(self) -> bool:
        """构建知识库"""
        try:
            self.console.print(f"\n[{self.theme.info}]检查知识库状态...[/]")
            
            # 检查Milvus集合是否存在
            if self.index_module.has_collection():
                self.console.print(f"[{self.theme.success}]✅ 发现已存在的知识库，尝试加载...[/]")
                if self.index_module.load_collection():
                    self.console.print(f"[{self.theme.success}]知识库加载成功！[/]")
                    
                    # 加载图数据
                    self.console.print(f"[{self.theme.secondary_text}]加载图数据以支持图检索...[/]")
                    self.data_module.load_graph_data()
                    self.data_module.build_documents()
                    chunks = self.data_module.chunk_documents(
                        chunk_size=self.config.chunk_size,
                        chunk_overlap=self.config.chunk_overlap
                    )
                    
                    self._initialize_retrievers(chunks)
                    self.system_ready = True
                    return True
            
            self.console.print(f"[{self.theme.info}]未找到已存在的集合，开始构建新的知识库...[/]")
            
            # 从Neo4j加载图数据
            self.console.print(f"[{self.theme.secondary_text}]从Neo4j加载图数据...[/]")
            self.data_module.load_graph_data()
            
            self.console.print(f"[{self.theme.secondary_text}]构建旅游实体文档...[/]")
            self.data_module.build_documents()
            
            self.console.print(f"[{self.theme.secondary_text}]进行文档分块...[/]")
            chunks = self.data_module.chunk_documents(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap
            )
            
            self.console.print(f"[{self.theme.secondary_text}]构建Milvus向量索引...[/]")
            if not self.index_module.build_vector_index(chunks):
                raise Exception("构建向量索引失败")
            
            self._initialize_retrievers(chunks)
            self._show_knowledge_base_stats()
            
            self.console.print(f"[{self.theme.success}]✅ 知识库构建完成！[/]")
            self.system_ready = True
            return True
            
        except Exception as e:
            self.console.print(f"[{self.theme.error}]❌ 知识库构建失败: {e}[/]")
            return False
    
    def _initialize_retrievers(self, chunks=None):
        """初始化检索器"""
        self.console.print(f"[{self.theme.secondary_text}]初始化检索引擎...[/]")
        
        if chunks is None:
            chunks = self.data_module.chunks or []
        
        self.traditional_retrieval.initialize(chunks)
        self.graph_rag_retrieval.initialize()
        
        self.console.print(f"[{self.theme.success}]✅ 检索引擎初始化完成！[/]")
    
    def _show_knowledge_base_stats(self):
        """显示知识库统计"""
        stats = self.data_module.get_statistics()
        
        self.console.print(f"\n[{self.theme.info}]📊 知识库统计:[/]")
        self.console.print(f"   城市/地区: {stats.get('total_cities', 0)}")
        self.console.print(f"   景点数量: {stats.get('total_attractions', 0)}")
        self.console.print(f"   美食数量: {stats.get('total_foods', 0)}")
        self.console.print(f"   文档数量: {stats.get('total_documents', 0)}")
        self.console.print(f"   文本块数: {stats.get('total_chunks', 0)}")
    
    def query(self, question: str, stream: bool = True) -> str:
        """处理查询"""
        if not self.system_ready:
            return "系统未就绪，请先初始化"
        
        try:
            # 智能路由检索
            relevant_docs, analysis = self.query_router.route_query(question, self.config.top_k)
            
            # 路由信息已隐藏，只显示答案
            if not relevant_docs:
                return "抱歉，没有找到相关的旅游信息。请尝试其他问题。"
            
            # 生成回答
            if stream:
                return self._stream_answer(question, relevant_docs)
            else:
                return self.generation_module.generate_adaptive_answer(question, relevant_docs)
                
        except Exception as e:
            return f"处理问题时出现错误：{str(e)}"
    
    def _stream_answer(self, question: str, relevant_docs) -> str:
        """流式生成回答"""
        result_parts = []
        
        self.console.print(f"\n[{self.theme.assistant}]🎯 回答:[/]")
        self.console.print()
        
        try:
            for chunk_text in self.generation_module.generate_adaptive_answer_stream(question, relevant_docs):
                self.console.print(chunk_text, end="")
                result_parts.append(chunk_text)
            
            self.console.print()  # 换行
            return "".join(result_parts)
            
        except Exception as e:
            self.console.print(f"\n[{self.theme.error}]流式输出出错: {e}[/]")
            return self.generation_module.generate_adaptive_answer(question, relevant_docs)
    
    def get_status(self) -> dict:
        """获取系统状态"""
        neo4j_status = "已连接" if self.data_module else "未连接"
        milvus_status = "已连接" if self.index_module else "未连接"
        model_name = self.config.llm_model if self.config else "未配置"
        
        return {
            "neo4j": neo4j_status,
            "milvus": milvus_status,
            "model": model_name,
            "ready": self.system_ready,
        }
    
    def cleanup(self):
        """清理资源"""
        if self.data_module:
            self.data_module.close()
        if self.traditional_retrieval:
            self.traditional_retrieval.close()
        if self.graph_rag_retrieval:
            self.graph_rag_retrieval.close()
        if self.index_module:
            self.index_module.close()


def version_callback(value: bool):
    """版本回调"""
    if value:
        console.print(f"[{theme.primary}]{PRODUCT_NAME}[/] v{VERSION}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False, "--version", "-v",
        callback=version_callback,
        is_eager=True,
        help="显示版本信息"
    ),
):
    """GraphRAG - 智能图RAG旅游助手"""
    pass


@app.command()
def start(
    verbose: bool = typer.Option(False, "--verbose", "-V", help="详细输出模式"),
    debug: bool = typer.Option(False, "--debug", "-d", help="调试模式"),
    safe: bool = typer.Option(False, "--safe", help="安全模式"),
):
    """
    启动交互式 GraphRAG 助手
    
    这是主要的入口命令，启动后可以进行交互式问答。
    """
    setup_logging(verbose, debug)
    
    # 创建应用实例
    rag_app = GraphRAGApp(console)
    
    # 显示启动信息
    console.clear()

    # 初始化系统
    console.print(f"[{theme.info}]初始化系统中...[/]")
    if not rag_app.initialize():
        raise typer.Exit(1)
    console.print(f"[{theme.success}]✓ 系统初始化完成[/]")

    # 构建知识库
    console.print(f"[{theme.info}]加载知识库中...[/]")
    if not rag_app.build_knowledge_base():
        raise typer.Exit(1)
    console.print(f"[{theme.success}]✓ 知识库加载完成[/]")
    
    # 获取状态
    status = rag_app.get_status()
    
    # 显示 Logo
    logo = Logo(console)
    logo.render(
        neo4j_status=status["neo4j"],
        milvus_status=status["milvus"],
        model_name=status["model"],
        cwd=os.getcwd(),
    )
    
    # 创建 REPL - 使用基础 REPL
    def on_query(question: str) -> str:
        return rag_app.query(question, stream=True)

    def on_command(cmd: str, args: list) -> None:
        if cmd == "stats":
            rag_app._show_knowledge_base_stats()

    repl = REPL(
        console=console,
        on_query=on_query,
        on_command=on_command,
    )
    
    # 打印提示
    repl.print_hints()
    
    try:
        # 运行 REPL
        repl.run()
    finally:
        # 清理资源
        rag_app.cleanup()


@app.command()
def query(
    question: str = typer.Argument(..., help="要查询的问题"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="是否流式输出"),
):
    """
    单次查询模式
    
    直接查询问题并获取回答，不进入交互模式。
    """
    setup_logging()

    rag_app = GraphRAGApp(console)

    console.print(f"[{theme.info}]初始化系统中...[/]")
    if not rag_app.initialize():
        raise typer.Exit(1)
    console.print(f"[{theme.success}]✓ 系统初始化完成[/]")

    console.print(f"[{theme.info}]加载知识库中...[/]")
    if not rag_app.build_knowledge_base():
        raise typer.Exit(1)
    console.print(f"[{theme.success}]✓ 知识库加载完成[/]")
    
    result = rag_app.query(question, stream=stream)
    
    if not stream:
        console.print(result)
    
    rag_app.cleanup()


# Config 子命令组
config_app = typer.Typer(help="配置管理命令")
app.add_typer(config_app, name="config")


@config_app.command("list")
def config_list():
    """列出所有配置"""
    from config.config import DEFAULT_CONFIG
    
    config_dict = DEFAULT_CONFIG.to_dict()
    
    console.print(f"\n[{theme.primary}]📋 当前配置:[/]\n")
    
    for key, value in config_dict.items():
        # 隐藏敏感信息
        if "password" in key.lower() or "key" in key.lower():
            display_value = "***" if value else "(未设置)"
        else:
            display_value = value if value else "(未设置)"
        
        console.print(f"  {key}: [{theme.secondary_text}]{display_value}[/]")


@config_app.command("get")
def config_get(key: str = typer.Argument(..., help="配置项名称")):
    """获取指定配置项"""
    from config.config import DEFAULT_CONFIG
    
    config_dict = DEFAULT_CONFIG.to_dict()
    
    if key in config_dict:
        value = config_dict[key]
        if "password" in key.lower() or "key" in key.lower():
            value = "***" if value else "(未设置)"
        console.print(f"{key}: {value}")
    else:
        console.print(f"[{theme.error}]未知配置项: {key}[/]")
        raise typer.Exit(1)


@app.command()
def doctor():
    """
    检查系统健康状态
    
    检查所有必需服务的连接状态。
    """
    console.print(f"\n[{theme.primary}]🏥 系统健康检查[/]\n")
    
    checks = []
    
    # 检查 Neo4j
    try:
        from config.config import DEFAULT_CONFIG
        from neo4j import GraphDatabase
        
        driver = GraphDatabase.driver(
            DEFAULT_CONFIG.neo4j_uri,
            auth=(DEFAULT_CONFIG.neo4j_user, DEFAULT_CONFIG.neo4j_password)
        )
        driver.verify_connectivity()
        driver.close()
        checks.append(("Neo4j", True, "连接正常"))
    except Exception as e:
        checks.append(("Neo4j", False, str(e)))
    
    # 检查 Milvus
    try:
        from pymilvus import connections
        from config.config import DEFAULT_CONFIG
        
        connections.connect(
            alias="health_check",
            host=DEFAULT_CONFIG.milvus_host,
            port=DEFAULT_CONFIG.milvus_port
        )
        connections.disconnect("health_check")
        checks.append(("Milvus", True, "连接正常"))
    except Exception as e:
        checks.append(("Milvus", False, str(e)))
    
    # 检查 LLM API
    try:
        from config.config import DEFAULT_CONFIG
        if DEFAULT_CONFIG.llm_api_key and DEFAULT_CONFIG.llm_base_url:
            checks.append(("LLM API", True, f"已配置 ({DEFAULT_CONFIG.llm_model})"))
        else:
            checks.append(("LLM API", False, "未配置 API Key 或 Base URL"))
    except Exception as e:
        checks.append(("LLM API", False, str(e)))
    
    # 显示结果
    for name, status, message in checks:
        icon = "✅" if status else "❌"
        color = theme.success if status else theme.error
        console.print(f"  {icon} {name}: [{color}]{message}[/]")
    
    console.print()
    
    all_passed = all(c[1] for c in checks)
    if all_passed:
        console.print(f"[{theme.success}]所有检查通过！系统可以正常运行。[/]")
    else:
        console.print(f"[{theme.warning}]部分检查未通过，请检查相关服务配置。[/]")
        raise typer.Exit(1)


# Cache 子命令组
cache_app = typer.Typer(help="缓存管理命令")
app.add_typer(cache_app, name="cache")


@cache_app.command("stats")
def cache_stats():
    """显示缓存统计信息"""
    from cache import get_cache_manager

    cache_manager = get_cache_manager()
    stats = cache_manager.get_stats()

    console.print(f"\n[{theme.primary}]📊 缓存统计[/]\n")

    # 向量检索缓存
    vector_stats = stats.get('vector_cache')
    if vector_stats:
        console.print(f"[{theme.info}]向量检索缓存:[/]")
        console.print(f"  条目数: {vector_stats.get('size', 0)}")
        console.print(f"  命中: {vector_stats.get('hits', 0)}")
        console.print(f"  未命中: {vector_stats.get('misses', 0)}")
        console.print(f"  命中率: {vector_stats.get('hit_rate', 0):.2%}")
        console.print()

    # 图查询缓存
    graph_stats = stats.get('graph_cache')
    if graph_stats:
        console.print(f"[{theme.info}]图查询缓存:[/]")
        console.print(f"  条目数: {graph_stats.get('size', 0)}")
        console.print(f"  命中: {graph_stats.get('hits', 0)}")
        console.print(f"  未命中: {graph_stats.get('misses', 0)}")
        console.print(f"  命中率: {graph_stats.get('hit_rate', 0):.2%}")
        console.print()

    # LLM缓存
    llm_stats = stats.get('llm_cache')
    if llm_stats:
        console.print(f"[{theme.info}]LLM结果缓存:[/]")
        console.print(f"  条目数: {llm_stats.get('size', 0)}")
        console.print(f"  命中: {llm_stats.get('hits', 0)}")
        console.print(f"  未命中: {llm_stats.get('misses', 0)}")
        console.print(f"  命中率: {llm_stats.get('hit_rate', 0):.2%}")
        console.print()

    # 总体统计
    overall = stats.get('overall', {})
    console.print(f"[{theme.success}]总体统计:[/]")
    console.print(f"  总请求: {overall.get('total_requests', 0)}")
    console.print(f"  总命中: {overall.get('total_hits', 0)}")
    console.print(f"  总体命中率: {overall.get('overall_hit_rate', 0):.2%}")


@cache_app.command("clear")
def cache_clear(
    vector: bool = typer.Option(False, "--vector", help="清空向量检索缓存"),
    graph: bool = typer.Option(False, "--graph", help="清空图查询缓存"),
    llm: bool = typer.Option(False, "--llm", help="清空LLM结果缓存"),
    all: bool = typer.Option(False, "--all", help="清空所有缓存"),
):
    """清空缓存"""
    from cache import get_cache_manager

    cache_manager = get_cache_manager()

    if all:
        cache_manager.clear_all()
        console.print(f"[{theme.success}]✅ 所有缓存已清空[/]")
    else:
        if vector:
            cache_manager.clear_vector_cache()
            console.print(f"[{theme.success}]✅ 向量检索缓存已清空[/]")
        if graph:
            cache_manager.clear_graph_cache()
            console.print(f"[{theme.success}]✅ 图查询缓存已清空[/]")
        if llm:
            cache_manager.clear_llm_cache()
            console.print(f"[{theme.success}]✅ LLM结果缓存已清空[/]")

        if not any([vector, graph, llm]):
            console.print(f"[{theme.warning}]⚠️ 请指定要清空的缓存类型（--vector, --graph, --llm, --all）[/]")
            raise typer.Exit(1)


# Collect 子命令组 - 统一采集入口
collect_app = typer.Typer(help="数据采集命令")
app.add_typer(collect_app, name="collect")


@collect_app.command("run")
def collect_run(
    engine: str = typer.Argument(..., help="采集引擎: toolbbrowser, scrapling, auto"),
    source: str = typer.Option(..., "--source", "-s", help="来源站点: zhihu, weibo, news等"),
    task: str = typer.Option(..., "--task", "-t", help="任务类型: hot_list, search, article等"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="目标URL"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="搜索关键词"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出目录"),
    mock: bool = typer.Option(False, "--mock", help="使用模拟模式"),
):
    """
    执行采集任务

    示例:
        python cli.py collect run toolbbrowser -s zhihu -t hot_list
        python cli.py collect run scrapling -s news -t article -u https://example.com
        python cli.py collect run auto -s zhihu -t hot_list --mock
    """
    from collectors import CollectionManager, ToolBbrowserAdapter, ScraplingAdapter

    console.print(f"\n[{theme.primary}]🕷️ 启动数据采集[/]\n")

    # 创建管理器
    manager = CollectionManager()

    # 注册适配器（如果不是mock模式）
    if not mock:
        manager.register_collector('toolbbrowser', ToolBbrowserAdapter())
        manager.register_collector('scrapling', ScraplingAdapter())
    else:
        # mock 模式下注册空配置适配器
        manager.register_collector('toolbbrowser', ToolBbrowserAdapter({'mock': True}))
        manager.register_collector('scrapling', ScraplingAdapter({'mock': True}))

    # 确定引擎
    if engine == 'auto':
        task_config = {
            'source_site': source,
            'task_type': task,
            'url': url,
            'keyword': keyword,
        }
        selected_engine = manager.auto_select_engine(task_config)
        if not selected_engine:
            console.print(f"[{theme.error}]❌ 无法自动选择合适的引擎[/]")
            raise typer.Exit(1)
        console.print(f"[{theme.info}]自动选择引擎: {selected_engine}[/]")
        engine = selected_engine

    # 构建任务配置
    task_config = {
        'source_site': source,
        'task_type': task,
    }
    if url:
        task_config['url'] = url
    if keyword:
        task_config['keyword'] = keyword

    # 执行采集
    with console.status(f"[{theme.secondary_text}]采集中...[/]"):
        result = manager.collect(
            engine=engine,
            task_config=task_config,
            output_dir=output
        )

    # 显示结果
    console.print(f"\n[{theme.info}]📊 采集结果:[/]\n")
    console.print(f"  状态: [{'green' if result.status == 'success' else 'red'}]{result.status}[/]")
    console.print(f"  引擎: {result.source_project}")
    console.print(f"  来源: {result.source_site}")
    console.print(f"  任务: {result.task_type}")
    console.print(f"  条数: {result.item_count}")

    if result.raw_file_path:
        console.print(f"  原始数据: {result.raw_file_path}")
    if result.normalized_file_path:
        console.print(f"  标准化数据: {result.normalized_file_path}")

    if result.error_message and result.status != 'success':
        console.print(f"\n[{theme.error}]错误: {result.error_message}[/]")

    # 显示数据预览
    if result.items:
        console.print(f"\n[{theme.info}]📄 数据预览 (前3条):[/]\n")
        for i, item in enumerate(result.items[:3], 1):
            console.print(f"  {i}. {item.title[:50]}..." if len(item.title) > 50 else f"  {i}. {item.title}")

    console.print()


@collect_app.command("list-engines")
def collect_list_engines():
    """列出可用的采集引擎"""
    from collectors import CollectionManager, ToolBbrowserAdapter, ScraplingAdapter

    manager = CollectionManager()
    manager.register_collector('toolbbrowser', ToolBbrowserAdapter())
    manager.register_collector('scrapling', ScraplingAdapter())

    console.print(f"\n[{theme.primary}]📦 可用采集引擎:[/]\n")

    for name in manager.list_collectors():
        collector = manager.get_collector(name)
        health = collector.health_check()

        status_icon = "✅" if health.get('cli_available') or health.get('module_available') else "⚠️"
        console.print(f"  {status_icon} {name}")

        if 'cli_available' in health:
            console.print(f"     CLI可用: {'是' if health['cli_available'] else '否'}")
        if 'module_available' in health:
            console.print(f"     模块可用: {'是' if health['module_available'] else '否'}")

    console.print()


@collect_app.command("stats")
def collect_stats():
    """显示采集统计信息"""
    from collectors import CollectionManager

    manager = CollectionManager()
    stats = manager.get_statistics()

    console.print(f"\n[{theme.primary}]📊 采集统计[/]\n")

    console.print(f"[{theme.info}]数据目录:[/]")
    for dir_name, count in stats['data_directories'].items():
        console.print(f"  {dir_name}: {count} 个文件")

    console.print()


@collect_app.command("demo")
def collect_demo():
    """运行采集演示"""
    from collectors import CollectionManager, ToolBbrowserAdapter, ScraplingAdapter

    console.print(f"\n[{theme.primary}]🎮 运行采集演示[/]\n")

    # 创建管理器
    manager = CollectionManager()

    # 注册适配器
    manager.register_collector('toolbbrowser', ToolBbrowserAdapter())
    manager.register_collector('scrapling', ScraplingAdapter())

    # 演示任务列表
    demo_tasks = [
        {
            'engine': 'toolbbrowser',
            'task_config': {
                'source_site': 'zhihu',
                'task_type': 'hot_list',
            }
        },
        {
            'engine': 'scrapling',
            'task_config': {
                'source_site': 'example',
                'task_type': 'article',
                'url': 'https://example.com',
            }
        },
    ]

    results = []
    for task in demo_tasks:
        engine = task['engine']
        task_config = task['task_config']

        console.print(f"[{theme.info}]执行: {engine} / {task_config['source_site']} / {task_config['task_type']}[/]")

        result = manager.collect(
            engine=engine,
            task_config=task_config
        )
        results.append(result)

        status_color = theme.success if result.status == 'success' else theme.error
        console.print(f"  状态: [{status_color}]{result.status}[/], 条数: {result.item_count}")
        if result.normalized_file_path:
            console.print(f"  输出: {result.normalized_file_path}")
        console.print()

    # 汇总
    success_count = sum(1 for r in results if r.status == 'success')
    console.print(f"[{theme.success}]演示完成: {success_count}/{len(results)} 个任务成功[/]")
    console.print()


@app.command()
def web(
    port: int = typer.Option(8080, "--port", "-p", help="监听端口"),
    host: str = typer.Option("127.0.0.1", "--host", "-H", help="监听地址"),
    reload: bool = typer.Option(False, "--reload", "-r", help="开发模式热重载"),
):
    """
    启动 Web UI 服务
    
    使用 FastAPI 和 pure HTML/JS/CSS 提供网页交互界面。
    """
    import uvicorn
    console.print(f"[{theme.primary}]🌐 启动 Web UI 服务 (http://{host}:{port})...[/]")
    
    # Run uvicorn with factory pattern if reload is used, else direct call
    if reload:
        uvicorn.run("web.app:create_app", host=host, port=port, reload=True, factory=True)
    else:
        from web.app import create_app
        uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    app()
