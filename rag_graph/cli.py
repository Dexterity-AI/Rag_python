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
import subprocess
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
    skip_service_check: bool = typer.Option(False, "--skip-service-check", help="跳过服务检查"),
    auto_start: bool = typer.Option(False, "--auto-start", "-a", help="服务未启动时自动启动"),
):
    """
    启动交互式 GraphRAG 助手

    这是主要的入口命令，启动后可以进行交互式问答。

    示例:
        python main.py start                    # 正常启动
        python main.py start -a                 # 自动启动基础设施服务
        python main.py start --skip-service-check  # 跳过服务检查
    """
    setup_logging(verbose, debug)

    # 显示启动信息
    console.clear()

    # 检查服务状态
    if not skip_service_check:
        console.print(f"[{theme.info}]🔍 检查基础设施服务...[/]")

        from config.config import DEFAULT_CONFIG
        neo4j_ready = check_service_health(DEFAULT_CONFIG.neo4j_uri, "neo4j")
        milvus_ready = check_service_health(
            f"{DEFAULT_CONFIG.milvus_host}:{DEFAULT_CONFIG.milvus_port}", "milvus"
        )

        if not neo4j_ready or not milvus_ready:
            console.print(f"[{theme.warning}]⚠️ 检测到服务未启动:[/]")
            if not neo4j_ready:
                console.print(f"  ❌ Neo4j (bolt://localhost:7687)")
            if not milvus_ready:
                console.print(f"  ❌ Milvus (localhost:19530)")
            console.print()

            if auto_start:
                console.print(f"[{theme.info}]🚀 自动启动基础设施服务...[/]")
                returncode, _, stderr = run_docker_compose(["up", "-d"], capture=True)
                if returncode != 0:
                    console.print(f"[{theme.error}]❌ 启动失败: {stderr}[/]")
                    raise typer.Exit(1)

                console.print(f"[{theme.success}]✅ Docker 容器已启动[/]")
                console.print(f"[{theme.info}]⏳ 等待服务就绪...[/]")

                if wait_for_services_ready():
                    console.print(f"[{theme.success}]✅ 所有服务已就绪！[/]")
                else:
                    console.print(f"[{theme.error}]❌ 服务启动超时，请检查日志[/]")
                    raise typer.Exit(1)
            else:
                console.print(f"[{theme.info}]💡 提示: 可以使用以下命令启动服务[/]")
                console.print(f"  python main.py service up")
                console.print(f"  或")
                console.print(f"  python main.py start -a   # 自动启动服务")
                console.print()

                if not typer.confirm("是否继续尝试启动？"):
                    raise typer.Exit(0)
        else:
            console.print(f"[{theme.success}]✅ 所有服务已就绪[/]")

    console.print()

    # 创建应用实例
    rag_app = GraphRAGApp(console)

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


# Service 子命令组 - 服务管理
def get_compose_file() -> str:
    """获取 docker-compose 文件路径"""
    # 从 rag_graph 目录向上找到项目根目录
    rag_graph_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(rag_graph_dir)
    return os.path.join(project_root, "config", "docker-compose.yml")


