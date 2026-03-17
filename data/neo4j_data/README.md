# 旅游图数据库 - Neo4j

## 项目概述

本项目基于马蜂窝旅游攻略数据，创建了一个包含北京、南京、上海、西藏四个热门旅游目的地的Neo4j图数据库。

## 数据来源

- 马蜂窝北京.md
- 马蜂窝南京.md
- 马蜂窝上海.md
- 马蜂窝西藏.md

## 图数据库结构

### 节点类型 (Node Labels)

| 节点类型 | 说明 | 属性 |
|---------|------|-----|
| SummaryNode | 热门旅游城市总结点 | id, name, description |
| City | 城市 | id, name, type, description, best_time, consumption_level, highlights |
| Region | 地区（西藏） | id, name, type, description, best_time, consumption_level, highlights |
| SubRegion | 子地区（西藏下属地区） | id, name, parent_region, description |
| Attraction | 景点 | id, name, city_id, category, description, ticket_price, opening_hours, address |
| Food | 美食 | id, name, city_id, category, description |
| Restaurant | 餐厅 | id, name, city_id, type, description, address |
| Hotel | 住宿 | id, name, city_id, type, description, area |
| Specialty | 特产/购物 | id, name, city_id, category, description |
| Festival | 节庆活动 | id, name, city_id, time, description |

### 关系类型 (Relationship Types)

| 关系类型 | 起始节点 | 目标节点 | 说明 |
|---------|---------|---------|-----|
| IS_POPULAR_DESTINATION | SummaryNode | City/Region | 热门旅游目的地 |
| HAS_SUBREGION | Region | SubRegion | 地区包含子地区 |
| HAS_ATTRACTION | City/SubRegion | Attraction | 拥有景点 |
| HAS_FOOD | City/Region/SubRegion | Food | 拥有美食 |
| HAS_RESTAURANT | City/SubRegion | Restaurant | 拥有餐厅 |
| HAS_HOTEL | City/SubRegion | Hotel | 拥有住宿 |
| HAS_SPECIALTY | City/Region | Specialty | 拥有特产 |
| HAS_FESTIVAL | City/Region | Festival | 拥有节庆 |
| NEARBY | Attraction | Attraction | 景点邻近关系 |

### 数据库结构图

```
                          ┌─────────────────────┐
                          │   热门旅游城市      │
                          │   (SummaryNode)     │
                          └─────────┬───────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        ▼                        ▼
    ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
    │    北京     │          │   南京/上海  │          │    西藏     │
    │   (City)    │          │   (City)    │          │  (Region)   │
    └──────┬──────┘          └──────┬──────┘          └──────┬──────┘
           │                        │                        │
           ▼                        ▼                        ▼
    ┌─────────────┐          ┌─────────────┐    ┌─────────────────────────┐
    │ • 故宫      │          │ • 中山陵    │    │   子地区 (SubRegion)    │
    │ • 长城      │          │ • 夫子庙    │    ├─────────────────────────┤
    │ • 颐和园    │          │ • 外滩      │    │ • 拉萨市    • 林芝地区  │
    │ • 天坛      │          │ • 新天地    │    │ • 山南地区  • 日喀则    │
    │ • 南锣鼓巷  │          │ • 田子坊    │    │ • 阿里地区  • 那曲地区  │
    │ • 后海      │          │ • 南京博物院│    │ • 昌都地区              │
    │ • 北京烤鸭  │          │ • 鸭血粉丝  │    └──────────┬──────────────┘
    │ • 全聚德    │          │ • 生煎包    │               │
    │ • 北京饭店  │          │ • 金陵饭店  │               ▼
    └─────────────┘          └─────────────┘    ┌─────────────────────────┐
                                                │ 各子地区下属内容：      │
                                                │ • 布达拉宫 (拉萨)       │
                                                │ • 纳木错 (拉萨)         │
                                                │ • 鲁朗林海 (林芝)       │
                                                │ • 珠穆朗玛峰 (日喀则)   │
                                                │ • 冈仁波齐 (阿里)       │
                                                └─────────────────────────┘
```

## 文件说明

| 文件名 | 说明 |
|--------|------|
| import_data.cypher | **完整的Cypher导入脚本（推荐使用）** |
| query_examples.cypher | 查询示例 |
| cities.csv | 城市和地区节点数据（备份参考） |
| subregions.csv | 西藏子地区节点数据（备份参考） |
| attractions.csv | 景点节点数据（备份参考） |
| foods.csv | 美食节点数据（备份参考） |
| restaurants.csv | 餐厅节点数据（备份参考） |
| hotels.csv | 住宿节点数据（备份参考） |
| specialties.csv | 特产购物节点数据（备份参考） |
| festivals.csv | 节庆活动节点数据（备份参考） |
| relationships.csv | 关系数据（备份参考） |

