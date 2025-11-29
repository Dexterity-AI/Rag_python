#图数据准备模块

import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from neo4j import GraphDatabase
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

@dataclass 
class GraphNode:
    """图节点数据结构"""
    node_id: str
    labels: List[str] 
    name: str
    properties: Dict[str, Any]

@dataclass 
class GraphRelation:
    """图关系数据结构"""
    start_node_id: str 
    labels: List[str]
    name: str 
    properties: Dict[str, Any]

class GraphDataPreparationModule:

    #图数据库数据准备模块 - 从neo4j读取数据并转换为文档

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        
        """
        初始化数据库连接

        Args:
           uri: Neo4j连接的URI
           user: 用户名 
           password: 密码
           database: 数据库名称 
        """
        self.uri = uri 
        self.user = user 
        self.password = password 
        self.database = database 
        self.driver = None 
        self.documents: List[Document] = []
        self.chunks: List[Document] = []
        self.cities: List[GraphNode] = []
        self.regions: List[GraphNode] = []
        self.subregions: List[GraphNode] = []
        self.attractions: List[GraphNode] = []
        self.foods: List[GraphNode] = []
        self.restaurants: List[GraphNode] = []
        self.hotels: List[GraphNode] = []
        self.festivals: List[GraphNode] = []
        self.specialties: List[GraphNode] = []

        self._connect()

    def _connect(self):
        """建立Neo4j连接"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth = (self.user, self.password)
                # database参数应该在session级别设置
            )
            logger.info(f"已连接到Neo4j数据库: {self.uri}")

            #测试连接 - 在session级别指定数据库
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as test")
                tets_result = result.single()
                if tets_result:
                    logger.info("Neo4j连接测试成功")
        except Exception as e:
            logger.error(f"连接Neo4j失败: {e}")
            raise 

    def close(self):
        """关闭数据库连接"""
        if hasattr(self,'driver') and self.driver:
            self.driver.close() 
            logger.info("Neo4j连接已关闭")

    def load_graph_data(self) -> Dict[str, Any]:
        """
        从Neo4j加载图数据
        Returns:
               包含节点和关系的数据字典
        """

        logger.info("正在从Neo4j加载图数据")

        with self.driver.session() as session:
            # 加载城市节点
            city_query = """
            MATCH (n:City)
            OPTIONAL MATCH (n)-[:HAS_ATTRACTION]->(a:Attraction)
            WITH n, collect(DISTINCT a.category) as allCategories
            RETURN n.id as nodeId,
                   labels(n) as labels,
                   n.name as name,
                   properties(n) as originalProperties,
                   CASE WHEN size(allCategories) > 0 THEN allCategories[0] ELSE null END as mainCategories,
                   allCategories
            """

            result = session.run(city_query)
            self.cities = []

            for record in result:
                # 合并原始属性和新的分类信息
                properties = dict(record["originalProperties"])
                properties["category"] = record["mainCategories"]
                properties["all_categories"] = record["allCategories"]

                node = GraphNode(
                    node_id = record["nodeId"],
                    labels = record["labels"],
                    name = record["name"],
                    properties = properties
                )

                self.cities.append(node)

            logger.info(f"加载了{len(self.cities)} 个城市节点")

            # 加载地区节点
            region_query = """
            MATCH (n:Region)
            OPTIONAL MATCH (n)-[:HAS_SUBREGION]->(sr:SubRegion)
            OPTIONAL MATCH (n)-[:HAS_ATTRACTION]->(a:Attraction)
            WITH n, collect(DISTINCT sr.id) as subregionIds, collect(DISTINCT a.category) as allCategories
            RETURN n.id as nodeId,
                   labels(n) as labels,
                   n.name as name,
                   properties(n) as properties
            """

            result = session.run(region_query)
            self.regions = []
            for record in result:
                node = GraphNode(
                    node_id = record["nodeId"],
                    labels = record["labels"],
                    name = record["name"],
                    properties = record["properties"]
                )
                self.regions.append(node)

            logger.info(f"加载了{len(self.regions)} 个地区节点")

            # 加载子地区节点
            subregion_query = """
            MATCH (n:SubRegion)
            OPTIONAL MATCH (n)-[:HAS_ATTRACTION]->(a:Attraction)
            WITH n, collect(DISTINCT a.category) as allCategories
            RETURN n.id as nodeId,
                   labels(n) as labels,
                   n.name as name,
                   properties(n) as properties
            """

            result = session.run(subregion_query)
            self.subregions = []
            for record in result:
                node = GraphNode(
                    node_id = record["nodeId"],
                    labels = record["labels"],
                    name = record["name"],
                    properties = record["properties"]
                )
                self.subregions.append(node)

            logger.info(f"加载了{len(self.subregions)} 个子地区节点")

            # 加载所有的景点节点
            attraction_query = """
            MATCH (n:Attraction)
            RETURN n.id as nodeId,
                   labels(n) as labels,
                   n.name as name,
                   properties(n) as properties
            """

            result = session.run(attraction_query)
            self.attractions = []
            for record in result:
                node = GraphNode(
                    node_id = record["nodeId"],
                    labels = record["labels"],
                    name = record["name"],
                    properties = record["properties"]
                )
                self.attractions.append(node)

            logger.info(f"加载了{len(self.attractions)} 个景点节点")

            # 加载所有的美食节点 - 新增部分
            food_query = """
            MATCH (n:Food)
            RETURN n.id as nodeId,
                   labels(n) as labels,
                   n.name as name,
                   properties(n) as properties
            """

            result = session.run(food_query)
            self.foods = []
            for record in result:
                node = GraphNode(
                    node_id = record["nodeId"],
                    labels = record["labels"],
                    name = record["name"],
                    properties = record["properties"]
                )
                self.foods.append(node)

            logger.info(f"加载了{len(self.foods)} 个美食节点")

            # 加载所有的餐厅节点
            restaurant_query = """
            MATCH (n:Restaurant)
            RETURN n.id as nodeId,
                   labels(n) as labels,
                   n.name as name,
                   properties(n) as properties
            """
            result = session.run(restaurant_query)
            self.restaurants = []
            for record in result:
                node = GraphNode(
                    node_id = record["nodeId"],
                    labels = record["labels"],
                    name = record["name"],
                    properties = record["properties"]
                )
                self.restaurants.append(node)

            logger.info(f"加载了{len(self.restaurants)} 个餐厅节点")

            # 加载所有的住宿节点
            hotel_query = """
            MATCH (n:Hotel)
            RETURN n.id as nodeId,
                   labels(n) as labels,
                   n.name as name,
                   properties(n) as properties
            """
            result = session.run(hotel_query)
            self.hotels = []
            for record in result:
                node = GraphNode(
                    node_id = record["nodeId"],
                    labels = record["labels"],
                    name = record["name"],
                    properties = record["properties"]
                )
                self.hotels.append(node)

            logger.info(f"加载了{len(self.hotels)} 个住宿节点")

            # 加载所有的节庆节点
            festival_query = """
            MATCH (n:Festival)
            RETURN n.id as nodeId,
                   labels(n) as labels,
                   n.name as name,
                   properties(n) as properties
            """
            result = session.run(festival_query)
            self.festivals = []
            for record in result:
                node = GraphNode(
                    node_id = record["nodeId"],
                    labels = record["labels"],
                    name = record["name"],
                    properties = record["properties"]
                )
                self.festivals.append(node)

            logger.info(f"加载了{len(self.festivals)} 个节庆节点")

            # 加载所有特产节点
            specialty_query = """
            MATCH (n:Specialty)
            RETURN n.id as nodeId,
                   labels(n) as labels,
                   n.name as name,
                   properties(n) as properties
            """
            result = session.run(specialty_query)
            self.specialties = []
            for record in result:
                node = GraphNode(
                    node_id = record["nodeId"],
                    labels = record["labels"],
                    name = record["name"],
                    properties = record["properties"]
                )
                self.specialties.append(node)

            logger.info(f"加载了{len(self.specialties)} 个特产节点")

        return {
           'cities': len(self.cities),
           'regions': len(self.regions),
           'subregions': len(self.subregions),
           'attractions': len(self.attractions),
           'foods': len(self.foods),
           'restaurants': len(self.restaurants),
           'hotels': len(self.hotels),
           'festivals': len(self.festivals),
           'specialties': len(self.specialties)
        }

    def build_documents(self) -> List[Document]:
        """
        构建旅游计划文档，集成相关的参观住宿等信息

        Returns:
              结构化的旅行计划文档列表
        """

        logger.info("正在构建旅游计划文档...")

        documents = []

        # 构建城市文档
        for city in self.cities:
            doc = Document(
                page_content=f"城市：{city.name}。{city.properties.get('description', '')}",
                metadata={
                    "node_id": city.node_id,
                    "entity_name": city.name,
                    "node_type": "City",
                    "category": "城市",
                    "doc_type": "city"
                }
            )
            documents.append(doc)

        # 构建景点文档
        for attraction in self.attractions:
            doc = Document(
                page_content=f"景点：{attraction.name}。{attraction.properties.get('description', '')}",
                metadata={
                    "node_id": attraction.node_id,
                    "entity_name": attraction.name,
                    "node_type": "Attraction",
                    "category": attraction.properties.get('category', '景点'),
                    "doc_type": "attraction"
                }
            )
            documents.append(doc)

        # 构建美食文档
        for food in self.foods:
            doc = Document(
                page_content=f"美食：{food.name}。{food.properties.get('description', '')}",
                metadata={
                    "node_id": food.node_id,
                    "entity_name": food.name,
                    "node_type": "Food",
                    "category": "美食",
                    "doc_type": "food"
                }
            )
            documents.append(doc)

        # 构建餐厅文档
        for restaurant in self.restaurants:
            doc = Document(
                page_content=f"餐厅：{restaurant.name}。{restaurant.properties.get('description', '')}",
                metadata={
                    "node_id": restaurant.node_id,
                    "entity_name": restaurant.name,
                    "node_type": "Restaurant",
                    "category": "餐厅",
                    "doc_type": "restaurant"
                }
            )
            documents.append(doc)

        # 构建住宿文档
        for hotel in self.hotels:
            doc = Document(
                page_content=f"住宿：{hotel.name}。{hotel.properties.get('description', '')}",
                metadata={
                    "node_id": hotel.node_id,
                    "entity_name": hotel.name,
                    "node_type": "Hotel",
                    "category": "住宿",
                    "doc_type": "hotel"
                }
            )
            documents.append(doc)

        # 构建节庆文档
        for festival in self.festivals:
            doc = Document(
                page_content=f"节庆：{festival.name}。{festival.properties.get('description', '')}",
                metadata={
                    "node_id": festival.node_id,
                    "entity_name": festival.name,
                    "node_type": "Festival",
                    "category": "节庆",
                    "doc_type": "festival"
                }
            )
            documents.append(doc)

        # 构建特产文档
        for specialty in self.specialties:
            doc = Document(
                page_content=f"特产：{specialty.name}。{specialty.properties.get('description', '')}",
                metadata={
                    "node_id": specialty.node_id,
                    "entity_name": specialty.name,
                    "node_type": "Specialty",
                    "category": "特产",
                    "doc_type": "specialty"
                }
            )
            documents.append(doc)

        # 设置文档列表
        self.documents = documents
        self.chunks = []

        logger.info(f"已构建 {len(documents)} 个旅游实体文档")

        return documents          
    
    def chunk_douments(self, chunk_size: int = 5000, chunk_overlap: int = 50) -> List[Document]:
        """
        对文档进行分块处理

        Args:
           chunk_size = 分块大小 
           chunk_overlap = 重叠大小 

        Returns:
           分块后的文档列表
        """

        logger.info(f"正在进行文档分块，块大小：{chunk_size}，重叠：{chunk_overlap}")
        
        if not self.documents:
            raise ValueError("请先构建文档")
        
        chunks = []
        chunk_id_counter = 0 

        for doc in self.documents:
            content = doc.page_content
            
            # 简单的按长度分块
            if len(content) <= chunk_size:
                # 内容较短，不需要分块
                chunk = Document(
                    page_content=content,
                    metadata={
                        **doc.metadata,
                        "chunk_id": f"{doc.metadata['node_id']}_chunk_{chunk_id_counter}",
                        "parent_id": doc.metadata["node_id"],
                        "chunk_index": 0,
                        "total_chunks": 1,
                        "chunk_size": len(content),
                        "doc_type": "chunk"
                    }
                )
                chunks.append(chunk)
                chunk_id_counter += 1
            else:
                # 按章节分块（基于标题）
                sections = content.split('\n## ')
                if len(sections) <= 1:
                    # 没有二级标题，按长度强制分块
                    total_chunks = (len(content) - 1) // (chunk_size - chunk_overlap) + 1

                    for i in range(total_chunks):
                        start = i * (chunk_size - chunk_overlap)
                        end = min(start + chunk_size, len(content))

                        chunk_content = content[start:end]

                        chunk = Document(
                            page_content=chunk_content,
                            metadata={
                                **doc.metadata,
                                "chunk_id": f"{doc.metadata['node_id']}_chunk_{chunk_id_counter}",
                                "parent_id": doc.metadata["node_id"],
                                "chunk_index": i,
                                "total_chunks": total_chunks,
                                "chunk_size": len(chunk_content),
                                "doc_type": "chunk"
                            }
                        )
                        chunks.append(chunk)
                        chunk_id_counter += 1
                else:
                    # 按章节分块
                    total_chunks = len(sections)
                    for i, section in enumerate(sections):
                        if i == 0:
                            # 第一个部分包含标题
                            chunk_content = section
                        else:
                            # 其他部分添加章节标题
                            chunk_content = f"## {section}"

                        chunk = Document(
                            page_content=chunk_content,
                            metadata={
                                **doc.metadata,
                                "chunk_id": f"{doc.metadata['node_id']}_chunk_{chunk_id_counter}",
                                "parent_id": doc.metadata["node_id"],
                                "chunk_index": i,
                                "total_chunks": total_chunks,
                                "chunk_size": len(chunk_content),
                                "doc_type": "chunk",
                                "section_title": section.split('\n')[0] if i > 0 else "主标题"
                            }
                        )
                        chunks.append(chunk)
                        chunk_id_counter += 1
        
        self.chunks = chunks
        logger.info(f"文档分块完成，共生成 {len(chunks)} 个块")
        return chunks
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据统计信息

        Returns:
            统计信息字典
        """
        stats = {
           'total_cities': len(self.cities),
           'total_regions': len(self.regions),
           'total_subregions': len(self.subregions),
           'total_attractions': len(self.attractions),
           'total_foods': len(self.foods),
           'total_restaurants': len(self.restaurants),
           'total_hotels': len(self.hotels),
           'total_festivals': len(self.festivals),
           'total_specialties': len(self.specialties)
        }
        
        if self.documents:
            # 分类统计
            categories = {}
            cuisines = {}
            difficulties = {}
            
            for doc in self.documents:
                category = doc.metadata.get('category', '未知')
                categories[category] = categories.get(category, 0) + 1
                
                cuisine = doc.metadata.get('cuisine_type', '未知')
                cuisines[cuisine] = cuisines.get(cuisine, 0) + 1
                
                difficulty = doc.metadata.get('difficulty', 0)
                difficulties[str(difficulty)] = difficulties.get(str(difficulty), 0) + 1
            
            stats.update({
                'categories': categories,
                'cuisines': cuisines,
                'difficulties': difficulties,
                'avg_content_length': sum(doc.metadata.get('content_length', 0) for doc in self.documents) / len(self.documents),
                'avg_chunk_size': sum(chunk.metadata.get('chunk_size', 0) for chunk in self.chunks) / len(self.chunks) if self.chunks else 0
            })
        
        return stats
    

    
    def __del__(self):
        """析构函数，确保关闭连接"""
        self.close() 