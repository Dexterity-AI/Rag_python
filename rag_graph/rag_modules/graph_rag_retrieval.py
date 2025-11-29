"""
图RAG的检索模块
基于图结构的知识推理和检索，而非简单的关键词匹配
"""

import json
import logging
from collections import defaultdict, deque
from typing import List, Dict, Tuple, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from langchain_core.documents import Document
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """查询类型枚举"""
    ENTITY_RELATION = "entity_relation"  # 实体关系查询：A和B有什么关系？
    MULTI_HOP = "multi_hop"  # 多跳查询：A通过什么连接到C？
    SUBGRAPH = "subgraph"  # 子图查询：A相关的所有信息
    PATH_FINDING = "path_finding"  # 路径查找：从A到B的最佳路径
    CLUSTERING = "clustering"  # 聚类查询：和A相似的都有什么？

@dataclass
class GraphQuery:
    """图查询结构"""
    query_type: QueryType
    source_entities: List[str]
    target_entities: List[str] = None
    relation_types: List[str] = None
    max_depth: int = 2
    max_nodes: int = 50
    constraints: Dict[str, Any] = None

@dataclass
class GraphPath:
    """图路径结构"""
    nodes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    path_length: int
    relevance_score: float
    path_type: str

@dataclass
class KnowledgeSubgraph:
    """知识子图结构"""
    central_nodes: List[Dict[str, Any]]
    connected_nodes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    graph_metrics: Dict[str, float]
    reasoning_chains: List[List[str]]

