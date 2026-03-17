"""
基于图数据库的RAG系统配置文件
"""

import os
from dataclasses import dataclass
from typing import Dict, Any
from dotenv import load_dotenv

# 获取当前文件所在目录
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)

# 加载环境变量（从 config 目录下的 .env 文件）
env_path = os.path.join(CONFIG_DIR, '.env')
load_dotenv(env_path)

@dataclass
class GraphRAGConfig:
    """基于图数据库的RAG系统配置类"""

    # Neo4j数据库配置
    neo4j_uri: str = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    neo4j_database: str = os.getenv("NEO4J_DATABASE", "neo4j")

    # Milvus配置
    milvus_host: str = os.getenv("MILVUS_HOST", "localhost")
    milvus_port: int = int(os.getenv("MILVUS_PORT", "19530"))
    milvus_collection_name: str = os.getenv("MILVUS_COLLECTION_NAME", "travel_knowledge")
    milvus_dimension: int = 512  # BGE-small-zh-v1.5的向量维度

    # 模型配置
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    llm_model: str = os.getenv("LLM_MODEL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")

    # 检索配置（LightRAG Round-robin策略）
    top_k: int = int(os.getenv("TOP_K", "5"))

    # 生成配置
    temperature: float = float(os.getenv("TEMPERATURE", "0.1"))
    max_tokens: int = int(os.getenv("MAX_TOKENS", "2048"))

    # 图数据处理配置
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    max_graph_depth: int = int(os.getenv("MAX_GRAPH_DEPTH", "2"))  # 图遍历最大深度

    # 查询路由配置（轻量级优化）
    enable_llm_routing: bool = os.getenv("ENABLE_LLM_ROUTING", "false").lower() == "true"  # 是否启用LLM路由（默认关闭）
    router_cache_size: int = int(os.getenv("ROUTER_CACHE_SIZE", "1000"))  # 路由决策缓存大小

    # === 数据采集配置 ===
    # ToolBbrowser 配置
    toolbbrowser_enabled: bool = os.getenv("TOOLBBROWSER_ENABLED", "true").lower() == "true"
    toolbbrowser_path: str = os.getenv("TOOLBBROWSER_PATH", os.path.join(PROJECT_ROOT, "ToolBbrowser"))
    toolbbrowser_node_path: str = os.getenv("TOOLBBROWSER_NODE_PATH", "node")
    toolbbrowser_timeout: int = int(os.getenv("TOOLBBROWSER_TIMEOUT", "60"))

    # Scrapling 配置
    scrapling_enabled: bool = os.getenv("SCRAPLING_ENABLED", "true").lower() == "true"
    scrapling_path: str = os.getenv("SCRAPLING_PATH", os.path.join(PROJECT_ROOT, "Scrapling-main"))
    scrapling_default_fetcher: str = os.getenv("SCRAPLING_DEFAULT_FETCHER", "fetcher")
    scrapling_timeout: int = int(os.getenv("SCRAPLING_TIMEOUT", "30"))
    scrapling_retry_count: int = int(os.getenv("SCRAPLING_RETRY_COUNT", "3"))

    # 数据目录配置
    data_root: str = os.getenv("DATA_ROOT", os.path.join(PROJECT_ROOT, "data"))
    collector_save_raw: bool = os.getenv("COLLECTOR_SAVE_RAW", "true").lower() == "true"
    collector_save_normalized: bool = os.getenv("COLLECTOR_SAVE_NORMALIZED", "true").lower() == "true"

    def __post_init__(self):
        """初始化后的处理"""
        # LightRAG使用Round-robin策略，无需权重验证
        pass

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'GraphRAGConfig':
        """从字典创建配置对象"""
        return cls(**config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'neo4j_uri': self.neo4j_uri,
            'neo4j_user': self.neo4j_user,
            'neo4j_password': self.neo4j_password,
            'neo4j_database': self.neo4j_database,
            'milvus_host': self.milvus_host,
            'milvus_port': self.milvus_port,
            'milvus_collection_name': self.milvus_collection_name,
            'milvus_dimension': self.milvus_dimension,
            'embedding_model': self.embedding_model,
            'llm_model': self.llm_model,
            'top_k': self.top_k,

            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'max_graph_depth': self.max_graph_depth,
            'enable_llm_routing': self.enable_llm_routing,
            'router_cache_size': self.router_cache_size,

            # 数据采集配置
            'toolbbrowser_enabled': self.toolbbrowser_enabled,
            'scrapling_enabled': self.scrapling_enabled,
            'data_root': self.data_root,
            'collector_save_raw': self.collector_save_raw,
            'collector_save_normalized': self.collector_save_normalized,
        }

# 默认配置实例
DEFAULT_CONFIG = GraphRAGConfig()
