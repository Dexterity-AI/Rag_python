"""
智能查询路由器
根据查询特点自动选择最适合的检索策略：
- 传统混合检索：适合简单的信息查找
- 图RAG检索：适合复杂的关系推理和知识发现
"""

import hashlib
import logging
import re
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum

from langchain_core.documents import Document
from utils.llm_parser import parse_llm_json_response

logger = logging.getLogger(__name__)

class SearchStrategy(Enum):
    """搜索策略枚举"""
    HYBRID_TRADITIONAL = "hybrid_traditional"  # 传统混合检索
    GRAPH_RAG = "graph_rag"  # 图RAG检索
    COMBINED = "combined"  # 组合策略
    
@dataclass
class QueryAnalysis:
    """查询分析结果"""
    query_complexity: float  # 查询复杂度 (0-1)
    relationship_intensity: float  # 关系密集度 (0-1)
    reasoning_required: bool  # 是否需要推理
    entity_count: int  # 实体数量
    recommended_strategy: SearchStrategy
    confidence: float  # 推荐置信度
    reasoning: str  # 推荐理由

class IntelligentQueryRouter:
    """
    轻量级智能查询路由器

    核心能力：
    1. 查询复杂度分析：识别简单查找 vs 复杂推理（基于规则，无LLM）
    2. 关系密集度评估：判断是否需要图结构优势
    3. 策略自动选择：路由到最适合的检索引擎
    4. 路由决策缓存：避免重复分析相同查询

    设计原则：
    - 优先使用轻量级规则分类，避免LLM调用
    - 仅在配置启用时才使用LLM进行深度分析
    - 缓存路由决策以提高性能
    """

    def __init__(self,
                 traditional_retrieval,  # 传统混合检索模块
                 graph_rag_retrieval,    # 图RAG检索模块
                 llm_client,
                 config):
        self.traditional_retrieval = traditional_retrieval
        self.graph_rag_retrieval = graph_rag_retrieval
        self.llm_client = llm_client
        self.config = config

        # 路由决策缓存
        self._decision_cache = {}
        self._cache_max_size = getattr(config, 'router_cache_size', 1000)

        # 路由统计
        self.route_stats = {
            "traditional_count": 0,
            "graph_rag_count": 0,
            "combined_count": 0,
            "total_queries": 0,
            "cache_hits": 0,
            "rule_based_count": 0,
            "llm_based_count": 0
        }

        # 配置：是否启用LLM分析（默认关闭）
        self._enable_llm_analysis = getattr(config, 'enable_llm_routing', False)
        
    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        分析查询特征，决定最佳检索策略
        优先使用轻量级规则分析，仅在配置启用时使用LLM
        """
        logger.info(f"分析查询特征: {query}")

        # 1. 检查缓存
        cache_key = self._get_cache_key(query)
        if cache_key in self._decision_cache:
            self.route_stats["cache_hits"] += 1
            logger.info(f"路由决策缓存命中: {query[:50]}...")
            return self._decision_cache[cache_key]

        # 2. 优先使用规则分析（轻量级，无LLM调用）
        analysis = None

        if self._enable_llm_analysis:
            # 仅在配置启用时尝试LLM分析
            try:
                analysis = self._llm_based_analysis(query)
                self.route_stats["llm_based_count"] += 1
            except Exception as e:
                logger.warning(f"LLM分析失败，回退到规则分析: {e}")

        if analysis is None:
            # 默认使用规则分析
            analysis = self._rule_based_analysis(query)
            self.route_stats["rule_based_count"] += 1

        # 3. 缓存结果
        self._cache_decision(cache_key, analysis)

        logger.info(f"查询分析完成: {analysis.recommended_strategy.value} "
                   f"(复杂度: {analysis.query_complexity:.2f}, 置信度: {analysis.confidence:.2f})")
        return analysis

    def _get_cache_key(self, query: str) -> str:
        """生成查询的缓存键"""
        import hashlib
        # 标准化查询：去除空格和标点，转小写
        normalized = ''.join(c.lower() for c in query if c.isalnum())
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    def _cache_decision(self, key: str, analysis: QueryAnalysis):
        """缓存路由决策"""
        # 限制缓存大小，避免内存无限增长
        if len(self._decision_cache) >= self._cache_max_size:
            # 移除最早的10%条目
            keys_to_remove = list(self._decision_cache.keys())[:self._cache_max_size // 10]
            for k in keys_to_remove:
                del self._decision_cache[k]

        self._decision_cache[key] = analysis
    
    def _rule_based_analysis(self, query: str) -> QueryAnalysis:
        """
        基于规则的轻量级分析
        快速、可靠，零LLM调用
        """
        query_lower = query.lower()
        query_len = len(query)

        # ===== 1. 复杂度分析 =====
        # 高复杂度指示词（需要多跳推理或复杂分析）
        high_complexity_keywords = {
            '为什么': 0.25, '如何': 0.2, '关系': 0.2, '影响': 0.2,
            '原因': 0.2, '比较': 0.25, '区别': 0.25, '对比': 0.25,
            '攻略': 0.3, '路线规划': 0.3, '行程安排': 0.3, '最佳方案': 0.25
        }
        # 中等复杂度指示词
        medium_complexity_keywords = {
            '推荐': 0.15, '建议': 0.1, '哪些': 0.1, '有什么': 0.1,
            '怎么样': 0.1, '好玩': 0.1, '值得': 0.1
        }

        complexity_score = 0.0
        for kw, weight in high_complexity_keywords.items():
            if kw in query_lower:
                complexity_score += weight
        for kw, weight in medium_complexity_keywords.items():
            if kw in query_lower:
                complexity_score += weight

        # 查询长度因素（较长查询通常更复杂）
        if query_len > 30:
            complexity_score += 0.1
        if query_len > 50:
            complexity_score += 0.1

        complexity = min(1.0, complexity_score)

        # ===== 2. 关系密集度分析 =====
        # 实体关系指示词
        relation_keywords = {
            '搭配': 0.25, '组合': 0.25, '相关': 0.2, '联系': 0.2,
            '附近': 0.2, '周边': 0.2, '周围': 0.2, '一起': 0.15,
            '和': 0.1, '与': 0.1, '以及': 0.1, '还有': 0.1,
            '路线': 0.2, '行程': 0.2, '顺序': 0.15, '连接': 0.2
        }

        relation_score = sum(weight for kw, weight in relation_keywords.items() if kw in query_lower)

        # 多实体指示（逗号、顿号分隔的列表）
        entity_separators = query.count('、') + query.count(',') + query.count('，')
        if entity_separators >= 2:
            relation_score += 0.2 * entity_separators

        relation_intensity = min(1.0, relation_score)

        # ===== 3. 实体计数（基于规则和启发式） =====
        # 常见旅游实体词典
        common_entities = {
            '北京', '上海', '广州', '深圳', '杭州', '南京', '西安', '成都', '重庆', '武汉',
            '故宫', '长城', '天安门', '颐和园', '天坛', '北海公园', '圆明园',
            '西藏', '拉萨', '布达拉宫', '纳木错', '林芝',
            '黄山', '泰山', '华山', '峨眉山', '张家界',
            '西湖', '九寨沟', '桂林', '丽江', '大理', '三亚',
            '迪士尼', '欢乐谷', '海洋公园', '动物园', '博物馆',
            '机场', '火车站', '地铁站', '酒店', '民宿', '宾馆',
            '美食', '小吃', '特产', '餐厅', '饭店'
        }

        entity_count = sum(1 for entity in common_entities if entity in query)

        # 基于分隔符估算实体数量
        estimated_entities = len([w for w in re.split(r'[、，,\s]+', query) if len(w) >= 2])
        entity_count = max(1, entity_count, estimated_entities // 2)
        entity_count = min(entity_count, 10)  # 上限10个

        # ===== 4. 决策逻辑 =====
        # Graph RAG 触发条件：高复杂度 或 高关系密度 或 明确的多实体查询
        if complexity >= 0.6 or relation_intensity >= 0.5 or entity_count >= 4:
            strategy = SearchStrategy.GRAPH_RAG
            confidence = 0.75 + min(0.15, complexity * 0.1)
            reasoning = f"复杂查询需要图推理：复杂度{complexity:.2f}，关系密度{relation_intensity:.2f}，实体数{entity_count}"

        # Combined 触发条件：推荐类查询 或 中等复杂度
        elif '推荐' in query or '哪些' in query or '有什么' in query or complexity >= 0.4:
            strategy = SearchStrategy.COMBINED
            confidence = 0.7
            reasoning = f"推荐类查询使用组合策略：复杂度{complexity:.2f}"

        # 默认：传统混合检索（简单信息查询）
        else:
            strategy = SearchStrategy.HYBRID_TRADITIONAL
            confidence = 0.85
            reasoning = f"简单查询使用传统检索：复杂度{complexity:.2f}"

        return QueryAnalysis(
            query_complexity=complexity,
            relationship_intensity=relation_intensity,
            reasoning_required=complexity >= 0.4,
            entity_count=entity_count,
            recommended_strategy=strategy,
            confidence=confidence,
            reasoning=reasoning
        )

    def _llm_based_analysis(self, query: str) -> QueryAnalysis:
        """
        基于LLM的深度分析
        用于复杂查询场景
        """
        analysis_prompt = f"""
        作为RAG系统的查询分析专家，请深度分析以下查询的特征：

        查询：{query}

        请从以下维度分析：

        1. 查询复杂度 (0-1)：
           - 0.0-0.3: 简单信息查找
           - 0.4-0.7: 中等复杂度
           - 0.8-1.0: 高复杂度推理

        2. 关系密集度 (0-1)：
           - 0.0-0.3: 单一实体信息
           - 0.4-0.7: 实体间关系
           - 0.8-1.0: 复杂关系网络

        3. 推理需求：是否需要多跳推理、因果分析、对比分析？

        4. 实体识别：查询中包含多少个明确实体？

        推荐策略：hybrid_traditional（简单查找）、graph_rag（复杂推理）、combined（两者结合）

        只返回JSON，不要其他文字：
        {{"query_complexity": 0.5, "relationship_intensity": 0.5, "reasoning_required": false, "entity_count": 2, "recommended_strategy": "hybrid_traditional", "confidence": 0.8, "reasoning": "分析理由"}}
        """

        response = self.llm_client.chat.completions.create(
            model=self.config.llm_model,
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.1,
            max_tokens=400
        )

        content = response.choices[0].message.content
        result = parse_llm_json_response(content)

        if result is None:
            raise ValueError("无法从LLM响应中解析JSON")

        return QueryAnalysis(
            query_complexity=result.get("query_complexity", 0.5),
            relationship_intensity=result.get("relationship_intensity", 0.5),
            reasoning_required=result.get("reasoning_required", False),
            entity_count=result.get("entity_count", 1),
            recommended_strategy=SearchStrategy(result.get("recommended_strategy", "hybrid_traditional")),
            confidence=result.get("confidence", 0.5),
            reasoning=result.get("reasoning", "LLM分析")
        )
    
    def route_query(self, query: str, top_k: int = 5) -> Tuple[List[Document], QueryAnalysis]:
        """
        智能路由查询到最适合的检索引擎
        """
        logger.info(f"开始智能路由: {query}")
        
        # 1. 分析查询特征
        analysis = self.analyze_query(query)
        
        # 2. 更新统计
        self._update_route_stats(analysis.recommended_strategy)
        
        # 3. 根据策略执行检索
        documents = []
        
        try:
            if analysis.recommended_strategy == SearchStrategy.HYBRID_TRADITIONAL:
                logger.info("使用传统混合检索")
                documents = self.traditional_retrieval.hybrid_search(query, top_k)
                
            elif analysis.recommended_strategy == SearchStrategy.GRAPH_RAG:
                logger.info("🕸️ 使用图RAG检索")
                documents = self.graph_rag_retrieval.graph_rag_search(query, top_k)
                
            elif analysis.recommended_strategy == SearchStrategy.COMBINED:
                logger.info("🔄 使用组合检索策略")
                documents = self._combined_search(query, top_k)
            
            # 4. 结果后处理
            documents = self._post_process_results(documents, analysis)
            
            logger.info(f"路由完成，返回 {len(documents)} 个结果")
            return documents, analysis
            
        except Exception:
            # 静默降级到传统检索，不打印错误日志
            documents = self.traditional_retrieval.hybrid_search(query, top_k)
            return documents, analysis
    
    def _combined_search(self, query: str, top_k: int) -> List[Document]:
        """
        组合搜索策略：结合传统检索和图RAG的优势
        """
        # 分配结果数量
        traditional_k = max(1, top_k // 2)
        graph_k = top_k - traditional_k
        
        # 执行两种检索
        traditional_docs = self.traditional_retrieval.hybrid_search(query, traditional_k)
        graph_docs = self.graph_rag_retrieval.graph_rag_search(query, graph_k)
        
        # 合并和去重
        combined_docs = []
        seen_contents = set()
        
        # 交替添加结果（Round-robin）
        max_len = max(len(traditional_docs), len(graph_docs))
        for i in range(max_len):
            # 先添加图RAG结果（通常质量更高）
            if i < len(graph_docs):
                doc = graph_docs[i]
                content_hash = hashlib.md5(doc.page_content[:100].encode()).hexdigest()[:16]
                if content_hash not in seen_contents:
                    seen_contents.add(content_hash)
                    doc.metadata["search_source"] = "graph_rag"
                    combined_docs.append(doc)

            # 再添加传统检索结果
            if i < len(traditional_docs):
                doc = traditional_docs[i]
                content_hash = hashlib.md5(doc.page_content[:100].encode()).hexdigest()[:16]
                if content_hash not in seen_contents:
                    seen_contents.add(content_hash)
                    doc.metadata["search_source"] = "traditional"
                    combined_docs.append(doc)
        
        return combined_docs[:top_k]
    
    def _post_process_results(self, documents: List[Document], analysis: QueryAnalysis) -> List[Document]:
        """
        结果后处理：根据查询分析优化结果
        """
        for doc in documents:
            # 添加路由信息到元数据
            doc.metadata.update({
                "route_strategy": analysis.recommended_strategy.value,
                "query_complexity": analysis.query_complexity,
                "route_confidence": analysis.confidence
            })
        
        return documents
    
    def _update_route_stats(self, strategy: SearchStrategy):
        """更新路由统计"""
        self.route_stats["total_queries"] += 1
        
        if strategy == SearchStrategy.HYBRID_TRADITIONAL:
            self.route_stats["traditional_count"] += 1
        elif strategy == SearchStrategy.GRAPH_RAG:
            self.route_stats["graph_rag_count"] += 1
        elif strategy == SearchStrategy.COMBINED:
            self.route_stats["combined_count"] += 1
    
    def get_route_statistics(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        total = self.route_stats["total_queries"]
        if total == 0:
            return self.route_stats

        stats = {
            **self.route_stats,
            "traditional_ratio": self.route_stats["traditional_count"] / total,
            "graph_rag_ratio": self.route_stats["graph_rag_count"] / total,
            "combined_ratio": self.route_stats["combined_count"] / total,
            "cache_hit_ratio": self.route_stats["cache_hits"] / total if total > 0 else 0,
            "llm_usage_ratio": self.route_stats["llm_based_count"] / total if total > 0 else 0,
            "rule_usage_ratio": self.route_stats["rule_based_count"] / total if total > 0 else 0,
            "cache_size": len(self._decision_cache)
        }
        return stats

    def clear_cache(self):
        """清空路由决策缓存"""
        self._decision_cache.clear()
        logger.info("路由决策缓存已清空")
    
    def explain_routing_decision(self, query: str) -> str:
        """解释路由决策过程"""
        analysis = self.analyze_query(query)
        
        explanation = f"""
        查询路由分析报告
        
        查询：{query}
        
        特征分析：
        - 复杂度：{analysis.query_complexity:.2f} ({'简单' if analysis.query_complexity < 0.4 else '中等' if analysis.query_complexity < 0.8 else '复杂'})
        - 关系密集度：{analysis.relationship_intensity:.2f} ({'单一实体' if analysis.relationship_intensity < 0.4 else '实体关系' if analysis.relationship_intensity < 0.8 else '复杂关系网络'})
        - 推理需求：{'是' if analysis.reasoning_required else '否'}
        - 实体数量：{analysis.entity_count}
        
        推荐策略：{analysis.recommended_strategy.value}
        置信度：{analysis.confidence:.2f}
        
        决策理由：{analysis.reasoning}
        """
        
        return explanation

 