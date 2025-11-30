# 📋 Changelog

所有项目的重要更改都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### 🚧 计划中
- [ ] 支持更多文档格式 (PDF, Word)
- [ ] Web UI 界面
- [ ] 多语言支持

---

## [0.1.0] - 2024-11-30

### ✨ 新增

#### 🕸️ 图 RAG 系统 (rag_graph)
- **Neo4j 图数据库集成** - 支持知识图谱存储与查询
- **Milvus 向量数据库** - 高效向量相似度检索
- **智能查询路由器** - LLM 驱动的自动策略选择
  - `hybrid_traditional` - 传统混合检索
  - `graph_rag` - 图 RAG 检索
  - `combined` - 组合策略
- **图 RAG 检索引擎**
  - 多跳图遍历
  - 子图提取
  - 图结构推理（地理位置、景点关联、美食文化等）
- **旅游领域知识图谱** - 包含城市、景点、美食、酒店等实体数据

#### 📚 基础 RAG 系统 (rag)
- **BGE 向量嵌入** - 使用 `BAAI/bge-small-zh-v1.5` 模型
- **Faiss 向量索引** - 本地向量存储与检索
- **文档智能分块** - 按标题层次分块，建立父子关系
- **索引持久化** - 支持索引缓存，快速启动

### 📦 依赖
- Python 3.12+
- Neo4j 5.x
- Milvus 2.x
- LangChain
- Sentence-Transformers

### 📝 文档
- 完善 README.md
- 添加系统架构图
- 添加快速开始指南

---

## 版本对比

[Unreleased]: https://github.com/Zzeng0917/Rag_python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Zzeng0917/Rag_python/releases/tag/v0.1.0