## 使用方法

### 推荐：使用Cypher脚本导入

1. 启动Neo4j数据库
2. 打开Neo4j Browser (通常是 http://localhost:7474)
3. 如果数据库中已有数据，先清理：
   ```cypher
   MATCH (n) DETACH DELETE n;
   ```
4. 复制 `import_data.cypher` 文件中的内容并分段执行
5. 或者使用Neo4j Desktop导入整个脚本文件

### 注意事项

- 脚本使用 `CREATE` 语句，首次导入前请确保数据库为空
- 约束创建语句使用 `IF NOT EXISTS`，可以重复执行
- 建议分段执行：先执行约束和索引，再执行节点创建，最后执行关系创建

## 数据统计

### 节点统计

| 节点类型 | 数量 | 说明 |
|---------|------|-----|
| SummaryNode | 1 | 热门旅游城市 |
| City | 3 | 北京、南京、上海 |
| Region | 1 | 西藏 |
| SubRegion | 7 | 拉萨、林芝、山南、日喀则、阿里、那曲、昌都 |
| Attraction | ~60 | 北京35+、南京10+、上海10+、西藏各地区15+ |
| Food | ~15 | 各地特色美食 |
| Restaurant | ~15 | 各地特色餐厅 |
| Hotel | ~10 | 各地住宿推荐 |
| Festival | 4 | 各地节庆活动 |
| Specialty | 2 | 特产 |

### 北京景点分类

- 皇城古迹：故宫、天坛、颐和园、圆明园、鼓楼钟楼、天安门广场、明十三陵
- 长城：八达岭、居庸关、慕田峪、司马台、金山岭
- 胡同街区：南锣鼓巷、什刹海(后海)、王府井、三里屯
- 公园：景山公园、北海公园、香山公园、北京植物园
- 古寺：雍和宫、潭柘寺、红螺寺
- 后奥运：鸟巢、水立方、奥林匹克森林公园
- 博物馆：国家博物馆、首都博物馆、军事博物馆
- 学府与艺术区：清华大学、北京大学、798艺术区
- 老街故居：恭王府、孔庙国子监
- 亲子游乐：北京动物园、欢乐谷、中国科技馆

## 设计说明

### 关于城市分离

根据需求，不在同一地区的城市完全分开，通过"热门旅游城市"总结点连接：
- 北京：华北地区
- 南京：华东地区
- 上海：华东地区
- 西藏：西南地区

### 关于西藏的特殊处理

西藏作为地区(Region)而非城市(City)，下设7个子地区(SubRegion)：
- 拉萨市：西藏首府，布达拉宫、大昭寺、纳木错
- 林芝地区：西藏小江南，鲁朗林海、南迦巴瓦峰、雅鲁藏布大峡谷
- 山南地区：藏文化发源地，羊卓雍错、桑耶寺
- 日喀则地区：后藏，珠穆朗玛峰、扎什伦布寺
- 阿里地区：高原上的高原，冈仁波齐、玛旁雍错、古格王朝遗址
- 那曲地区：离天最近的地方，羌塘草原
- 昌都地区：西藏东北部，来古冰川

## 查询示例

请参考 `query_examples.cypher` 文件获取常用查询示例。

## 可视化技巧

### 在Neo4j Browser中同时显示所有节点和关系

```cypher
// 显示整个图
MATCH (n) 
OPTIONAL MATCH (n)-[r]->(m) 
RETURN n, r, m LIMIT 500;

// 或者更简单的方式
MATCH p=()-->() RETURN p LIMIT 200;
```

### 显示特定城市的完整子图

```cypher
// 北京的所有内容
MATCH (c:City {name: '北京'})-[r]->(n)
RETURN c, r, n;

// 西藏的完整结构（包含子地区）
MATCH (r:Region {name: '西藏'})-[rel1]->(sr:SubRegion)
OPTIONAL MATCH (sr)-[rel2]->(a)
RETURN r, rel1, sr, rel2, a;
```

## 版本信息

- 更新日期：2025.11.27
- Neo4j版本建议：4.x 或 5.x
- 数据来源：马蜂窝旅游攻略