def check_docker_daemon() -> tuple:
    """
    检查 Docker 守护进程是否运行

    Returns:
        (is_running: bool, error_msg: str)
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, ""
        else:
            return False, result.stderr
    except FileNotFoundError:
        return False, "Docker 命令未找到，请确保 Docker 已安装"
    except subprocess.TimeoutExpired:
        return False, "检查 Docker 状态超时"
    except Exception as e:
        return False, str(e)


def show_docker_start_help():
    """显示 Docker 启动帮助信息"""
    console.print(f"\n[{theme.error}]❌ Docker 守护进程未运行[/]\n")
    console.print(f"[{theme.info}]💡 解决方案:[/]\n")

    # 检测操作系统
    system = sys.platform

    if system == "darwin":  # macOS
        console.print("  macOS 用户:")
        console.print("  1. 打开 Launchpad → 启动 Docker 应用")
        console.print("  2. 或运行命令: open /Applications/Docker.app")
        console.print("  3. 等待菜单栏出现 Docker 图标 🐳\n")
    elif system == "linux":
        console.print("  Linux 用户:")
        console.print("  1. 运行: sudo systemctl start docker")
        console.print("  2. 或: sudo service docker start\n")
    elif system == "win32":
        console.print("  Windows 用户:")
        console.print("  1. 从开始菜单启动 Docker Desktop")
        console.print("  2. 等待系统托盘中出现 Docker 图标\n")

    console.print(f"[{theme.secondary_text}]启动 Docker 后，请重新运行当前命令[/]\n")


def run_docker_compose(args: list, capture: bool = False) -> tuple:
    """运行 docker-compose 命令"""
    # 先检查 Docker 守护进程
    is_running, error = check_docker_daemon()
    if not is_running:
        show_docker_start_help()
        raise typer.Exit(1)

    compose_file = get_compose_file()
    cmd = ["docker-compose", "-f", compose_file] + args

    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    else:
        result = subprocess.run(cmd)
        return result.returncode, "", ""


service_app = typer.Typer(help="Docker 服务管理")
app.add_typer(service_app, name="service")


@service_app.command("up")
def service_up(
    detach: bool = typer.Option(True, "--detach", "-d", help="后台运行"),
    build: bool = typer.Option(False, "--build", "-b", help="重新构建镜像"),
    wait: bool = typer.Option(True, "--wait", "-w", help="等待服务就绪"),
):
    """
    启动所有基础设施服务 (Neo4j + Milvus)

    示例:
        python main.py service up          # 后台启动
        python main.py service up -d       # 同上
        python main.py service up --build  # 重新构建后启动
    """
    console.print(f"\n[{theme.primary}]🐳 启动基础设施服务...[/]\n")

    cmd = ["up"]
    if detach:
        cmd.append("-d")
    if build:
        cmd.append("--build")

    returncode, stdout, stderr = run_docker_compose(cmd)

    if returncode != 0:
        console.print(f"[{theme.error}]❌ 启动失败: {stderr}[/]")
        raise typer.Exit(1)

    console.print(f"[{theme.success}]✅ Docker 容器已启动[/]")
    console.print()

    # 显示服务访问信息
    console.print(f"[{theme.info}]📋 服务访问地址:[/]")
    console.print(f"  Neo4j Browser: http://localhost:7474")
    console.print(f"  Neo4j Bolt:    bolt://localhost:7687")
    console.print(f"  Milvus gRPC:   localhost:19530")
    console.print(f"  MinIO Console: http://localhost:9001")
    console.print()

    if wait:
        console.print(f"[{theme.info}]⏳ 等待服务就绪...[/]")
        if wait_for_services_ready():
            console.print(f"[{theme.success}]✅ 所有服务已就绪！[/]")
        else:
            console.print(f"[{theme.warning}]⚠️ 服务可能尚未完全就绪，请稍后再试[/]")


@service_app.command("down")
def service_down(
    volumes: bool = typer.Option(False, "--volumes", "-v", help="同时删除数据卷"),
):
    """
    停止并移除所有服务

    示例:
        python main.py service down          # 停止服务
        python main.py service down -v       # 停止并删除数据（危险！）
    """
    console.print(f"\n[{theme.primary}]🛑 停止基础设施服务...[/]\n")

    cmd = ["down"]
    if volumes:
        cmd.append("-v")
        console.print(f"[{theme.warning}]⚠️ 警告: 将同时删除数据卷！[/]")
        if not typer.confirm("确认删除？"):
            console.print("已取消")
            raise typer.Exit(0)

    returncode, _, stderr = run_docker_compose(cmd)

    if returncode != 0:
        console.print(f"[{theme.error}]❌ 停止失败: {stderr}[/]")
        raise typer.Exit(1)

    console.print(f"[{theme.success}]✅ 服务已停止[/]")


@service_app.command("status")
def service_status():
    """
    查看服务运行状态
    """
    console.print(f"\n[{theme.primary}]📊 服务状态[/]\n")

    returncode, stdout, stderr = run_docker_compose(["ps"], capture=True)

    if returncode != 0:
        console.print(f"[{theme.error}]获取状态失败: {stderr}[/]")
        raise typer.Exit(1)

    if stdout.strip():
        console.print(stdout)
    else:
        console.print(f"[{theme.secondary_text}]没有运行中的服务[/]")

    # 额外检查服务健康状态
    console.print(f"\n[{theme.info}]🔍 健康检查:[/]")

    from config.config import DEFAULT_CONFIG

    # 检查 Neo4j
    neo4j_endpoint = f"bolt://{DEFAULT_CONFIG.neo4j_uri.replace('bolt://', '').replace('neo4j://', '')}"
    neo4j_ok = check_service_health(neo4j_endpoint, service_type="neo4j")
    neo4j_status = "✅ 健康" if neo4j_ok else "❌ 未连接"
    console.print(f"  Neo4j: {neo4j_status}")

    # 检查 Milvus
    milvus_endpoint = f"{DEFAULT_CONFIG.milvus_host}:{DEFAULT_CONFIG.milvus_port}"
    milvus_ok = check_service_health(milvus_endpoint, service_type="milvus")
    milvus_status = "✅ 健康" if milvus_ok else "❌ 未连接"
    console.print(f"  Milvus: {milvus_status}")


@service_app.command("logs")
def service_logs(
    service: str = typer.Option(None, "--service", "-s", help="指定服务: neo4j, standalone, etcd, minio"),
    follow: bool = typer.Option(False, "--follow", "-f", help="持续跟踪日志"),
    tail: int = typer.Option(100, "--tail", "-n", help="显示最后 N 行"),
):
    """
    查看服务日志

    示例:
        python main.py service logs              # 查看所有服务日志
        python main.py service logs -s neo4j     # 查看 Neo4j 日志
        python main.py service logs -f           # 持续跟踪所有日志
    """
    cmd = ["logs"]

    if follow:
        cmd.append("-f")
    if tail:
        cmd.extend(["--tail", str(tail)])
    if service:
        cmd.append(service)

    # 直接运行，让用户可以 Ctrl+C 退出
    run_docker_compose(cmd)


@service_app.command("restart")
def service_restart(
    service: str = typer.Argument(..., help="服务名: neo4j, standalone, etcd, minio"),
    wait: bool = typer.Option(True, "--wait", "-w", help="等待服务就绪"),
    timeout: int = typer.Option(120, "--timeout", "-t", help="等待超时时间（秒）"),
):
    """
    重启指定服务并等待就绪

    示例:
        python main.py service restart neo4j          # 重启 Neo4j 并等待就绪
        python main.py service restart neo4j --no-wait # 重启但不等待
        python main.py service restart standalone     # 重启 Milvus
    """
    console.print(f"\n[{theme.primary}]🔄 重启服务 {service}...[/]\n")

    returncode, _, stderr = run_docker_compose(["restart", service])

    if returncode != 0:
        console.print(f"[{theme.error}]❌ 重启失败: {stderr}[/]")
        raise typer.Exit(1)

    console.print(f"[{theme.success}]✅ 服务 {service} 已重启[/]")

    # 等待服务就绪
    if wait and service in ["neo4j", "standalone"]:
        service_map = {"neo4j": "neo4j", "standalone": "milvus"}
        service_key = service_map.get(service)
        if service_key:
            console.print()
            checker = ServiceHealthChecker(console)
            success, details = checker.wait_for_service(
                service_key,
                timeout=timeout,
                verbose=True
            )
            if not success:
                raise typer.Exit(1)


@service_app.command("wait")
def service_wait(
    service: str = typer.Argument(None, help="服务名: neo4j, milvus，不指定则等待所有"),
    timeout: int = typer.Option(180, "--timeout", "-t", help="等待超时时间（秒）"),
    verbose: bool = typer.Option(True, "--verbose", "-v", help="详细输出"),
):
    """
    等待服务就绪

    示例:
        python main.py service wait              # 等待所有服务就绪
        python main.py service wait neo4j        # 只等待 Neo4j
        python main.py service wait milvus -t 60 # 等待 Milvus，超时60秒
    """
    checker = ServiceHealthChecker(console)

    if service:
        # 等待单个服务
        success, details = checker.wait_for_service(
            service,
            timeout=timeout,
            verbose=verbose
        )
        if not success:
            raise typer.Exit(1)
    else:
        # 等待所有服务
        results = checker.wait_for_all(
            timeout=timeout,
            verbose=verbose
        )
        if not results["success"]:
            raise typer.Exit(1)


class ServiceHealthChecker:
    """服务健康检查器 - 支持详细进度显示和错误诊断"""

    SERVICES = {
        "neo4j": {
            "name": "Neo4j",
            "type": "neo4j",
            "docker_name": "rag-neo4j",
            "check_interval": 2,
            "start_time": 15,  # 预计启动时间（秒）
        },
        "milvus": {
            "name": "Milvus",
            "type": "milvus",
            "docker_name": "milvus-standalone",
            "check_interval": 3,
            "start_time": 30,
        },
    }

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.theme = get_theme()
        # 从配置加载端点地址
        from config.config import DEFAULT_CONFIG
        self.config = DEFAULT_CONFIG

    def _get_endpoint(self, service_name: str) -> str:
        """获取服务端点地址（从配置动态构建）"""
        if service_name == "neo4j":
            return self.config.neo4j_uri
        elif service_name == "milvus":
            return f"{self.config.milvus_host}:{self.config.milvus_port}"
        return ""

    def check(self, service_name: str, verbose: bool = False) -> tuple:
        """
        检查单个服务健康状态

        Returns:
            (is_healthy: bool, error_msg: str, details: dict)
        """
        service_config = self.SERVICES.get(service_name.lower())
        if not service_config:
            return False, f"未知服务: {service_name}", {}

        try:
            if service_config["type"] == "neo4j":
                return self._check_neo4j(service_config, verbose)
            elif service_config["type"] == "milvus":
                return self._check_milvus(service_config, verbose)
        except Exception as e:
            error_msg = str(e)
            if verbose:
                self.console.print(f"[{self.theme.error}]  检查异常: {error_msg}[/]")
            return False, error_msg, {}

        return False, "未知服务类型", {}

    def _check_neo4j(self, config: dict, verbose: bool) -> tuple:
        """检查 Neo4j 健康状态"""
        from neo4j import GraphDatabase

        try:
            driver = GraphDatabase.driver(
                self.config.neo4j_uri,
                auth=(self.config.neo4j_user, self.config.neo4j_password)
            )
            driver.verify_connectivity()

            # 获取数据库信息
            with driver.session() as session:
                result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions[0] as version")
                components = [{"name": record["name"], "version": record["version"]} for record in result]

            driver.close()

            details = {
                "endpoint": self.config.neo4j_uri,
                "components": components,
            }
            return True, "", details

        except Exception as e:
            error_msg = self._diagnose_neo4j_error(str(e))
            return False, error_msg, {}

    def _check_milvus(self, config: dict, verbose: bool) -> tuple:
        """检查 Milvus 健康状态"""
        from pymilvus import connections, utility

        try:
            connections.connect(
                alias="health_check",
                host=self.config.milvus_host,
                port=self.config.milvus_port
            )

            # 获取服务器版本
            version = utility.get_server_version()

            # 获取集合数量
            collections = utility.list_collections()

            connections.disconnect("health_check")

            details = {
                "endpoint": f"{self.config.milvus_host}:{self.config.milvus_port}",
                "version": version,
                "collections": len(collections),
            }
            return True, "", details

        except Exception as e:
            error_msg = self._diagnose_milvus_error(str(e))
            return False, error_msg, {}

    def _diagnose_neo4j_error(self, error: str) -> str:
        """诊断 Neo4j 错误并给出友好提示"""
        if "Failed to establish connection" in error or "Connection refused" in error:
            return "无法连接到 Neo4j，请检查服务是否已启动 (python main.py service up)"
        elif "Unauthorized" in error or "Authentication" in error:
            return "认证失败，请检查 config/.env 中的 NEO4J_USER 和 NEO4J_PASSWORD"
        elif "ServiceUnavailable" in error:
            return "Neo4j 服务不可用，可能正在启动中，请稍后再试"
        return f"连接错误: {error}"

    def _diagnose_milvus_error(self, error: str) -> str:
        """诊断 Milvus 错误并给出友好提示"""
        if "failed to connect" in error.lower() or "connection refused" in error.lower():
            return "无法连接到 Milvus，请检查服务是否已启动 (python main.py service up)"
        elif "timeout" in error.lower():
            return "连接 Milvus 超时，服务可能仍在启动中"
        return f"连接错误: {error}"

    def wait_for_service(
        self,
        service_name: str,
        timeout: int = 120,
        verbose: bool = True,
        progress_callback=None
    ) -> tuple:
        """
        等待单个服务就绪

        Returns:
            (success: bool, details: dict)
        """
        service_config = self.SERVICES.get(service_name.lower())
        if not service_config:
            return False, {"error": f"未知服务: {service_name}"}

        import time

        start_time = time.time()
        check_count = 0
        last_error = ""

        if verbose:
            self.console.print(f"[{self.theme.info}]⏳ 等待 {service_config['name']} 就绪...[/]")

        while time.time() - start_time < timeout:
            check_count += 1
            is_healthy, error_msg, details = self.check(service_name, verbose=False)

            if is_healthy:
                elapsed = time.time() - start_time
                if verbose:
                    self.console.print(f"[{self.theme.success}]  ✅ {service_config['name']} 已就绪 (耗时 {elapsed:.1f}s)[/]")
                    if details:
                        if "version" in details:
                            self.console.print(f"[{self.theme.secondary_text}]     版本: {details['version']}[/]")
                        if "collections" in details:
                            self.console.print(f"[{self.theme.secondary_text}]     集合数: {details['collections']}[/]")
                return True, details

            if error_msg and error_msg != last_error and verbose:
                self.console.print(f"[{self.theme.warning}]  尝试 {check_count}: {error_msg}[/]")
                last_error = error_msg

            if progress_callback:
                progress_callback(check_count, timeout // service_config["check_interval"])

            time.sleep(service_config["check_interval"])

        # 超时
        elapsed = time.time() - start_time
        error = f"等待 {service_config['name']} 超时 ({elapsed:.1f}s > {timeout}s)"
        if verbose:
            self.console.print(f"[{self.theme.error}]  ❌ {error}[/]")
            self.console.print(f"[{self.theme.info}]💡 建议: 查看日志 python main.py service logs -s {service_config['docker_name']}[/]")

        return False, {"error": error, "last_error": last_error}

    def wait_for_all(
        self,
        services: list = None,
        timeout: int = 180,
        verbose: bool = True,
        parallel: bool = False
    ) -> dict:
        """
        等待多个服务就绪

        Args:
            services: 服务列表，None 表示所有服务
            timeout: 总超时时间
            verbose: 是否显示详细输出
            parallel: 是否并行检查（默认顺序检查）

        Returns:
            {
                "success": bool,
                "services": {
                    "neo4j": {"ready": bool, "details": dict, "elapsed": float},
                    "milvus": {...}
                },
                "total_elapsed": float
            }
        """
        import time

        if services is None:
            services = list(self.SERVICES.keys())

        start_time = time.time()
        results = {"success": True, "services": {}, "total_elapsed": 0}

        if verbose:
            self.console.print(f"\n[{self.theme.primary}]🚀 等待基础设施服务就绪...[/]\n")

        for service_name in services:
            service_start = time.time()
            success, details = self.wait_for_service(
                service_name,
                timeout=timeout,
                verbose=verbose
            )
            elapsed = time.time() - service_start

            results["services"][service_name] = {
                "ready": success,
                "details": details,
                "elapsed": elapsed
            }

            if not success:
                results["success"] = False

        results["total_elapsed"] = time.time() - start_time

        if verbose:
            if results["success"]:
                self.console.print(f"\n[{self.theme.success}]✅ 所有服务已就绪 (总耗时 {results['total_elapsed']:.1f}s)[/]")
            else:
                failed = [name for name, r in results["services"].items() if not r["ready"]]
                self.console.print(f"\n[{self.theme.error}]❌ 部分服务未就绪: {', '.join(failed)}[/]")

        return results


def check_service_health(endpoint: str, service_type: str = "neo4j") -> bool:
    """检查单个服务健康状态（简化版，兼容旧代码）"""
    checker = ServiceHealthChecker()
    service_map = {
        "neo4j": "neo4j",
        "milvus": "milvus"
    }
    service_name = service_map.get(service_type)
    if not service_name:
        return False

    is_healthy, _, _ = checker.check(service_name, verbose=False)
    return is_healthy


def wait_for_services_ready(timeout: int = 120) -> bool:
    """等待所有服务就绪（兼容旧代码）"""
    checker = ServiceHealthChecker(console)
    results = checker.wait_for_all(timeout=timeout, verbose=True)
    return results["success"]


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
