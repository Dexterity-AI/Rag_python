"""
生成集成模块
"""

import os
import logging
from typing import List

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.documents import Document
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

class GenerationIntegrationModule:
    """旅游生成集成模块 - 负责LLM集成和旅游问答生成"""

    def __init__(self, config=None, temperature: float = 0.1, max_tokens: int = 2048):
        """
        初始化生成集成模块

        Args:
            config: 配置对象（可选）
            temperature: 生成温度
            max_tokens: 最大token数
        """
        self.config = config
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = None

        # 初始化GLM-4模型
        self.setup_glm4()

    def setup_glm4(self):
        """初始化GLM-4模型"""
        logger.info("正在初始化GLM-4模型")

        # 获取API密钥
        api_key = os.getenv("GLM_API_KEY")
        if not api_key:
            raise ValueError("请设置环境变量: GLM_API_KEY")

        # 创建GLM-4实例
        self.llm = ChatOpenAI(
            model="glm-4",
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            openai_api_key=api_key,
            openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
        )

        logger.info("GLM-4模型初始化完成")
    
    def generate_basic_answer(self, query: str, context_docs: List[Document]) -> str:
        """
        生成基础回答

        Args:
            query: 用户查询
            context_docs: 上下文文档列表

        Returns:
            生成的回答
        """
        context = self._build_context(context_docs)

        prompt = ChatPromptTemplate.from_template("""
你是一位专业的旅游顾问。请根据以下旅游信息回答用户的问题。

用户问题: {question}

相关旅游信息:
{context}

请提供详细、实用的回答。如果信息不足，请诚实说明。

回答:""")

        # 使用LCEL构建链
        chain = (
            {"question": RunnablePassthrough(), "context": lambda _: context}
            | prompt
            | self.llm
            | StrOutputParser()
        )

        response = chain.invoke(query)
        return response
    
    def generate_detailed_guide_answer(self, query: str, context_docs: List[Document]) -> str:
        """
        生成详细旅游指南回答

        Args:
            query: 用户查询
            context_docs: 上下文文档列表

        Returns:
            详细的旅游指南回答
        """
        context = self._build_context(context_docs)

        prompt = ChatPromptTemplate.from_template("""
你是一位专业的旅游规划师。请根据旅游信息，为用户提供详细的旅游指南。

用户问题: {question}

相关旅游信息:
{context}

请灵活组织回答，建议包含以下部分（可根据实际内容调整）：

## 🏞️ 景点介绍
[简要介绍景点特色和亮点]

## 📍 基本信息
[地址、开放时间、门票价格、联系方式等]

## 🚗 交通指南
[如何到达，包括公共交通和自驾路线]

## 💡 游览建议
[最佳游览时间、推荐路线、注意事项等]

注意：
- 根据实际内容灵活调整结构
- 不要强行填充无关内容
- 重点突出实用性和可操作性
- 如果没有额外的建议要分享，可以省略相应部分

回答:""")

        chain = (
            {"question": RunnablePassthrough(), "context": lambda _: context}
            | prompt
            | self.llm
            | StrOutputParser()
        )

        response = chain.invoke(query)
        return response
    
    def query_rewrite(self, query: str) -> str:
        """
        智能查询重写 - 让大模型判断是否需要重写查询

        Args:
            query: 原始查询

        Returns:
            重写后的查询或原查询
        """
        prompt = PromptTemplate(
            template="""
你是一个智能查询分析助手。请分析用户的查询，判断是否需要重写以提高旅游信息搜索效果。

原始查询: {query}

分析规则：
1. **具体明确的查询**（直接返回原查询）：
   - 包含具体景点名称：如"故宫怎么去"、"长城门票价格"
   - 明确的旅游询问：如"北京有什么好玩的"、"上海迪士尼攻略"
   - 具体的交通住宿：如"机场到市区怎么走"、"酒店推荐"

2. **模糊不清的查询**（需要重写）：
   - 过于宽泛：如"旅游"、"去哪玩"、"推荐个地方"
   - 缺乏具体信息：如"国内"、"国外"、"便宜的"
   - 口语化表达：如"想去玩"、"有什么好去处"

重写原则：
- 保持原意不变
- 增加相关旅游术语
- 优先推荐热门景点
- 保持简洁性

示例：
- "旅游" → "热门旅游景点推荐"
- "去哪玩" → "周末旅游景点推荐"
- "推荐个地方" → "国内热门旅游目的地"
- "国内" → "国内经典旅游路线"
- "故宫怎么去" → "故宫怎么去"（保持原查询）
- "北京有什么好玩的" → "北京有什么好玩的"（保持原查询）

请输出最终查询（如果不需要重写就返回原查询）:""",
            input_variables=["query"]
        )

        chain = (
            {"query": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )

        response = chain.invoke(query).strip()

        # 记录重写结果
        if response != query:
            logger.info(f"查询已重写: '{query}' → '{response}'")
        else:
            logger.info(f"查询无需重写: '{query}'")

        return response



    def query_router(self, query: str) -> str:
        """
        查询路由 - 根据查询类型选择不同的处理方式

        Args:
            query: 用户查询

        Returns:
            路由类型 ('list', 'detail', 'general')
        """
        prompt = ChatPromptTemplate.from_template("""
根据用户的问题，将其分类为以下三种类型之一：

1. 'list' - 用户想要获取景点列表或推荐，只需要景点名称
   例如：推荐几个景点、北京有什么好玩的、给我3个必去的地方

2. 'detail' - 用户想要具体的旅游信息或详细指南
   例如：故宫怎么去、门票多少钱、开放时间、旅游攻略

3. 'general' - 其他一般性问题
   例如：什么是文化旅游、旅游注意事项、最佳旅游季节

请只返回分类结果：list、detail 或 general

用户问题: {query}

分类结果:""")

        chain = (
            {"query": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )

        result = chain.invoke(query).strip().lower()

        # 确保返回有效的路由类型
        if result in ['list', 'detail', 'general']:
            return result
        else:
            return 'general'  # 默认类型

    def generate_list_answer(self, query: str, context_docs: List[Document]) -> str:
        """
        生成列表式回答 - 适用于推荐类查询

        Args:
            query: 用户查询
            context_docs: 上下文文档列表

        Returns:
            列表式回答
        """
        if not context_docs:
            return "抱歉，没有找到相关的旅游景点信息。"

        # 提取地点名称
        location_names = []
        for doc in context_docs:
            location_name = doc.metadata.get('location_name', '未知地点')
            if location_name not in location_names:
                location_names.append(location_name)

        # 构建简洁的列表回答
        if len(location_names) == 1:
            return f"为您推荐：{location_names[0]}"
        elif len(location_names) <= 3:
            return f"为您推荐以下景点：\n" + "\n".join([f"{i+1}. {name}" for i, name in enumerate(location_names)])
        else:
            return f"为您推荐以下景点：\n" + "\n".join([f"{i+1}. {name}" for i, name in enumerate(location_names[:3])]) + f"\n\n还有其他 {len(location_names)-3} 个景点可供选择。"

    def generate_basic_answer_stream(self, query: str, context_docs: List[Document]):
        """
        生成基础回答 - 流式输出

        Args:
            query: 用户查询
            context_docs: 上下文文档列表

        Yields:
            生成的回答片段
        """
        context = self._build_context(context_docs)

        prompt = ChatPromptTemplate.from_template("""
你是一位专业的旅游顾问。请根据以下旅游信息回答用户的问题。

用户问题: {question}

相关旅游信息:
{context}

请提供详细、实用的回答。如果信息不足，请诚实说明。

回答:""")

        chain = (
            {"question": RunnablePassthrough(), "context": lambda _: context}
            | prompt
            | self.llm
            | StrOutputParser()
        )

        for chunk in chain.stream(query):
            yield chunk

    def generate_detailed_guide_answer_stream(self, query: str, context_docs: List[Document]):
        """
        生成详细旅游指南回答 - 流式输出

        Args:
            query: 用户查询
            context_docs: 上下文文档列表

        Yields:
            详细旅游指南回答片段
        """
        context = self._build_context(context_docs)

        prompt = ChatPromptTemplate.from_template("""
你是一位专业的旅游规划师。请根据旅游信息，为用户提供详细的旅游指南。

用户问题: {question}

相关旅游信息:
{context}

请灵活组织回答，建议包含以下部分（可根据实际内容调整）：

## 🏞️ 景点介绍
[简要介绍景点特色和亮点]

## 📍 基本信息
[地址、开放时间、门票价格、联系方式等]

## 🚗 交通指南
[如何到达，包括公共交通和自驾路线]

## 💡 游览建议
[最佳游览时间、推荐路线、注意事项等]

注意：
- 根据实际内容灵活调整结构
- 不要强行填充无关内容
- 重点突出实用性和可操作性

回答:""")

        chain = (
            {"question": RunnablePassthrough(), "context": lambda _: context}
            | prompt
            | self.llm
            | StrOutputParser()
        )

        for chunk in chain.stream(query):
            yield chunk

    def _build_context(self, docs: List[Document], max_length: int = 2000) -> str:
        """
        构建上下文字符串

        Args:
            docs: 文档列表
            max_length: 最大长度

        Returns:
            格式化的上下文字符串
        """
        if not docs:
            return "暂无相关旅游信息。"

        context_parts = []
        current_length = 0

        for i, doc in enumerate(docs, 1):
            # 添加元数据信息
            metadata_info = f"【旅游信息 {i}】"
            if 'location_name' in doc.metadata:
                metadata_info += f" {doc.metadata['location_name']}"
            if 'category' in doc.metadata:
                metadata_info += f" | 分类: {doc.metadata['category']}"
            if 'city' in doc.metadata:
                metadata_info += f" | 城市: {doc.metadata['city']}"
            if 'price_level' in doc.metadata:
                metadata_info += f" | 价格: {doc.metadata['price_level']}"

            # 构建文档文本
            doc_text = f"{metadata_info}\n{doc.page_content}\n"

            # 检查长度限制
            if current_length + len(doc_text) > max_length:
                break

            context_parts.append(doc_text)
            current_length += len(doc_text)

        return "\n" + "="*50 + "\n".join(context_parts)