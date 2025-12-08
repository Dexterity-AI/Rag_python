# GraphRAG Docker 部署指南

## 📦 文件说明

| 文件 | 说明 |
|------|------|
| `Dockerfile` | RAG 应用镜像构建文件 |
| `docker-compose.yml` | 服务编排配置（Neo4j + Milvus + RAG） |
| `.dockerignore` | Docker 构建忽略文件 |

## 🚀 快速开始

### 1. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的配置：

```bash
cp .env.example .env
```

**必须配置的变量：**
```bash
# LLM API 配置（必填）
LLM_API_KEY=your_api_key_here
LLM_MODEL=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com/v1

# Neo4j 密码（可选，默认 graphrag123）
NEO4J_PASSWORD=graphrag123
```

### 2. 启动所有服务

```bash
# 构建并启动（首次运行）
docker-compose up -d --build

# 查看启动日志
docker-compose logs -f
```

### 3. 等待服务就绪

首次启动需要：
- 下载镜像（约 5-10 分钟，取决于网络）
- Neo4j 初始化并导入数据（约 1-2 分钟）
- Milvus 启动（约 1-2 分钟）
- RAG 应用下载 Embedding 模型（首次约 5 分钟）

可以通过以下命令查看服务状态：
```bash
docker-compose ps
```

### 4. 进入交互式界面

```bash
# 方式1: 进入已运行的容器
docker exec -it graphrag-app python main.py

# 方式2: 单次查询
docker exec graphrag-app python main.py query "北京有什么好玩的"
```

## 🔧 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f graphrag      # RAG 应用日志
docker-compose logs -f neo4j         # Neo4j 日志
docker-compose logs -f milvus        # Milvus 日志

# 重新构建 RAG 应用（代码更新后）
docker-compose up -d --build graphrag

# 清理所有数据（慎用！）
docker-compose down -v
rm -rf ./volumes
```

## 🌐 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Neo4j Browser | http://localhost:7474 | 图数据库可视化界面 |
| Neo4j Bolt | bolt://localhost:7687 | 数据库连接 |
| Milvus | localhost:19530 | 向量数据库 |
| MinIO Console | http://localhost:9001 | 对象存储控制台 |

## 🇨🇳 国内镜像加速

如果拉取镜像失败，在 `.env` 中配置镜像加速：

```bash
# 可选镜像源
REGISTRY_MIRROR=docker.1ms.run/
# 或
REGISTRY_MIRROR=dockerpull.org/
# 或
REGISTRY_MIRROR=docker.rainbond.cc/
```

然后重新启动：
```bash
docker-compose down
docker-compose up -d --build
```

## 📊 数据持久化

所有数据存储在 `./volumes/` 目录：

```
volumes/
├── neo4j/         # Neo4j 数据
│   ├── data/
│   └── logs/
├── etcd/          # etcd 数据
├── minio/         # MinIO 对象存储
├── milvus/        # Milvus 向量数据
└── huggingface/   # HuggingFace 模型缓存
```

## ❓ 常见问题

### Q: Neo4j 数据没有自动导入？

手动执行导入：
```bash
docker exec -it graphrag-neo4j cypher-shell -u neo4j -p graphrag123 -f /var/lib/neo4j/import/init_data/import_data.cypher
```

### Q: Milvus 启动失败？

检查 etcd 和 minio 是否正常：
```bash
docker-compose ps
docker-compose logs etcd
docker-compose logs minio
```

### Q: 如何查看 Neo4j 中的数据？

1. 打开浏览器访问 http://localhost:7474
2. 使用账号 `neo4j` / 密码 `graphrag123`（或你设置的密码）登录
3. 运行 `MATCH (n) RETURN n LIMIT 25` 查看节点

### Q: 如何重置所有数据？

```bash
docker-compose down -v
rm -rf ./volumes
docker-compose up -d
```

## 🔄 更新代码

修改 Python 代码后，重新构建 RAG 应用：

```bash
docker-compose up -d --build graphrag
```

## 📝 日志调试

```bash
# 查看 RAG 应用详细日志
docker logs -f graphrag-app

# 进入容器调试
docker exec -it graphrag-app /bin/bash
```
