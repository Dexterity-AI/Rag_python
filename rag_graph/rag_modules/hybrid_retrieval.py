"""
混合检索模块
基于双层检索范式：实体级 + 主题级检索
结合图结构检索和向量检索，使用Round-robin轮询策略
"""

import json
import logging
import re
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from neo4j import GraphDatabase
from .graph_indexing import GraphIndexingModule
from cache import VectorSearchCache, get_cache_manager

logger = logging.getLogger(__name__)

@dataclass
class RetrievalResult:
    """检索结果数据结构"""
    content: str
    node_id: str
    node_type: str
    relevance_score: float
    retrieval_level: str  # 'low' or 'high'
    metadata: Dict[str, Any]

class HybridRetrievalModule:
    """
    混合检索模块
    核心特点：
    1. 双层检索范式（实体级 + 主题级）
    2. 关键词提取和匹配
    3. 图结构+向量检索结合
    4. 一跳邻居扩展
    5. Round-robin轮询合并策略
    """
    
    def __init__(self, config, milvus_module, data_module, llm_client):
        self.config = config
        self.milvus_module = milvus_module
        self.data_module = data_module
        self.llm_client = llm_client
        self.driver = None
        self.bm25_retriever = None

        # 图索引模块
        self.graph_indexing = GraphIndexingModule(config, llm_client)
        self.graph_indexed = False
        self.graph_data_module = None

        # 初始化向量检索缓存
        cache_manager = get_cache_manager()
        self.vector_cache = cache_manager.vector_cache

    def initialize(self, chunks: List[Document]):
        """初始化检索系统"""
        logger.info("初始化混合检索模块...")

        # 连接Neo4j
        self.driver = GraphDatabase.driver(
            self.config.neo4j_uri,
            auth=(self.config.neo4j_user, self.config.neo4j_password)
        )

        # 初始化图数据模块
        try:
            from .graph_data_preparation import GraphDataPreparationModule
            self.graph_data_module = GraphDataPreparationModule(
                self.config.neo4j_uri,
                self.config.neo4j_user,
                self.config.neo4j_password
            )
            logger.info("图数据准备模块初始化成功")
        except Exception as e:
            logger.warning(f"图数据准备模块初始化失败: {e}")

        # 初始化BM25检索器
        if chunks:
            self.bm25_retriever = BM25Retriever.from_documents(chunks)
            logger.info(f"BM25检索器初始化完成，文档数量: {len(chunks)}")

        # 初始化图索引
        self._build_graph_index()
        
    def _build_graph_index(self):
        """构建图索引"""
        if self.graph_indexed:
            return

        logger.info("开始构建图索引...")

        try:
            # 获取旅游图数据
            if self.graph_data_module:
                # 从图数据模块加载所有实体
                data_stats = self.graph_data_module.load_graph_data()
                logger.info(f"从图数据模块加载数据: {data_stats}")

                # 创建实体键值对
                self.graph_indexing.create_entity_key_values(
                    cities=self.graph_data_module.cities,
                    regions=self.graph_data_module.regions,
                    subregions=self.graph_data_module.subregions,
                    attractions=self.graph_data_module.attractions,
                    foods=self.graph_data_module.foods,
                    restaurants=self.graph_data_module.restaurants,
                    hotels=self.graph_data_module.hotels,
                    festivals=self.graph_data_module.festivals,
                    specialties=self.graph_data_module.specialties
                )
            else:
                # 降级方案：直接从Neo4j获取数据
                self._load_entities_from_neo4j()

            # 创建关系键值对（这里需要从Neo4j获取关系数据）
            relationships = self._extract_relationships_from_graph()
            if relationships:
                self.graph_indexing.create_relation_key_values(relationships)

            # 去重优化
            self.graph_indexing.deduplicate_entities_and_relations()

            self.graph_indexed = True
            stats = self.graph_indexing.get_statistics()
            logger.info(f"图索引构建完成: {stats}")

        except Exception as e:
            logger.error(f"构建图索引失败: {e}")

    def _load_entities_from_neo4j(self):
        """降级方案：直接从Neo4j加载实体数据"""
        logger.info("使用降级方案：直接从Neo4j加载实体数据")

        try:
            with self.driver.session() as session:
                # 加载城市数据
                city_query = "MATCH (c:City) RETURN c as city_data LIMIT 50"
                cities_data = []
                for record in session.run(city_query):
                    city_data = record["city_data"]
                    cities_data.append(city_data)

                # 加载景点数据
                attraction_query = "MATCH (a:Attraction) RETURN a as attraction_data LIMIT 100"
                attractions_data = []
                for record in session.run(attraction_query):
                    attraction_data = record["attraction_data"]
                    attractions_data.append(attraction_data)

                # 创建实体键值对
                self.graph_indexing.create_entity_key_values(
                    cities=cities_data,
                    attractions=attractions_data
                )

        except Exception as e:
            logger.error(f"从Neo4j加载实体数据失败: {e}")
            
    def _extract_relationships_from_graph(self) -> List[Tuple[str, str, str]]:
        """从Neo4j图中提取关系"""
        relationships = []
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (source)-[r]->(target)
                WHERE source.nodeId >= '200000000' OR target.nodeId >= '200000000'
                RETURN source.nodeId as source_id, type(r) as relation_type, target.nodeId as target_id
                LIMIT 1000
                """
                result = session.run(query)
                
                for record in result:
                    relationships.append((
                        record["source_id"],
                        record["relation_type"],
                        record["target_id"]
                    ))
                    
        except Exception as e:
            logger.error(f"提取图关系失败: {e}")
            
        return relationships
            
    def extract_query_keywords(self, query: str) -> Tuple[List[str], List[str]]:
        """
        提取查询关键词：实体级 + 主题级
        使用轻量级规则方法，避免LLM调用
        """
        return self._extract_keywords_rule_based(query)

    def _extract_keywords_rule_based(self, query: str) -> Tuple[List[str], List[str]]:
        """
        基于规则的智能关键词提取（轻量级，无LLM调用）
        使用词典匹配 + 启发式规则
        """
        # 停用词表
        stop_words = {
            '的', '了', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很',
            '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '什么',
            '吗', '吧', '呢', '啊', '哦', '嗯', '在', '与', '及', '等', '之', '为', '以', '被', '把'
        }

        # 旅游领域实体词典
        tourism_entities = {
            # 城市
            '北京', '上海', '广州', '深圳', '杭州', '南京', '西安', '成都', '重庆', '武汉',
            '天津', '苏州', '无锡', '厦门', '青岛', '大连', '宁波', '长沙', '郑州', '济南',
            '西藏', '拉萨', '林芝', '日喀则', '青海', '西宁', '新疆', '乌鲁木齐', '伊犁',
            '云南', '昆明', '大理', '丽江', '香格里拉', '西双版纳',
            '四川', '九寨沟', '黄龙', '峨眉山', '乐山', '稻城亚丁',
            '陕西', '华山', '兵马俑', '华清池',
            '广西', '桂林', '阳朔', '北海',
            '海南', '三亚', '海口', '蜈支洲岛',
            # 景点
            '故宫', '长城', '天安门', '颐和园', '天坛', '北海公园', '圆明园', '景山', '什刹海',
            '八达岭', '慕田峪', '居庸关', '司马台', '箭扣',
            '黄山', '泰山', '华山', '衡山', '恒山', '嵩山', '庐山', '雁荡山', '武夷山',
            '西湖', '千岛湖', '太湖', '滇池', '洱海', '泸沽湖', '纳木错', '青海湖',
            '布达拉宫', '大昭寺', '罗布林卡', '扎什伦布寺',
            '九寨沟', '黄龙', '张家界', '天门山', '凤凰古城',
            '漓江', '象鼻山', '两江四湖', '遇龙河',
            '外滩', '东方明珠', '豫园', '城隍庙', '南京路', '田子坊',
            '迪士尼', '欢乐谷', '方特', '长隆', '海洋公园', '动物园', '植物园',
            '博物馆', '美术馆', '纪念馆', '故居', '陵墓', '寺庙', '教堂',
            # 美食相关
            '火锅', '烧烤', '烤鸭', '拉面', '小吃', '美食', '餐厅', '饭店', '酒楼',
            # 住宿相关
            '酒店', '宾馆', '民宿', '客栈', '度假村', '青年旅舍',
            # 交通相关
            '机场', '火车站', '高铁站', '地铁站', '公交站', '港口', '码头',
            # 其他地点
            '古镇', '古村', '老街', '步行街', '广场', '公园', '湿地', '海滩', '海岛'
        }

        # 主题/类别词典
        topic_keywords_set = {
            '景点', '景区', '旅游', '旅行', '游览', '观光', '度假', '休闲',
            '美食', '餐饮', '小吃', '特产', '购物',
            '酒店', '住宿', '宾馆', '民宿', '客栈',
            '交通', '出行', '路线', '导航', '距离', '时间',
            '门票', '票价', '费用', '价格', '花费', '预算', '多少钱',
            '攻略', '指南', '建议', '推荐', '介绍', '分享', '体验',
            '历史', '文化', '古迹', '遗产', '建筑', '宗教', '民俗',
            '自然', '风景', '风光', '山水', '海景', '森林', '草原', '沙漠', '雪山',
            '亲子', '情侣', '家庭', '团队', '自助', '自驾', '徒步', '骑行', '探险',
            '春季', '夏季', '秋季', '冬季', '春天', '夏天', '秋天', '冬天',
            '最佳', '适合', '好玩', '值得', '著名', '热门', '必去', '打卡'
        }

        entity_keywords = []
        topic_keywords = []

        # 1. 直接匹配实体词典
        for entity in tourism_entities:
            if entity in query:
                entity_keywords.append(entity)

        # 2. 直接匹配主题词典
        for topic in topic_keywords_set:
            if topic in query:
                topic_keywords.append(topic)

        # 3. 分词提取额外关键词
        words = re.findall(r'[\u4e00-\u9fff]+', query)

        for word in words:
            if len(word) < 2 or word in stop_words:
                continue

            # 跳过已匹配的
            if word in entity_keywords or word in topic_keywords:
                continue

            # 根据词性/特征分类
            # 地点后缀 -> 实体
            location_suffixes = ['市', '省', '县', '镇', '村', '山', '河', '湖', '海', '岛', '塔', '寺', '庙', '宫', '殿', '园', '馆', '街', '路']
            if any(word.endswith(suffix) for suffix in location_suffixes):
                entity_keywords.append(word)
                continue

            # 活动/抽象后缀 -> 主题
            abstract_suffixes = ['游', '行', '观', '览', '玩', '学', '感', '赏']
            if any(word.endswith(suffix) for suffix in abstract_suffixes):
                topic_keywords.append(word)
                continue

        # 4. 去重并限制数量
        entity_keywords = list(dict.fromkeys(entity_keywords))[:5]  # 保持顺序去重
        topic_keywords = list(dict.fromkeys(topic_keywords))[:5]

        # 5. 保底处理：确保至少有一些关键词
        if not entity_keywords and words:
            # 从查询中提取最长的词作为实体
            entity_keywords = sorted([w for w in words if len(w) >= 2 and w not in stop_words],
                                    key=len, reverse=True)[:3]

        if not topic_keywords:
            # 添加通用主题
            topic_keywords = ['旅游']

        logger.info(f"规则提取关键词 - 实体: {entity_keywords}, 主题: {topic_keywords}")
        return entity_keywords, topic_keywords

    def entity_level_retrieval(self, entity_keywords: List[str], top_k: int = 5) -> List[RetrievalResult]:
        """
        实体级检索：专注于具体实体和关系
        使用图索引的键值对结构进行检索
        """
        results = []
        
        # 1. 使用图索引进行实体检索
        for keyword in entity_keywords:
            # 检索匹配的实体
            entities = self.graph_indexing.get_entities_by_key(keyword)
            
            for entity in entities:
                # 获取邻居信息
                neighbors = self._get_node_neighbors(entity.metadata["node_id"], max_neighbors=2)
                
                # 构建增强内容
                enhanced_content = entity.value_content
                if neighbors:
                    enhanced_content += f"\n相关信息: {', '.join(neighbors)}"
                
                results.append(RetrievalResult(
                    content=enhanced_content,
                    node_id=entity.metadata["node_id"],
                    node_type=entity.entity_type,
                    relevance_score=0.9,  # 精确匹配得分较高
                    retrieval_level="entity",
                    metadata={
                        "entity_name": entity.entity_name,
                        "entity_type": entity.entity_type,
                        "index_keys": entity.index_keys,
                        "matched_keyword": keyword
                    }
                ))
        
        # 2. 如果图索引结果不足，使用Neo4j进行补充检索
        if len(results) < top_k:
            neo4j_results = self._neo4j_entity_level_search(entity_keywords, top_k - len(results))
            results.extend(neo4j_results)
            
        # 3. 按相关性排序并返回
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(f"实体级检索完成，返回 {len(results)} 个结果")
        return results[:top_k]
    
    def _neo4j_entity_level_search(self, keywords: List[str], limit: int) -> List[RetrievalResult]:
        """Neo4j补充检索 - 使用 CONTAINS 查询，不依赖全文索引"""
        results = []

        try:
            with self.driver.session() as session:
                # 使用简单的 CONTAINS 查询，不依赖全文索引
                # 修复：简化查询，避免复杂的WITH传递问题
                cypher_query = """
                UNWIND $keywords as keyword

                // 搜索景点
                OPTIONAL MATCH (a:Attraction)
                WHERE a.name CONTAINS keyword OR a.description CONTAINS keyword
                WITH keyword, a as node WHERE node IS NOT NULL
                RETURN DISTINCT
                    node.nodeId as node_id,
                    node.name as name,
                    node.description as description,
                    node.category as category,
                    node.ticket_price as ticket_price,
                    node.address as address,
                    node.best_time as best_time,
                    node.highlights as highlights,
                    labels(node) as labels,
                    head(labels(node)) as node_type,
                    keyword as matched_keyword,
                    1.0 as score
                LIMIT $limit

                UNION

                UNWIND $keywords as keyword
                // 搜索城市
                OPTIONAL MATCH (c:City)
                WHERE c.name CONTAINS keyword OR c.description CONTAINS keyword
                WITH keyword, c as node WHERE node IS NOT NULL
                RETURN DISTINCT
                    node.nodeId as node_id,
                    node.name as name,
                    node.description as description,
                    node.category as category,
                    node.ticket_price as ticket_price,
                    node.address as address,
                    node.best_time as best_time,
                    node.highlights as highlights,
                    labels(node) as labels,
                    head(labels(node)) as node_type,
                    keyword as matched_keyword,
                    1.0 as score
                LIMIT $limit

                UNION

                UNWIND $keywords as keyword
                // 搜索地区
                OPTIONAL MATCH (r:Region)
                WHERE r.name CONTAINS keyword OR r.description CONTAINS keyword
                WITH keyword, r as node WHERE node IS NOT NULL
                RETURN DISTINCT
                    node.nodeId as node_id,
                    node.name as name,
                    node.description as description,
                    node.category as category,
                    node.ticket_price as ticket_price,
                    node.address as address,
                    node.best_time as best_time,
                    node.highlights as highlights,
                    labels(node) as labels,
                    head(labels(node)) as node_type,
                    keyword as matched_keyword,
                    1.0 as score
                LIMIT $limit
                """

                result = session.run(cypher_query, {
                    "keywords": keywords,
                    "limit": limit
                })

                for record in result:
                    content_parts = []
                    node_type = record["node_type"]

                    if node_type == "Attraction":
                        if record["name"]:
                            content_parts.append(f"景点: {record['name']}")
                        if record["category"]:
                            content_parts.append(f"类型: {record['category']}")
                        if record["description"]:
                            content_parts.append(f"描述: {record['description']}")
                        if record["ticket_price"]:
                            content_parts.append(f"门票: {record['ticket_price']}")
                        if record["address"]:
                            content_parts.append(f"地址: {record['address']}")
                    elif node_type == "City":
                        if record["name"]:
                            content_parts.append(f"城市: {record['name']}")
                        if record["description"]:
                            content_parts.append(f"描述: {record['description']}")
                        if record["best_time"]:
                            content_parts.append(f"最佳旅游时间: {record['best_time']}")
                        if record["highlights"]:
                            content_parts.append(f"特色: {record['highlights']}")
                    elif node_type == "Region":
                        if record["name"]:
                            content_parts.append(f"地区: {record['name']}")
                        if record["description"]:
                            content_parts.append(f"描述: {record['description']}")

                    if content_parts:
                        results.append(RetrievalResult(
                            content='\n'.join(content_parts),
                            node_id=record["node_id"] or f"unknown_{len(results)}",
                            node_type=node_type,
                            relevance_score=0.7,
                            retrieval_level="entity",
                            metadata={
                                "name": record["name"],
                                "category": record.get("category"),
                                "description": record.get("description"),
                                "ticket_price": record.get("ticket_price"),
                                "labels": record["labels"],
                                "matched_keyword": record["matched_keyword"],
                                "source": "neo4j_contains"
                            }
                        ))

        except Exception as e:
            logger.warning(f"Neo4j CONTAINS 检索失败: {e}，尝试降级方案")
            # 降级方案：更简单的查询
            try:
                with self.driver.session() as session:
                    fallback_query = """
                    UNWIND $keywords as keyword
                    MATCH (n)
                    WHERE (n:City OR n:Attraction OR n:Region)
                      AND n.name CONTAINS keyword
                    RETURN DISTINCT
                        n.nodeId as node_id,
                        n.name as name,
                        n.description as description,
                        labels(n) as labels,
                        head(labels(n)) as node_type
                    LIMIT $limit
                    """

                    result = session.run(fallback_query, {
                        "keywords": keywords,
                        "limit": limit
                    })

                    for record in result:
                        content_parts = []
                        node_type = record["node_type"]

                        if node_type == "Attraction":
                            content_parts.append(f"景点: {record['name']}")
                        elif node_type == "City":
                            content_parts.append(f"城市: {record['name']}")
                        elif node_type == "Region":
                            content_parts.append(f"地区: {record['name']}")
                        
                        if record["description"]:
                            content_parts.append(f"描述: {record['description']}")

                        if content_parts:
                            results.append(RetrievalResult(
                                content='\n'.join(content_parts),
                                node_id=record["node_id"] or f"fallback_{len(results)}",
                                node_type=node_type,
                                relevance_score=0.6,
                                retrieval_level="entity",
                                metadata={
                                    "name": record["name"],
                                    "labels": record["labels"],
                                    "source": "neo4j_fallback_simple"
                                }
                            ))
            except Exception as e2:
                logger.error(f"Neo4j降级检索也失败: {e2}")

        return results
    
    def topic_level_retrieval(self, topic_keywords: List[str], top_k: int = 5) -> List[RetrievalResult]:
        """
        主题级检索：专注于广泛主题和概念
        使用图索引的关系键值对结构进行主题检索
        """
        results = []
        
        # 1. 使用图索引进行关系/主题检索
        for keyword in topic_keywords:
            # 检索匹配的关系
            relations = self.graph_indexing.get_relations_by_key(keyword)
            
            for relation in relations:
                # 获取相关实体信息
                source_entity = self.graph_indexing.entity_kv_store.get(relation.source_entity)
                target_entity = self.graph_indexing.entity_kv_store.get(relation.target_entity)
                
                if source_entity and target_entity:
                    # 构建丰富的主题内容
                    content_parts = [
                        f"主题: {keyword}",
                        relation.value_content,
                        f"相关菜品: {source_entity.entity_name}",
                        f"相关信息: {target_entity.entity_name}"
                    ]
                    
                    # 添加源实体的详细信息
                    if source_entity.entity_type in ["Attraction", "City", "Region"]:
                        newline = '\n'
                        content_parts.append(f"详情: {source_entity.value_content.split(newline)[0]}")
                    
                    results.append(RetrievalResult(
                        content='\n'.join(content_parts),
                        node_id=relation.source_entity,  # 以主要实体为ID
                        node_type=source_entity.entity_type,
                        relevance_score=0.95,  # 主题匹配得分
                        retrieval_level="topic",
                        metadata={
                            "relation_id": relation.relation_id,
                            "relation_type": relation.relation_type,
                            "source_name": source_entity.entity_name,
                            "target_name": target_entity.entity_name,
                            "matched_keyword": keyword,
                            "index_keys": relation.index_keys
                        }
                    ))
        
        # 2. 使用实体的分类信息进行主题检索
        for keyword in topic_keywords:
            entities = self.graph_indexing.get_entities_by_key(keyword)
            for entity in entities:
                if entity.entity_type in ["Attraction", "City", "Region", "Food", "Hotel"]:
                    # 构建分类主题内容
                    content_parts = [
                        f"主题分类: {keyword}",
                        entity.value_content
                    ]

                    results.append(RetrievalResult(
                        content='\n'.join(content_parts),
                        node_id=entity.metadata["node_id"],
                        node_type=entity.entity_type,
                        relevance_score=0.85,  # 分类匹配得分
                        retrieval_level="topic",
                        metadata={
                            "entity_name": entity.entity_name,
                            "entity_type": entity.entity_type,
                            "matched_keyword": keyword,
                            "source": "category_match"
                        }
                    ))
        
        # 3. 如果结果不足，使用Neo4j进行补充检索
        if len(results) < top_k:
            neo4j_results = self._neo4j_topic_level_search(topic_keywords, top_k - len(results))
            results.extend(neo4j_results)
            
        # 4. 按相关性排序并返回
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(f"主题级检索完成，返回 {len(results)} 个结果")
        return results[:top_k]
    
    def _neo4j_topic_level_search(self, keywords: List[str], limit: int) -> List[RetrievalResult]:
        """Neo4j主题级检索补充"""
        results = []

        try:
            with self.driver.session() as session:
                cypher_query = """
                UNWIND $keywords as keyword
                // 搜索景点
                MATCH (a:Attraction)
                WHERE a.category CONTAINS keyword
                WITH a, 'Attraction' as node_type, a.category as category_info, keyword
                OPTIONAL MATCH (a)-[:HAS_ATTRACTION]->(sub_attraction:Attraction)
                WITH a, node_type, category_info, keyword, collect(sub_attraction.name)[0..3] as related_attractions
                RETURN
                    a.nodeId as node_id,
                    a.name as name,
                    node_type as node_type,
                    category_info as category_info,
                    a.description as description,
                    a.ticket_price as ticket_price,
                    a.best_time as best_time,
                    related_attractions,
                    keyword as matched_keyword
                UNION ALL
                UNWIND $keywords as keyword
                // 搜索城市
                MATCH (c:City)
                WHERE c.highlights CONTAINS keyword OR c.description CONTAINS keyword
                WITH c, 'City' as node_type, '旅游城市' as category_info, keyword
                OPTIONAL MATCH (c)-[:HAS_ATTRACTION]->(a:Attraction)
                WITH c, node_type, category_info, keyword, collect(a.name)[0..3] as related_attractions
                RETURN
                    c.nodeId as node_id,
                    c.name as name,
                    node_type as node_type,
                    category_info as category_info,
                    c.description as description,
                    c.ticket_price as ticket_price,
                    c.best_time as best_time,
                    related_attractions,
                    keyword as matched_keyword
                UNION ALL
                UNWIND $keywords as keyword
                // 搜索地区
                MATCH (r:Region)
                WHERE r.description CONTAINS keyword OR r.highlights CONTAINS keyword
                WITH r, 'Region' as node_type, '旅游地区' as category_info, keyword
                OPTIONAL MATCH (r)-[:HAS_ATTRACTION]->(a:Attraction)
                WITH r, node_type, category_info, keyword, collect(a.name)[0..3] as related_attractions
                RETURN
                    r.nodeId as node_id,
                    r.name as name,
                    node_type as node_type,
                    category_info as category_info,
                    r.description as description,
                    r.ticket_price as ticket_price,
                    r.best_time as best_time,
                    related_attractions,
                    keyword as matched_keyword
                ORDER BY name
                LIMIT $limit
                """

                result = session.run(cypher_query, {
                    "keywords": keywords,
                    "limit": limit
                })

                for record in result:
                    content_parts = []
                    node_type = record["node_type"]

                    if node_type == "Attraction":
                        content_parts.append(f"景点: {record['name']}")
                        if record.get("description"):
                            content_parts.append(f"描述: {record['description']}")
                        if record.get("ticket_price"):
                            content_parts.append(f"门票: {record['ticket_price']}")
                    elif node_type == "City":
                        content_parts.append(f"城市: {record['name']}")
                        if record.get("description"):
                            content_parts.append(f"描述: {record['description']}")
                        if record.get("best_time"):
                            content_parts.append(f"最佳旅游时间: {record['best_time']}")
                    elif node_type == "Region":
                        content_parts.append(f"地区: {record['name']}")
                        if record.get("description"):
                            content_parts.append(f"描述: {record['description']}")

                    if record.get("category_info"):
                        content_parts.append(f"类别: {record['category_info']}")

                    if record.get("related_attractions"):
                        attractions_str = ', '.join([a for a in record["related_attractions"] if a])
                        if attractions_str:
                            content_parts.append(f"相关景点: {attractions_str}")

                    if content_parts:
                        results.append(RetrievalResult(
                            content='\n'.join(content_parts),
                            node_id=record.get("node_id") or f"topic_{len(results)}",
                            node_type=node_type,
                            relevance_score=0.75,
                            retrieval_level="topic",
                            metadata={
                                "name": record.get("name"),
                                "category": record.get("category_info"),
                                "description": record.get("description"),
                                "matched_keyword": record.get("matched_keyword"),
                                "source": "neo4j_topic"
                            }
                        ))
                    
        except Exception as e:
            logger.error(f"Neo4j主题级检索失败: {e}")
            
        return results
        
    def dual_level_retrieval(self, query: str, top_k: int = 5) -> List[Document]:
        """
        双层检索：结合实体级和主题级检索
        """
        logger.info(f"开始双层检索: {query}")
        
        # 1. 提取关键词
        entity_keywords, topic_keywords = self.extract_query_keywords(query)
        
        # 2. 执行双层检索
        entity_results = self.entity_level_retrieval(entity_keywords, top_k)
        topic_results = self.topic_level_retrieval(topic_keywords, top_k)
        
        # 3. 结果合并和排序
        all_results = entity_results + topic_results
        
        # 4. 去重和重排序
        seen_nodes = set()
        unique_results = []
        
        for result in sorted(all_results, key=lambda x: x.relevance_score, reverse=True):
            if result.node_id not in seen_nodes:
                seen_nodes.add(result.node_id)
                unique_results.append(result)
        
        # 5. 转换为Document格式
        documents = []
        for result in unique_results[:top_k]:
            # 确保recipe_name字段正确设置
            recipe_name = result.metadata.get("name") or result.metadata.get("entity_name", "未知菜品")
            
            doc = Document(
                page_content=result.content,
                metadata={
                    "node_id": result.node_id,
                    "node_type": result.node_type,
                    "retrieval_level": result.retrieval_level,
                    "relevance_score": result.relevance_score,
                    "recipe_name": recipe_name,  # 确保有recipe_name字段
                    "search_type": "dual_level",  # 设置搜索类型
                    **result.metadata
                }
            )
            documents.append(doc)
            
        logger.info(f"双层检索完成，返回 {len(documents)} 个文档")
        return documents
    
    def vector_search_enhanced(self, query: str, top_k: int = 5) -> List[Document]:
        """
        增强的向量检索：结合图信息
        支持缓存机制
        """
        try:
            # 尝试从缓存获取
            if self.vector_cache:
                cached_result = self.vector_cache.get(query, top_k)
                if cached_result is not None:
                    logger.info(f"向量检索缓存命中: {query[:50]}...")
                    return cached_result

            # 使用Milvus进行向量检索
            vector_docs = self.milvus_module.similarity_search(query, k=top_k*2)

            # 用图信息增强结果并转换为Document对象
            enhanced_docs = []
            for result in vector_docs:
                # 从Milvus结果创建Document对象
                content = result.get("text", "")
                metadata = result.get("metadata", {})
                node_id = metadata.get("node_id")

                if node_id:
                    # 从图中获取邻居信息
                    neighbors = self._get_node_neighbors(node_id)
                    if neighbors:
                        # 将邻居信息添加到内容中
                        neighbor_info = f"\n相关信息: {', '.join(neighbors[:3])}"
                        content += neighbor_info

                # 确保recipe_name字段正确设置
                recipe_name = metadata.get("recipe_name", "未知菜品")

                # 调试：打印向量得分
                vector_score = result.get("score", 0.0)
                logger.debug(f"向量检索得分: {recipe_name} = {vector_score}")

                # 创建Document对象
                doc = Document(
                    page_content=content,
                    metadata={
                        **metadata,
                        "recipe_name": recipe_name,  # 确保有recipe_name字段
                        "score": vector_score,
                        "search_type": "vector_enhanced"
                    }
                )
                enhanced_docs.append(doc)

            # 缓存结果
            result_docs = enhanced_docs[:top_k]
            if self.vector_cache:
                self.vector_cache.set(query, result_docs, top_k)
                logger.debug(f"向量检索结果已缓存: {query[:50]}...")

            return result_docs

        except Exception as e:
            logger.error(f"增强向量检索失败: {e}")
            return []
    
    def _get_node_neighbors(self, node_id: str, max_neighbors: int = 3) -> List[str]:
        """获取节点的邻居信息"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (n {nodeId: $node_id})-[r]-(neighbor)
                RETURN neighbor.name as name
                LIMIT $limit
                """
                result = session.run(query, {"node_id": node_id, "limit": max_neighbors})
                return [record["name"] for record in result if record["name"]]
        except Exception as e:
            logger.error(f"获取邻居节点失败: {e}")
            return []
    
    def hybrid_search(self, query: str, top_k: int = 5) -> List[Document]:
        """
        混合检索：使用Round-robin轮询合并策略
        公平轮询合并不同检索结果，不使用权重配置
        """
        logger.info(f"开始混合检索: {query}")
        
        # 1. 双层检索（实体+主题检索）
        dual_docs = self.dual_level_retrieval(query, top_k)
        
        # 2. 增强向量检索
        vector_docs = self.vector_search_enhanced(query, top_k)
        
        # 3. Round-robin轮询合并
        merged_docs = []
        seen_doc_ids = set()
        max_len = max(len(dual_docs), len(vector_docs))
        origin_len = len(dual_docs) + len(vector_docs)
        
        for i in range(max_len):
            # 先添加双层检索结果
            if i < len(dual_docs):
                doc = dual_docs[i]
                doc_id = doc.metadata.get("node_id", hash(doc.page_content))
                if doc_id not in seen_doc_ids:
                    seen_doc_ids.add(doc_id)
                    doc.metadata["search_method"] = "dual_level"
                    doc.metadata["round_robin_order"] = len(merged_docs)
                    # 设置统一的final_score字段
                    doc.metadata["final_score"] = doc.metadata.get("relevance_score", 0.0)
                    merged_docs.append(doc)
            
            # 再添加向量检索结果
            if i < len(vector_docs):
                doc = vector_docs[i]
                doc_id = doc.metadata.get("node_id", hash(doc.page_content))
                if doc_id not in seen_doc_ids:
                    seen_doc_ids.add(doc_id)
                    doc.metadata["search_method"] = "vector_enhanced"
                    doc.metadata["round_robin_order"] = len(merged_docs)
                    # 设置统一的final_score字段（向量得分需要转换）
                    vector_score = doc.metadata.get("score", 0.0)
                    # COSINE距离转换为相似度：distance越小，相似度越高
                    similarity_score = max(0.0, 1.0 - vector_score) if vector_score <= 1.0 else 0.0
                    doc.metadata["final_score"] = similarity_score
                    merged_docs.append(doc)
        
        # 取前top_k个结果
        final_docs = merged_docs[:top_k]
        
        logger.info(f"Round-robin合并：从总共{origin_len}个结果合并为{len(final_docs)}个文档")
        logger.info(f"混合检索完成，返回 {len(final_docs)} 个文档")
        return final_docs
        
    def close(self):
        """关闭资源连接"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j连接已关闭") 
