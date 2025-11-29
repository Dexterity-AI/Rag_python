"""
基于图数据库的RAG模块包
"""

# 尝试导入各个模块，如果失败则跳过
try:
    from .graph_data_preparation import GraphDataPreparationModule
    AVAILABLE_MODULES = ['GraphDataPreparationModule']
except ImportError:
    AVAILABLE_MODULES = []

try:
    from .milvus_index_construction import MilvusIndexConstructionModule
    AVAILABLE_MODULES.append('MilvusIndexConstructionModule')
except ImportError:
    pass

try:
    from .hybrid_retrieval import HybridRetrievalModule
    AVAILABLE_MODULES.append('HybridRetrievalModule')
except ImportError:
    pass

try:
    from .generation_integration import GenerationIntegrationModule
    AVAILABLE_MODULES.append('GenerationIntegrationModule')
except ImportError:
    pass

__all__ = AVAILABLE_MODULES