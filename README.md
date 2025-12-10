# 🚀 GraphRAG

> 智能图RAG旅游助手 - 基于 Neo4j 图数据库与向量检索的智能问答系统

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-blue)]()
[![Milvus](https://img.shields.io/badge/Milvus-2.x-orange)]()

## ✨ 核心特性

- **🕸️ 图 RAG 检索** - 基于 Neo4j 的多跳遍历与图结构推理
- **⚡ 向量检索** - Milvus + BGE 中文嵌入模型高效搜索
- **🧠 智能路由** - LLM 驱动的查询策略自动选择
- **🔄 混合检索** - 传统检索与图 RAG 的 Round-robin 融合
- **💬 现代 CLI** - 基于 Typer + Rich 的交互式命令行界面

## 🚀 快速开始

### 📦 环境要求
- Python 3.12+（目前使用3.12.7）
- Docker (用于 Neo4j 和 Milvus)
- 16GB+ 内存

### 🔧 安装与启动

```bash
# 1. 克隆项目
git clone https://github.com/Zzeng0917/Rag_python.git
cd Rag_python/rag_graph

# 2. 创建虚拟环境
conda create -n rag_graph python=3.12.7
conda activate rag_graph

# 3. 启动 Docker 服务
docker-compose up -d --build

# 4. 安装依赖
pip install -r requirement.txt

# 5. 配置环境变量 (.env 文件)
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_PASSWORD=your-password
LLM_MODEL=your_model
LLM_API_KEY=your_api_key
LLM_BASE_URL=your_base_url

# 6. 启动系统
python main.py
```

## 📖 使用指南

### 💻 命令行界面

```bash
# 启动交互式界面 (默认)
python main.py

# 单次查询模式
python main.py query "北京有哪些必去的景点？"

# 配置管理
python main.py config list

# 系统健康检查
python main.py doctor
```

### 🔧 交互式命令

在交互模式中可使用以下命令：
- `/help` - 显示帮助信息
- `/stats` - 查看系统统计
- `/quit` - 退出系统

### 📋 项目结构

```
rag_graph/
├── main.py                    # 程序入口
├── cli.py                     # CLI 界面
├── config.py                  # 配置管理
├── requirement.txt            # 依赖列表
├── docker-compose.yml         # Docker 编排
├── .env                       # 环境配置
├── rag_modules/               # 核心模块
│   ├── graph_data_preparation.py    # 图数据准备
│   ├── graph_rag_retrieval.py       # 图 RAG 检索
│   ├── hybrid_retrieval.py          # 混合检索
│   ├── intelligent_query_touter.py  # 智能路由
│   ├── milvus_index_construction.py # 向量索引
│   └── generation_integration.py    # 生成集成
├── neo4j_data/                # Neo4j 数据文件
└── ui/                        # 用户界面组件
```

## ⚙️ 核心配置

系统配置通过 `.env` 文件管理：

```bash
# Neo4j 图数据库
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Milvus 向量数据库
MILVUS_HOST=127.0.0.1
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME=travel_knowledge

# 大语言模型
LLM_MODEL=your_model
LLM_API_KEY=your_api_key
LLM_BASE_URL=your_base_url

# 嵌入模型 (中文优化)
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5

# 检索配置
TOP_K=5
MAX_GRAPH_DEPTH=2
TEMPERATURE=0.1
```

## 🛠️ 技术栈

- **数据库**: Neo4j (图), Milvus (向量), MinIO (对象存储)
- **AI/ML**: BGE 中文嵌入, LangChain, OpenAI API
- **CLI 框架**: Typer + Rich (类 Kode-cli 风格)
- **核心语言**: Python 3.12+

---

## 📰  RAG 分享

> 📌 记录发现的 RAG 相关有用内容

### 🗓️ 2025 年 11 月

| 日期 | 内容 | 标签 |
|:----:|------|:----:|
| **11/30** | 📘 [**字节跳动 RAG 实践手册**](https://docs.qq.com/doc/DSXJiaE5taUtaVGx6) <br> 字节内部 RAG 系统架构设计，涵盖数据处理、索引构建、检索优化、生成层设计等完整实践经验 | `工业实践` `架构设计` |

---

## 🙏 致谢

- [BAAI](https://github.com/FlagOpen/FlagEmbedding) - 优秀的 BGE 嵌入模型
- [Neo4j](https://neo4j.com/) - 强大的图数据库
- [Milvus](https://milvus.io/) - 高性能向量数据库
- [Datawhale](https://github.com/datawhalechina/all-in-rag) - RAG 学习教程
- [Hugging Face](https://huggingface.co/) - 丰富的预训练模型资源

## 📞 联系我

- **项目主页**: [https://github.com/Zzeng0917/Rag_python](https://github.com/Zzeng0917/Rag_python)
- **问题反馈**: [Issues](https://github.com/Zzeng0917/Rag_python/issues)
- **功能建议**: [Discussions](https://github.com/Zzeng0917/Rag_python/discussions)
- **邮箱**: zxd450273@gmail.com

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给我们一个 Star！**

Made with ❤️ by RAG Python Team

</div>