class GraphRAGRetrieval:
    """
    真正的图RAG检索系统
    核心特点：
    1. 查询意图理解：识别图查询模式
    2. 多跳图遍历：深度关系探索
    3. 子图提取：相关知识网络
    4. 图结构推理：基于拓扑的推理
    5. 动态查询规划：自适应遍历策略
    """
    
    def __init__(self, config, llm_client):
        self.config = config
        self.llm_client = llm_client
        self.driver = None
        
        # 图结构缓存
        self.entity_cache = {}
        self.relation_cache = {}
        self.subgraph_cache = {}
        
    def initialize(self):
        """初始化图RAG检索系统"""
        logger.info("初始化图RAG检索系统...")
        
        # 连接Neo4j
        try:
            self.driver = GraphDatabase.driver(
                self.config.neo4j_uri, 
                auth=(self.config.neo4j_user, self.config.neo4j_password)
            )
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Neo4j连接成功")
        except Exception as e:
            logger.error(f"Neo4j连接失败: {e}")
            return
        
        # 预热：构建实体和关系索引
        self._build_graph_index()
        
    def _build_graph_index(self):
        """构建图索引以加速查询"""
        logger.info("构建图结构索引...")
        
        try:
            with self.driver.session() as session:
                # 构建实体索引 - 修复Neo4j语法兼容性问题
                entity_query = """
                MATCH (n)
                WHERE n.id IS NOT NULL
                WITH n, size((n)--()) as degree
                RETURN labels(n) as node_labels, n.id as node_id,
                       n.name as name, n.category as category, degree
                ORDER BY degree DESC
                LIMIT 1000
                """
                
                result = session.run(entity_query)
                for record in result:
                    node_id = record["node_id"]
                    self.entity_cache[node_id] = {
                        "labels": record["node_labels"],
                        "name": record["name"],
                        "category": record["category"],
                        "degree": record["degree"]
                    }
                
                # 构建关系类型索引
                relation_query = """
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(r) as frequency
                ORDER BY frequency DESC
                """
                
                result = session.run(relation_query)
                for record in result:
                    rel_type = record["rel_type"]
                    self.relation_cache[rel_type] = record["frequency"]
                    
                logger.info(f"索引构建完成: {len(self.entity_cache)}个实体, {len(self.relation_cache)}个关系类型")
                
        except Exception as e:
            logger.error(f"构建图索引失败: {e}")
    
    def understand_graph_query(self, query: str) -> GraphQuery:
        """
        理解查询的图结构意图
        这是图RAG的核心：从自然语言到图查询的转换
        """
        prompt = f"""
        作为图数据库专家，分析以下查询的图结构意图：
        
        查询：{query}
        
        请识别：
        1. 查询类型：
           - entity_relation: 询问实体间的直接关系（如：鸡肉和胡萝卜能一起做菜吗？）
           - multi_hop: 需要多跳推理（如：鸡肉配什么蔬菜？需要：鸡肉→菜品→食材→蔬菜）
           - subgraph: 需要完整子图（如：川菜有什么特色？需要川菜相关的完整知识网络）
           - path_finding: 路径查找（如：从食材到成品菜的制作路径）
           - clustering: 聚类相似性（如：和宫保鸡丁类似的菜有哪些？）
        
        2. 核心实体：查询中的关键实体名称
        3. 目标实体：期望找到的实体类型
        4. 关系类型：涉及的关系类型
        5. 遍历深度：需要的图遍历深度（1-3跳）
        
        示例：
        查询："鸡肉配什么蔬菜好？"
        分析：这是multi_hop查询，需要通过"鸡肉→使用鸡肉的菜品→这些菜品使用的蔬菜"的路径推理
        
        返回JSON格式：
        {{
            "query_type": "multi_hop",
            "source_entities": ["鸡肉"],
            "target_entities": ["蔬菜类食材"],
            "relation_types": ["REQUIRES", "BELONGS_TO_CATEGORY"],
            "max_depth": 3,
            "reasoning": "需要多跳推理：鸡肉→菜品→食材→蔬菜"
        }}
        """
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.config.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            
            return GraphQuery(
                query_type=QueryType(result.get("query_type", "subgraph")),
                source_entities=result.get("source_entities", []),
                target_entities=result.get("target_entities", []),
                relation_types=result.get("relation_types", []),
                max_depth=result.get("max_depth", 2),
                max_nodes=50
            )
            
        except Exception as e:
            logger.error(f"查询意图理解失败: {e}")
            # 降级方案：默认子图查询
            return GraphQuery(
                query_type=QueryType.SUBGRAPH,
                source_entities=[query],
                max_depth=2
            )
    
    def multi_hop_traversal(self, graph_query: GraphQuery) -> List[GraphPath]:
        """
        多跳图遍历：这是图RAG的核心优势
        通过图结构发现隐含的知识关联
        """
        logger.info(f"执行多跳遍历: {graph_query.source_entities} -> {graph_query.target_entities}")
        
        paths = []
        
        if not self.driver:
            logger.error("Neo4j连接未建立")
            return paths
            
        try:
            with self.driver.session() as session:
                # 构建多跳遍历查询
                source_entities = graph_query.source_entities
                target_entities = graph_query.target_entities or []
                max_depth = graph_query.max_depth
                
                # 根据查询类型选择不同的遍历策略
                if graph_query.query_type == QueryType.MULTI_HOP:
                    cypher_query = f"""
                    // 多跳推理查询
                    UNWIND $source_entities as source_name
                    MATCH (source)
                    WHERE source.name CONTAINS source_name OR source.id = source_name

                    // 执行多跳遍历
                    MATCH path = (source)-[*1..{max_depth}]-(target)
                    WHERE NOT source = target
                    {"AND ANY(label IN labels(target) WHERE label IN $target_labels)" if target_entities else ""}

                    // 计算路径相关性
                    WITH path, source, target,
                         length(path) as path_len,
                         relationships(path) as rels,
                         nodes(path) as path_nodes

                    // 路径评分：短路径 + 高度数节点 + 关系类型匹配
                    WITH path, source, target, path_len, rels, path_nodes,
                         (1.0 / path_len) +
                         (REDUCE(s = 0.0, n IN path_nodes | s + size((n)--())) / 10.0 / size(path_nodes)) +
                         (CASE WHEN ANY(r IN rels WHERE type(r) IN $relation_types) THEN 0.3 ELSE 0.0 END) as relevance

                    ORDER BY relevance DESC
                    LIMIT 20

                    RETURN path, source, target, path_len, rels, path_nodes, relevance
                    """
                    
                    result = session.run(cypher_query, {
                        "source_entities": source_entities,
                        "target_labels": target_entities,
                        "relation_types": graph_query.relation_types or []
                    })
                    
                    for record in result:
                        path_data = self._parse_neo4j_path(record)
                        if path_data:
                            paths.append(path_data)
                
                elif graph_query.query_type == QueryType.ENTITY_RELATION:
                    # 实体间关系查询
                    paths.extend(self._find_entity_relations(graph_query, session))
                
                elif graph_query.query_type == QueryType.PATH_FINDING:
                    # 最短路径查找
                    paths.extend(self._find_shortest_paths(graph_query, session))
                    
        except Exception as e:
            logger.error(f"多跳遍历失败: {e}")
            
        logger.info(f"多跳遍历完成，找到 {len(paths)} 条路径")
        return paths
    
    def extract_knowledge_subgraph(self, graph_query: GraphQuery) -> KnowledgeSubgraph:
        """
        提取知识子图：获取实体相关的完整知识网络
        这体现了图RAG的整体性思维
        """
        logger.info(f"提取知识子图: {graph_query.source_entities}")
        
        if not self.driver:
            logger.error("Neo4j连接未建立")
            return self._fallback_subgraph_extraction(graph_query)
        
        try:
            with self.driver.session() as session:
                # 简化的子图提取（不依赖APOC）
                cypher_query = f"""
                // 找到源实体
                UNWIND $source_entities as entity_name
                MATCH (source)
                WHERE source.name CONTAINS entity_name
                   OR source.id = entity_name
                
                // 获取指定深度的邻居
                MATCH (source)-[r*1..{graph_query.max_depth}]-(neighbor)
                WITH source, collect(DISTINCT neighbor) as neighbors, 
                     collect(DISTINCT r) as relationships
                WHERE size(neighbors) <= $max_nodes
                
                // 计算图指标
                WITH source, neighbors, relationships,
                     size(neighbors) as node_count,
                     size(relationships) as rel_count
                
                RETURN 
                    source,
                    neighbors[0..{graph_query.max_nodes}] as nodes,
                    relationships[0..{graph_query.max_nodes}] as rels,
                    {{
                        node_count: node_count,
                        relationship_count: rel_count,
                        density: CASE WHEN node_count > 1 THEN toFloat(rel_count) / (node_count * (node_count - 1) / 2) ELSE 0.0 END
                    }} as metrics
                """
                
                result = session.run(cypher_query, {
                    "source_entities": graph_query.source_entities,
                    "max_nodes": graph_query.max_nodes
                })
                
                record = result.single()
                if record:
                    return self._build_knowledge_subgraph(record)
                    
        except Exception as e:
            logger.error(f"子图提取失败: {e}")
            
        # 降级方案：简单邻居查询
        return self._fallback_subgraph_extraction(graph_query)
    
    def graph_structure_reasoning(self, subgraph: KnowledgeSubgraph, query: str) -> List[str]:
        """
        基于图结构的推理：这是图RAG的智能之处
        不仅检索信息，还能进行逻辑推理
        """
        reasoning_chains = []
        
        try:
            # 1. 识别推理模式
            reasoning_patterns = self._identify_reasoning_patterns(subgraph)
            
            # 2. 构建推理链
            for pattern in reasoning_patterns:
                chain = self._build_reasoning_chain(pattern, subgraph)
                if chain:
                    reasoning_chains.append(chain)
            
            # 3. 验证推理链的可信度
            validated_chains = self._validate_reasoning_chains(reasoning_chains, query)
            
            logger.info(f"图结构推理完成，生成 {len(validated_chains)} 条推理链")
            return validated_chains
            
        except Exception as e:
            logger.error(f"图结构推理失败: {e}")
            return []
    
    def adaptive_query_planning(self, query: str) -> List[GraphQuery]:
        """
        自适应查询规划：根据查询复杂度动态调整策略
        """
        # 分析查询复杂度
        complexity_score = self._analyze_query_complexity(query)
        
        query_plans = []
        
        if complexity_score < 0.3:
            # 简单查询：直接邻居查询
            plan = GraphQuery(
                query_type=QueryType.ENTITY_RELATION,
                source_entities=[query],
                max_depth=1,
                max_nodes=20
            )
            query_plans.append(plan)
            
        elif complexity_score < 0.7:
            # 中等复杂度：多跳查询
            plan = GraphQuery(
                query_type=QueryType.MULTI_HOP,
                source_entities=[query],
                max_depth=2,
                max_nodes=50
            )
            query_plans.append(plan)
            
        else:
            # 复杂查询：子图提取 + 推理
            plan1 = GraphQuery(
                query_type=QueryType.SUBGRAPH,
                source_entities=[query],
                max_depth=3,
                max_nodes=100
            )
            plan2 = GraphQuery(
                query_type=QueryType.MULTI_HOP,
                source_entities=[query],
                max_depth=3,
                max_nodes=50
            )
            query_plans.extend([plan1, plan2])
            
        return query_plans
    
    def graph_rag_search(self, query: str, top_k: int = 5) -> List[Document]:
        """
        图RAG主搜索接口：整合所有图RAG能力
        """
        logger.info(f"开始图RAG检索: {query}")
        
        if not self.driver:
            logger.warning("Neo4j连接未建立，返回空结果")
            return []
        
        # 1. 查询意图理解
        graph_query = self.understand_graph_query(query)
        logger.info(f"查询类型: {graph_query.query_type.value}")
        
        results = []
        
        try:
            # 2. 根据查询类型执行不同策略
            if graph_query.query_type in [QueryType.MULTI_HOP, QueryType.PATH_FINDING]:
                # 多跳遍历
                paths = self.multi_hop_traversal(graph_query)
                results.extend(self._paths_to_documents(paths, query))
                
            elif graph_query.query_type == QueryType.SUBGRAPH:
                # 子图提取
                subgraph = self.extract_knowledge_subgraph(graph_query)
                
                # 图结构推理
                reasoning_chains = self.graph_structure_reasoning(subgraph, query)
                
                results.extend(self._subgraph_to_documents(subgraph, reasoning_chains, query))
                
            elif graph_query.query_type == QueryType.ENTITY_RELATION:
                # 实体关系查询
                paths = self.multi_hop_traversal(graph_query)
                results.extend(self._paths_to_documents(paths, query))
            
            # 3. 图结构相关性排序
            results = self._rank_by_graph_relevance(results, query)
            
            logger.info(f"图RAG检索完成，返回 {len(results[:top_k])} 个结果")
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"图RAG检索失败: {e}")
            return []
    
    # ========== 辅助方法 ==========
    
    def _parse_neo4j_path(self, record) -> Optional[GraphPath]:
        """解析Neo4j路径记录"""
        try:
            path_nodes = []
            for node in record["path_nodes"]:
                path_nodes.append({
                    "id": node.get("nodeId", ""),
                    "name": node.get("name", ""),
                    "labels": list(node.labels),
                    "properties": dict(node)
                })
            
            relationships = []
            for rel in record["rels"]:
                relationships.append({
                    "type": type(rel).__name__,
                    "properties": dict(rel)
                })
            
            return GraphPath(
                nodes=path_nodes,
                relationships=relationships,
                path_length=record["path_len"],
                relevance_score=record["relevance"],
                path_type="multi_hop"
            )
            
        except Exception as e:
            logger.error(f"路径解析失败: {e}")
            return None
    
    def _build_knowledge_subgraph(self, record) -> KnowledgeSubgraph:
        """构建知识子图对象"""
        try:
            central_nodes = [dict(record["source"])]
            connected_nodes = [dict(node) for node in record["nodes"]]
            relationships = [dict(rel) for rel in record["rels"]]
            
            return KnowledgeSubgraph(
                central_nodes=central_nodes,
                connected_nodes=connected_nodes,
                relationships=relationships,
                graph_metrics=record["metrics"],
                reasoning_chains=[]
            )
        except Exception as e:
            logger.error(f"构建知识子图失败: {e}")
            return KnowledgeSubgraph(
                central_nodes=[],
                connected_nodes=[],
                relationships=[],
                graph_metrics={},
                reasoning_chains=[]
            )
    
    def _paths_to_documents(self, paths: List[GraphPath], query: str) -> List[Document]:
        """将图路径转换为Document对象"""
        documents = []
        
        for i, path in enumerate(paths):
            # 构建路径描述
            path_desc = self._build_path_description(path)
            
            doc = Document(
                page_content=path_desc,
                metadata={
                    "search_type": "graph_path",
                    "path_length": path.path_length,
                    "relevance_score": path.relevance_score,
                    "path_type": path.path_type,
                    "node_count": len(path.nodes),
                    "relationship_count": len(path.relationships),
                    "recipe_name": path.nodes[0].get("name", "图结构结果") if path.nodes else "图结构结果"
                }
            )
            documents.append(doc)
            
        return documents
    
    def _subgraph_to_documents(self, subgraph: KnowledgeSubgraph, 
                              reasoning_chains: List[str], query: str) -> List[Document]:
        """将知识子图转换为Document对象"""
        documents = []
        
        # 子图整体描述
        subgraph_desc = self._build_subgraph_description(subgraph)
        
        doc = Document(
            page_content=subgraph_desc,
            metadata={
                "search_type": "knowledge_subgraph",
                "node_count": len(subgraph.connected_nodes),
                "relationship_count": len(subgraph.relationships),
                "graph_density": subgraph.graph_metrics.get("density", 0.0),
                "reasoning_chains": reasoning_chains,
                "recipe_name": subgraph.central_nodes[0].get("name", "知识子图") if subgraph.central_nodes else "知识子图"
            }
        )
        documents.append(doc)
        
        return documents
    
    def _build_path_description(self, path: GraphPath) -> str:
        """构建路径的自然语言描述"""
        if not path.nodes:
            return "空路径"
            
        desc_parts = []
        for i, node in enumerate(path.nodes):
            desc_parts.append(node.get("name", f"节点{i}"))
            if i < len(path.relationships):
                rel_type = path.relationships[i].get("type", "相关")
                desc_parts.append(f" --{rel_type}--> ")
        
        return "".join(desc_parts)
    
    def _build_subgraph_description(self, subgraph: KnowledgeSubgraph) -> str:
        """构建子图的自然语言描述"""
        central_names = [node.get("name", "未知") for node in subgraph.central_nodes]
        node_count = len(subgraph.connected_nodes)
        rel_count = len(subgraph.relationships)
        
        return f"关于 {', '.join(central_names)} 的知识网络，包含 {node_count} 个相关概念和 {rel_count} 个关系。"
    
    def _rank_by_graph_relevance(self, documents: List[Document], query: str) -> List[Document]:
        """基于图结构相关性排序"""
        return sorted(documents, 
                     key=lambda x: x.metadata.get("relevance_score", 0.0), 
                     reverse=True)
    
    def _analyze_query_complexity(self, query: str) -> float:
        """分析查询复杂度"""
        complexity_indicators = ["什么", "如何", "为什么", "哪些", "关系", "影响", "原因"]
        score = sum(1 for indicator in complexity_indicators if indicator in query)
        return min(score / len(complexity_indicators), 1.0)
    
    def _identify_reasoning_patterns(self, subgraph: KnowledgeSubgraph) -> List[str]:
        """识别推理模式 - 针对旅游领域优化"""
        patterns = []

        try:
            # 分析子图中的节点类型
            node_types = set()
            relationship_types = set()

            for node in subgraph.central_nodes + subgraph.connected_nodes:
                if 'labels' in node:
                    node_types.update(node['labels'])

            for rel in subgraph.relationships:
                if isinstance(rel, dict) and 'type' in rel:
                    relationship_types.add(rel['type'])

            # 基于旅游领域的推理模式
            if 'City' in node_types or 'Region' in node_types:
                patterns.append("地理位置推理")

            if 'Attraction' in node_types:
                patterns.append("旅游景点相关性推理")

            if any(rel_type in ['HAS_ATTRACTION', 'HAS_FOOD', 'HAS_HOTEL'] for rel_type in relationship_types):
                patterns.append("旅游配套服务推理")

            if 'NEARBY' in relationship_types:
                patterns.append("空间邻近性推理")

            if 'Food' in node_types or 'Restaurant' in node_types:
                patterns.append("美食文化推理")

            if 'Hotel' in node_types:
                patterns.append("住宿便利性推理")

            if 'Festival' in node_types:
                patterns.append("节庆时间推理")

            # 默认推理模式
            if not patterns:
                patterns = ["旅游主题关联推理", "相似性推理"]

        except Exception as e:
            logger.error(f"推理模式识别失败: {e}")
            patterns = ["基本关联推理"]

        return patterns

    def _build_reasoning_chain(self, pattern: str, subgraph: KnowledgeSubgraph) -> Optional[str]:
        """构建推理链 - 针对旅游领域优化"""
        try:
            # 根据推理模式构建具体的推理链
            if pattern == "地理位置推理":
                return self._build_geographic_reasoning(subgraph)
            elif pattern == "旅游景点相关性推理":
                return self._build_attraction_reasoning(subgraph)
            elif pattern == "旅游配套服务推理":
                return self._build_service_reasoning(subgraph)
            elif pattern == "空间邻近性推理":
                return self._build_spatial_reasoning(subgraph)
            elif pattern == "美食文化推理":
                return self._build_food_reasoning(subgraph)
            elif pattern == "住宿便利性推理":
                return self._build_accommodation_reasoning(subgraph)
            elif pattern == "节庆时间推理":
                return self._build_festival_reasoning(subgraph)
            else:
                return f"基于{pattern}的旅游推理链"

        except Exception as e:
            logger.error(f"推理链构建失败: {e}")
            return None

    def _build_geographic_reasoning(self, subgraph: KnowledgeSubgraph) -> str:
        """构建地理位置推理链"""
        locations = []
        regions = []

        for node in subgraph.central_nodes + subgraph.connected_nodes:
            if isinstance(node, dict):
                labels = node.get('labels', [])
                if 'City' in labels:
                    locations.append(node.get('name', '未知城市'))
                elif 'Region' in labels or 'SubRegion' in labels:
                    regions.append(node.get('name', '未知地区'))

        if locations and regions:
            return f"地理位置推理：{', '.join(locations)}位于{', '.join(regions)}，形成区域旅游集群"
        elif len(locations) > 1:
            return f"地理位置推理：{', '.join(locations)}之间存在地理关联性，可规划旅游路线"
        else:
            return f"地理位置推理：基于地理位置的旅游规划建议"

    def _build_attraction_reasoning(self, subgraph: KnowledgeSubgraph) -> str:
        """构建旅游景点相关性推理链"""
        attractions = []
        categories = set()

        for node in subgraph.central_nodes + subgraph.connected_nodes:
            if isinstance(node, dict):
                labels = node.get('labels', [])
                if 'Attraction' in labels:
                    attractions.append(node.get('name', '未知景点'))
                    if 'category' in node:
                        categories.add(node['category'])

        reasoning = f"景点相关性推理：{', '.join(attractions)}"
        if categories:
            reasoning += f"都属于{', '.join(categories)}类型，"
        reasoning += "适合同类主题的旅游体验"

        return reasoning

    def _build_service_reasoning(self, subgraph: KnowledgeSubgraph) -> str:
        """构建旅游配套服务推理链"""
        services = {'餐饮': [], '住宿': [], '购物': [], '交通': []}

        for node in subgraph.central_nodes + subgraph.connected_nodes:
            if isinstance(node, dict):
                labels = node.get('labels', [])
                if 'Food' in labels or 'Restaurant' in labels:
                    services['餐饮'].append(node.get('name', '未知餐饮'))
                elif 'Hotel' in labels:
                    services['住宿'].append(node.get('name', '未知住宿'))
                # 可以根据需要扩展其他服务类型

        service_desc = []
        for service_type, items in services.items():
            if items:
                service_desc.append(f"{service_type}({len(items)}项)")

        return f"旅游配套推理：该目的地提供{', '.join(service_desc)}，旅游服务设施完善"

    def _build_spatial_reasoning(self, subgraph: KnowledgeSubgraph) -> str:
        """构建空间邻近性推理链"""
        nearby_pairs = []

        for rel in subgraph.relationships:
            if isinstance(rel, dict) and rel.get('type') == 'NEARBY':
                nearby_pairs.append(f"邻近区域")

        if nearby_pairs:
            return f"空间邻近性推理：存在{len(nearby_pairs)}组邻近关系，适合步行游览或短途出行"
        else:
            return "空间邻近性推理：基于空间位置安排旅游行程"

    def _build_food_reasoning(self, subgraph: KnowledgeSubgraph) -> str:
        """构建美食文化推理链"""
        foods = []
        restaurants = []

        for node in subgraph.central_nodes + subgraph.connected_nodes:
            if isinstance(node, dict):
                labels = node.get('labels', [])
                if 'Food' in labels:
                    foods.append(node.get('name', '未知美食'))
                elif 'Restaurant' in labels:
                    restaurants.append(node.get('name', '未知餐厅'))

        reasoning = "美食文化推理："
        if foods:
            reasoning += f"特色美食包括{', '.join(foods)}"
        if restaurants:
            if foods:
                reasoning += f"，推荐餐厅有{', '.join(restaurants)}"
            else:
                reasoning += f"推荐餐厅有{', '.join(restaurants)}"
        reasoning += "，体现当地饮食文化特色"

        return reasoning

    def _build_accommodation_reasoning(self, subgraph: KnowledgeSubgraph) -> str:
        """构建住宿便利性推理链"""
        hotels = []

        for node in subgraph.central_nodes + subgraph.connected_nodes:
            if isinstance(node, dict) and 'Hotel' in node.get('labels', []):
                hotels.append(node.get('name', '未知酒店'))

        if hotels:
            return f"住宿便利性推理：提供{', '.join(hotels)}等住宿选择，满足不同层次需求"
        else:
            return "住宿便利性推理：基于住宿需求安排旅游行程"

    def _build_festival_reasoning(self, subgraph: KnowledgeSubgraph) -> str:
        """构建节庆时间推理链"""
        festivals = []

        for node in subgraph.central_nodes + subgraph.connected_nodes:
            if isinstance(node, dict) and 'Festival' in node.get('labels', []):
                festival_name = node.get('name', '未知节庆')
                festival_time = node.get('time', '时间待定')
                festivals.append(f"{festival_name}({festival_time})")

        if festivals:
            return f"节庆时间推理：最佳旅游时间为{', '.join(festivals)}期间，体验当地特色文化"
        else:
            return "节庆时间推理：考虑当地节庆活动安排旅游时间"

    def _validate_reasoning_chains(self, chains: List[str], query: str) -> List[str]:
        """验证推理链 - 针对旅游领域优化"""
        validated_chains = []

        # 旅游关键词集合
        tourism_keywords = {
            '旅游', '景点', '酒店', '美食', '餐厅', '交通', '路线',
            '门票', '开放时间', '地址', '推荐', '攻略', '体验',
            '文化', '历史', '自然', '风光', '住宿', '购物'
        }

        # 验证推理链与查询的相关性
        query_lower = query.lower()
        for chain in chains:
            # 检查推理链是否包含旅游相关内容
            chain_lower = chain.lower()
            relevance_score = 0

            for keyword in tourism_keywords:
                if keyword in query_lower and keyword in chain_lower:
                    relevance_score += 2
                elif keyword in chain_lower:
                    relevance_score += 1

            # 选择相关性高的推理链
            if relevance_score >= 2 or len(chains) <= 3:
                validated_chains.append(chain)

        # 如果验证通过的链太少，返回前几个
        if len(validated_chains) < 2 and chains:
            validated_chains = chains[:2]

        return validated_chains[:3]  # 最多返回3条推理链
    
    def _find_entity_relations(self, graph_query: GraphQuery, session) -> List[GraphPath]:
        """查找实体间关系"""
        paths = []

        try:
            # 旅游场景的实体关系查询
            cypher_query = """
            UNWIND $source_entities as source_name
            MATCH (source)
            WHERE source.name CONTAINS source_name OR source.id = source_name

            // 查找直接关系
            MATCH (source)-[r]-(target)
            WHERE target.name IS NOT NULL

            // 计算关系权重
            WITH source, target, r,
                 CASE
                     WHEN type(r) = 'NEARBY' THEN 0.9
                     WHEN type(r) = 'HAS_ATTRACTION' THEN 0.8
                     WHEN type(r) = 'HAS_FOOD' THEN 0.7
                     WHEN type(r) = 'HAS_SPECIALTY' THEN 0.6
                     ELSE 0.5
                 END as weight

            RETURN source, target, type(r) as rel_type, weight,
                   [source.name, type(r), target.name] as path_names,
                   1 as path_len, weight as relevance
            ORDER BY weight DESC
            LIMIT 15
            """

            result = session.run(cypher_query, {
                "source_entities": graph_query.source_entities
            })

            for record in result:
                # 构建简单路径
                nodes = [
                    {"name": record["source"].get("name", ""), "id": record["source"].get("id", "")},
                    {"name": record["target"].get("name", ""), "id": record["target"].get("id", "")}
                ]

                relationships = [{
                    "type": record["rel_type"],
                    "weight": record["weight"]
                }]

                path = GraphPath(
                    nodes=nodes,
                    relationships=relationships,
                    path_length=record["path_len"],
                    relevance_score=record["relevance"],
                    path_type="entity_relation"
                )
                paths.append(path)

        except Exception as e:
            logger.error(f"实体关系查询失败: {e}")

        return paths

    def _find_shortest_paths(self, graph_query: GraphQuery, session) -> List[GraphPath]:
        """查找最短路径"""
        paths = []

        try:
            # 旅游场景的最短路径查询
            cypher_query = """
            UNWIND $source_entities as source_name
            MATCH (source)
            WHERE source.name CONTAINS source_name OR source.id = source_name

            UNWIND $target_entities as target_name
            MATCH (target)
            WHERE target.name CONTAINS target_name OR target.id = target_name

            // 使用最短路径算法
            MATCH path = shortestPath((source)-[*1..4]-(target))
            WHERE source <> target

            // 计算路径得分（考虑路径长度和节点类型）
            WITH path, length(path) as path_len,
                 nodes(path) as path_nodes,
                 relationships(path) as path_rels

            // 旅游相关性评分
            CALL {
                WITH path_nodes
                UNWIND path_nodes as node
                RETURN
                    CASE
                        WHEN 'City' IN labels(node) THEN 1.0
                        WHEN 'Attraction' IN labels(node) THEN 0.9
                        WHEN 'Food' IN labels(node) OR 'Restaurant' IN labels(node) THEN 0.8
                        WHEN 'Hotel' IN labels(node) THEN 0.7
                        WHEN 'Region' IN labels(node) OR 'SubRegion' IN labels(node) THEN 0.6
                        ELSE 0.5
                    END as node_score
            }

            WITH path, path_len, path_nodes, path_rels, avg(node_score) as avg_node_score

            // 计算总相关性（路径越短，节点得分越高越好）
            WITH path, path_len, path_nodes, path_rels,
                 (avg_node_score * 2.0 / path_len) as relevance

            RETURN path, path_len, path_nodes, path_rels, relevance
            ORDER BY relevance DESC
            LIMIT 10
            """

            result = session.run(cypher_query, {
                "source_entities": graph_query.source_entities,
                "target_entities": graph_query.target_entities or []
            })

            for record in result:
                path_data = self._parse_neo4j_path(record)
                if path_data:
                    path_data.path_type = "shortest_path"
                    paths.append(path_data)

        except Exception as e:
            logger.error(f"最短路径查询失败: {e}")

        return paths
    
    def _fallback_subgraph_extraction(self, graph_query: GraphQuery) -> KnowledgeSubgraph:
        """降级子图提取"""
        return KnowledgeSubgraph(
            central_nodes=[],
            connected_nodes=[],
            relationships=[],
            graph_metrics={},
            reasoning_chains=[]
        )
    
    def close(self):
        """关闭资源连接"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.close()
            logger.info("图RAG检索系统已关闭") 