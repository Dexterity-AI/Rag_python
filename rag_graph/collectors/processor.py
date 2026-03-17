"""
采集数据处理器

将采集结果转换为适合 GraphRAG 处理的格式。
提供文本切分、实体抽取准备、图谱构建准备等功能。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .core.base import CollectionResult, CollectionItem

logger = logging.getLogger(__name__)


class CollectionProcessor:
    """
    采集数据处理器

    将标准化采集结果转换为 RAG 系统可消费的格式。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化处理器

        Args:
            config: 配置项
                - chunk_size: 文本块大小 (默认: 500)
                - chunk_overlap: 文本块重叠 (默认: 50)
                - output_format: 输出格式 (jsonl|json) (默认: jsonl)
        """
        self.config = config or {}
        self.chunk_size = self.config.get('chunk_size', 500)
        self.chunk_overlap = self.config.get('chunk_overlap', 50)
        self.output_format = self.config.get('output_format', 'jsonl')
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self, result: CollectionResult, output_dir: Path) -> Path:
        """
        处理采集结果

        Args:
            result: 采集结果
            output_dir: 输出目录

        Returns:
            输出文件路径
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 生成输出文件名
        timestamp = result.fetch_time.replace(':', '-').replace('.', '-')
        base_name = f"{result.source_site}_{result.task_type}_processed_{timestamp}"

        if self.output_format == 'jsonl':
            output_path = output_dir / f"{base_name}.jsonl"
            self._write_jsonl(result, output_path)
        else:
            output_path = output_dir / f"{base_name}.json"
            self._write_json(result, output_path)

        self.logger.info(f"处理完成: {output_path}")
        return output_path

    def _write_jsonl(self, result: CollectionResult, output_path: Path):
        """写入 JSONL 格式"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for record in self._generate_records(result):
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def _write_json(self, result: CollectionResult, output_path: Path):
        """写入 JSON 格式"""
        records = list(self._generate_records(result))
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def _generate_records(self, result: CollectionResult) -> Iterator[Dict[str, Any]]:
        """
        生成处理后的记录

        每条记录包含完整的元信息和文本内容，适合后续：
        - 向量化
        - 实体抽取
        - 图谱构建
        """
        for item in result.items:
            # 构建基础记录
            record = {
                # 元信息
                'meta': {
                    'source_project': result.source_project,
                    'source_site': result.source_site,
                    'task_type': result.task_type,
                    'fetch_time': result.fetch_time,
                    'request_url': result.request_url,
                    'keyword': result.keyword,
                    'original_url': item.url,
                },
                # 内容信息
                'content': {
                    'title': item.title,
                    'text': item.content or item.summary,
                    'author': item.author,
                    'publish_time': item.publish_time,
                    'source': item.source,
                    'tags': item.tags,
                },
                # 扩展信息（保留原始数据）
                'extra': item.extra,
            }

            # 生成文本块（用于长文本）
            full_text = self._build_full_text(item)
            if len(full_text) > self.chunk_size:
                chunks = self._chunk_text(full_text)
                for i, chunk in enumerate(chunks):
                    chunk_record = record.copy()
                    chunk_record['content'] = record['content'].copy()
                    chunk_record['content']['text'] = chunk
                    chunk_record['content']['chunk_index'] = i
                    chunk_record['content']['total_chunks'] = len(chunks)
                    yield chunk_record
            else:
                record['content']['chunk_index'] = 0
                record['content']['total_chunks'] = 1
                yield record

    def _build_full_text(self, item: CollectionItem) -> str:
        """构建完整文本"""
        parts = []

        if item.title:
            parts.append(f"标题: {item.title}")

        if item.content:
            parts.append(item.content)
        elif item.summary:
            parts.append(item.summary)

        if item.author:
            parts.append(f"作者: {item.author}")

        return '\n\n'.join(parts)

    def _chunk_text(self, text: str) -> List[str]:
        """
        将文本切分为块

        使用简单的滑动窗口策略。
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]

            # 尝试在句子边界处截断
            if end < len(text):
                # 查找最近的句号、问号或感叹号
                for delim in ['。', '？', '！', '. ', '? ', '! ', '\n']:
                    pos = chunk.rfind(delim)
                    if pos > self.chunk_size * 0.5:  # 至少保留一半内容
                        chunk = chunk[:pos + 1]
                        end = start + len(chunk)
                        break

            chunks.append(chunk.strip())
            start = end - self.chunk_overlap

        return chunks

    def process_file(self, input_path: Path, output_dir: Path) -> Optional[Path]:
        """
        处理采集结果文件

        Args:
            input_path: 输入文件路径（标准化采集结果）
            output_dir: 输出目录

        Returns:
            输出文件路径或None
        """
        # 加载采集结果
        result = CollectionResult.from_file(str(input_path))
        if not result:
            self.logger.error(f"无法加载文件: {input_path}")
            return None

        return self.process(result, output_dir)

    def batch_process(
        self,
        input_dir: Path,
        output_dir: Path,
        pattern: str = "*.json"
    ) -> List[Path]:
        """
        批量处理目录中的采集结果

        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            pattern: 文件匹配模式

        Returns:
            输出文件路径列表
        """
        output_paths = []

        for input_file in sorted(input_dir.glob(pattern)):
            self.logger.info(f"处理文件: {input_file}")
            output_path = self.process_file(input_file, output_dir)
            if output_path:
                output_paths.append(output_path)

        self.logger.info(f"批量处理完成: {len(output_paths)} 个文件")
        return output_paths


class GraphRAGDataBuilder:
    """
    GraphRAG 数据构建器

    将采集结果转换为 GraphRAG 数据准备模块可消费的格式。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def build_documents(self, result: CollectionResult) -> List[Dict[str, Any]]:
        """
        构建文档列表

        输出格式与 rag_modules.graph_data_preparation 兼容。
        """
        documents = []

        for item in result.items:
            doc = {
                'id': self._generate_doc_id(item),
                'text': self._build_document_text(item),
                'metadata': {
                    'source': result.source_project,
                    'source_site': result.source_site,
                    'task_type': result.task_type,
                    'fetch_time': result.fetch_time,
                    'url': item.url,
                    'author': item.author,
                    'publish_time': item.publish_time,
                    'tags': item.tags,
                }
            }
            documents.append(doc)

        return documents

    def _generate_doc_id(self, item: CollectionItem) -> str:
        """生成文档ID"""
        import hashlib
        content = f"{item.url}:{item.title}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _build_document_text(self, item: CollectionItem) -> str:
        """构建文档文本"""
        parts = []

        if item.title:
            parts.append(f"标题: {item.title}")

        if item.content:
            parts.append(item.content)
        elif item.summary:
            parts.append(item.summary)

        if item.author:
            parts.append(f"作者: {item.author}")

        if item.source:
            parts.append(f"来源: {item.source}")

        return '\n\n'.join(parts)

    def export_for_ingestion(
        self,
        result: CollectionResult,
        output_path: Path
    ) -> bool:
        """
        导出为知识库导入格式

        生成适合直接导入 GraphRAG 知识库的格式。
        """
        documents = self.build_documents(result)

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'source': result.source_project,
                    'fetch_time': result.fetch_time,
                    'document_count': len(documents),
                    'documents': documents,
                }, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"导出失败: {e}")
            return False
