"""
生成集成模块
负责LLM集成和旅游问答生成
"""

import logging
import os
import time
from typing import List, Iterator, Optional
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.documents import Document
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from openai import OpenAI
from dotenv import load_dotenv
from cache import get_cache_manager

# 加载环境变量（从项目根目录的 config 文件夹）
_current_file = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_file)
env_path = os.path.join(_project_root, '..', 'config', '.env')
load_dotenv(env_path)

logger = logging.getLogger(__name__)

class GenerationIntegrationModule:
    """生成集成模块 - 负责答案生成"""

    def __init__(self, config=None, model_name: str = "gpt-3.5-turbo", temperature: float = 0.1, max_tokens: int = 2048):
        """
        初始化生成集成模块

        Args:
            config: 配置对象（可选）
            model_name: 模型名称
            temperature: 生成温度
            max_tokens: 最大token数
        """
        self.config = config
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = None

        # 初始化LLM模型
        self.setup_llm()

        # 初始化LLM缓存
        cache_manager = get_cache_manager()
        self.llm_cache = cache_manager.llm_cache

    def setup_llm(self):
        """初始化LLM模型"""
        logger.info("正在初始化LLM模型")

        # 优先从config获取配置，否则从环境变量获取
        if self.config and hasattr(self.config, 'llm_api_key') and self.config.llm_api_key:
            api_key = self.config.llm_api_key
            base_url = self.config.llm_base_url
            self.model_name = self.config.llm_model
        else:
            # 从环境变量获取（支持多种变量名）
            api_key = (os.getenv("LLM_API_KEY") or 
                      os.getenv("ZHIPU_API_KEY") or 
                      os.getenv("GLM_API_KEY") or 
                      os.getenv("OPENAI_API_KEY"))
            base_url = os.getenv("LLM_BASE_URL")
            model_name = os.getenv("LLM_MODEL")
            if model_name:
                self.model_name = model_name

        if not api_key:
            raise ValueError("请设置环境变量: LLM_API_KEY 或 ZHIPU_API_KEY")

        try:
            # 设置超时时间（本地模型需要更长时间）
            timeout = float(os.getenv("REQUEST_TIMEOUT", "60.0"))

            if base_url:
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    timeout=timeout
                )
                logger.info(f"LLM模型初始化完成，超时时间: {timeout}秒")
            else:
                self.client = OpenAI(
                    api_key=api_key,
                    timeout=timeout
                )
                logger.info(f"OpenAI模型初始化完成，超时时间: {timeout}秒")
        except Exception as e:
            logger.error(f"LLM模型初始化失败: {e}")
            raise

    def generate_adaptive_answer(self, question: str, documents: List[Document]) -> str:
        """
        智能统一答案生成
        自动适应不同类型的查询，无需预先分类
        支持缓存机制

        Args:
            question: 用户问题
            documents: 文档列表

        Returns:
            生成的回答
        """
        # 尝试从缓存获取
        if self.llm_cache:
            cached_response = self.llm_cache.get_for_generation(
                question=question,
                documents=documents,
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            if cached_response is not None:
                logger.info(f"LLM缓存命中: {question[:50]}...")
                return cached_response

        # 构建上下文
        context_parts = []

        for doc in documents:
            content = doc.page_content.strip()
            if content:
                # 添加检索层级信息（如果有的话）
                level = doc.metadata.get('retrieval_level', '')
                if level:
                    context_parts.append(f"[{level.upper()}] {content}")
                else:
                    context_parts.append(content)

        context = "\n".join(context_parts)

        # 智能提示词模板
        prompt = f"""
        你是一位专业的旅游顾问。请根据以下旅游信息回答用户的问题。

        检索到的相关信息：
        {context}

        用户问题：{question}

        请提供准确、实用的回答。根据问题的性质：
        - 如果是询问多个景点，请提供清晰的列表
        - 如果是询问具体信息（如门票、开放时间），请提供详细信息
        - 如果是询问交通或住宿，请提供实用建议
        - 如果是一般性咨询，请提供综合性回答

        回答：
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            result = response.choices[0].message.content.strip()

            # 缓存结果
            if self.llm_cache:
                self.llm_cache.set_for_generation(
                    question=question,
                    documents=documents,
                    response=result,
                    model=self.model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                logger.debug(f"LLM结果已缓存: {question[:50]}...")

            return result

        except Exception as e:
            logger.error(f"答案生成失败: {e}")
            return f"抱歉，生成回答时出现错误：{str(e)}"

    def generate_adaptive_answer_stream(self, question: str, documents: List[Document], max_retries: int = 3) -> Iterator[str]:
        """
        智能统一流式答案生成（带重试机制）

        Args:
            question: 用户问题
            documents: 文档列表
            max_retries: 最大重试次数

        Yields:
            回答片段
        """
        # 构建上下文
        context_parts = []

        for doc in documents:
            content = doc.page_content.strip()
            if content:
                # 添加检索层级信息
                level = doc.metadata.get('retrieval_level', '')
                if level:
                    context_parts.append(f"[{level.upper()}] {content}")
                else:
                    context_parts.append(content)

        context = "\n".join(context_parts)

        # 智能提示词模板
        prompt = f"""
        你是一位专业的旅游顾问。请基于以下信息回答用户的问题。

        检索到的相关信息：
        {context}

        用户问题：{question}

        请提供准确、实用的回答。根据问题的性质：
        - 如果是询问多个景点，请提供清晰的列表
        - 如果是询问具体信息（如门票、开放时间），请提供详细信息
        - 如果是询问交通或住宿，请提供实用建议
        - 如果是一般性咨询，请提供综合性回答

        回答：
        """

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=True,
                    timeout=60  # 添加超时设置
                )

                if attempt == 0:
                    print("开始流式回答生成...")
                else:
                    print(f"第{attempt + 1}次尝试流式生成...")

                full_response = ""
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield content

                # 如果成功完成，退出重试循环
                return

            except Exception as e:
                logger.warning(f"流式生成第{attempt + 1}次尝试失败: {e}")

                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 递增等待时间
                    print(f"⚠️ 连接中断，{wait_time}秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    # 所有重试都失败，使用非流式作为后备
                    logger.error("流式生成完全失败，切换到标准模式...")

                    try:
                        fallback_response = self.generate_adaptive_answer(question, documents)
                        yield fallback_response
                        return
                    except Exception as fallback_error:
                        logger.error(f"后备生成也失败: {fallback_error}")
                        error_msg = f"抱歉，生成回答时出现网络错误，请稍后重试。错误信息：{str(fallback_error)}"
                        yield error_msg
                        return

    def query_rewrite(self, query: str) -> str:
        """
        智能查询重写 - 让大模型判断是否需要重写查询以提高旅游信息搜索效果

        Args:
            query: 原始查询

        Returns:
            重写后的查询或原始查询
        """
        prompt = PromptTemplate(
            template="""
        你是一个智能查询分析助手。请分析用户的查询，判断是否需要重写以提高旅游信息搜索效果。

        原始查询：{query}

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
        - 保持原查询意图不变
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

        请只输出最终查询（如果不需要重写就返回原查询）：
        """,
            input_variables=["query"]
        )

        chain = (
            {"query": RunnablePassthrough()}
            | prompt
            | self.client
            | StrOutputParser()
        )

        try:
            response = chain.invoke(query).strip()
            # 记录重写结果
            if response != query:
                logger.info(f"查询已重写: '{query}' → '{response}'")
            else:
                logger.info(f"查询无需重写: '{query}'")
            return response
        except Exception as e:
            logger.error(f"查询重写失败: {e}")
            return query

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
            location_name = doc.metadata.get('location_name',
                           doc.metadata.get('name',
                           doc.metadata.get('entity_name', '未知地点')))
            if location_name and location_name not in location_names:
                location_names.append(location_name)

        # 构建简洁的列表回答
        if len(location_names) == 1:
            return f"为您推荐：{location_names[0]}"
        elif len(location_names) <= 3:
            return f"为您推荐以下景点：\n" + "\n".join([f"{i+1}. {name}" for i, name in enumerate(location_names)])
        else:
            return f"为您推荐以下景点：\n" + "\n".join([f"{i+1}. {name}" for i, name in enumerate(location_names[:3])]) + f"\n\n还有其他{len(location_names)-3}个景点可供选择。"

    def generate_basic_answer_stream(self, query: str, context_docs: List[Document]) -> Iterator[str]:
        """
        生成基础回答 - 流式输出

        Args:
            query: 用户查询
            context_docs: 上下文文档列表

        Yields:
            回答片段
        """
        context = self._build_context(context_docs)

        prompt = ChatPromptTemplate.from_template("""
        你是一位专业的旅游顾问。请根据以下旅游信息回答用户的问题。

        用户问题：{query}
        相关旅游信息：
        {context}
        请提供详细、实用的回答。如果信息不足，请诚实说明。

        回答：
        """)

        chain = (
            {"query": RunnablePassthrough(), "context": lambda _: context}
            | prompt
            | self.client
            | StrOutputParser()
        )

        try:
            for chunk in chain.stream(query):
                yield chunk
        except Exception as e:
            logger.error(f"流式回答生成失败: {e}")
            yield "抱歉，生成回答时出现错误。"

    def generate_detailed_guide_answer_stream(self, query: str, context_docs: List[Document]) -> Iterator[str]:
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

        用户问题：{query}
        相关旅游信息：
        {context}
        请灵活组织回答，建议包含以下部分（可根据实际内容调整）：

        ## 🏛️ 景点介绍
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

        回答：
        """)

        chain = (
            {"query": RunnablePassthrough(), "context": lambda _: context}
            | prompt
            | self.client
            | StrOutputParser()
        )

        try:
            for chunk in chain.stream(query):
                yield chunk
        except Exception as e:
            logger.error(f"详细指南流式生成失败: {e}")
            yield "抱歉，生成详细指南时出现错误。"

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

            # 提取关键元数据
            node_type = doc.metadata.get('node_type', '')
            location_name = (doc.metadata.get('location_name') or
                           doc.metadata.get('name') or
                           doc.metadata.get('entity_name', ''))

            if location_name:
                metadata_info += f" {location_name}"

            if node_type:
                metadata_info += f" | 类型: {node_type}"

            # 构建文档文本
            doc_text = f"{metadata_info}\n{doc.page_content}"

            # 检查长度限制
            if current_length + len(doc_text) > max_length:
                break

            context_parts.append(doc_text)
            current_length += len(doc_text)

        return "\n\n".join(context_parts)