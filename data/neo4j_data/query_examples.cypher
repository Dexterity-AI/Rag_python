// ============================================
// 旅游图数据库 - 查询示例
// ============================================

// ===========================================
// 一、基础查询
// ===========================================

// 1. 查看所有热门旅游目的地
MATCH (s:SummaryNode)-[r:IS_POPULAR_DESTINATION]->(dest)
RETURN s.name AS 总结点, dest.name AS 目的地, r.region AS 所在地区;

// 2. 查看所有城市/地区
MATCH (c) WHERE c:City OR c:Region
RETURN c.name AS 名称, c.description AS 描述, c.highlights AS 亮点;

// 3. 查看西藏的所有子地区
MATCH (r:Region {name: '西藏'})-[:HAS_SUBREGION]->(sr:SubRegion)
RETURN sr.name AS 子地区, sr.description AS 描述;

// ===========================================
// 二、景点查询
// ===========================================

// 4. 查看北京所有景点（按分类）
MATCH (c:City {name: '北京'})-[:HAS_ATTRACTION]->(a:Attraction)
RETURN a.category AS 分类, collect(a.name) AS 景点列表
ORDER BY a.category;

// 5. 查看北京长城相关景点
MATCH (c:City {name: '北京'})-[:HAS_ATTRACTION]->(a:Attraction)
WHERE a.category = '长城'
RETURN a.name AS 名称, a.description AS 描述, a.ticket_price AS 票价;

// 6. 查看北京皇城古迹
MATCH (c:City {name: '北京'})-[:HAS_ATTRACTION]->(a:Attraction)
WHERE a.category = '皇城古迹'
RETURN a.name AS 名称, a.description AS 描述, a.ticket_price AS 票价;

// 7. 查看西藏拉萨的景点
MATCH (sr:SubRegion {name: '拉萨市'})-[:HAS_ATTRACTION]->(a:Attraction)
RETURN a.name AS 景点, a.description AS 描述, a.ticket_price AS 票价;

// 8. 查看西藏所有地区的景点
MATCH (r:Region {name: '西藏'})-[:HAS_SUBREGION]->(sr:SubRegion)
OPTIONAL MATCH (sr)-[:HAS_ATTRACTION]->(a:Attraction)
RETURN sr.name AS 地区, collect(a.name) AS 景点列表;

// 9. 查找免费景点
MATCH (a:Attraction)
WHERE a.ticket_price CONTAINS '免费'
RETURN a.name AS 景点, a.city_id AS 城市;

// ===========================================
// 三、美食餐厅查询
// ===========================================

// 10. 查看北京美食
MATCH (c:City {name: '北京'})-[:HAS_FOOD]->(f:Food)
RETURN f.name AS 美食, f.category AS 类别, f.description AS 描述;

// 11. 查看北京著名餐厅
MATCH (c:City {name: '北京'})-[:HAS_RESTAURANT]->(r:Restaurant)
RETURN r.name AS 餐厅, r.type AS 类型, r.description AS 描述, r.address AS 地址;

// 12. 查看各城市的特色美食
MATCH (c)-[:HAS_FOOD]->(f:Food)
WHERE c:City OR c:Region
RETURN c.name AS 城市, collect(f.name) AS 美食列表;

// ===========================================
// 四、住宿查询
// ===========================================

// 13. 查看北京住宿
MATCH (c:City {name: '北京'})-[:HAS_HOTEL]->(h:Hotel)
RETURN h.name AS 酒店, h.type AS 类型, h.description AS 描述, h.area AS 区域;

// 14. 查看拉萨住宿
MATCH (sr:SubRegion {name: '拉萨市'})-[:HAS_HOTEL]->(h:Hotel)
RETURN h.name AS 酒店, h.type AS 类型, h.description AS 描述;

// ===========================================
// 五、关系查询
// ===========================================

// 15. 查看故宫附近的景点
MATCH (a:Attraction {name: '故宫'})-[:NEARBY]->(b:Attraction)
RETURN a.name AS 起点, b.name AS 附近景点;

// 16. 查看所有景点邻近关系
MATCH (a:Attraction)-[r:NEARBY]->(b:Attraction)
RETURN a.name AS 景点A, r.area AS 区域, b.name AS 景点B;

// 17. 查看西藏神山圣湖
MATCH (a:Attraction)-[:NEARBY]-(b:Attraction)
WHERE a.city_id = 'ngari' OR b.city_id = 'ngari'
RETURN a.name, b.name;

// ===========================================
// 六、可视化查询
// ===========================================

// 18. 显示完整图结构（限制数量防止过载）
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 300;

// 19. 显示北京完整子图
MATCH (c:City {name: '北京'})-[r]->(n)
RETURN c, r, n;

// 20. 显示西藏完整子图（包含子地区和景点）
MATCH path = (r:Region {name: '西藏'})-[*1..2]->(n)
RETURN path;

// 21. 显示热门旅游城市及其直接连接
MATCH (s:SummaryNode {name: '热门旅游城市'})-[r]->(dest)
OPTIONAL MATCH (dest)-[r2:HAS_SUBREGION]->(sr)
RETURN s, r, dest, r2, sr;

// 22. 显示所有城市和它们的景点
MATCH (c:City)-[r:HAS_ATTRACTION]->(a:Attraction)
RETURN c, r, a;

// ===========================================
// 七、统计查询
// ===========================================

// 23. 统计各城市景点数量
MATCH (c)-[:HAS_ATTRACTION]->(a:Attraction)
WHERE c:City OR c:SubRegion
RETURN c.name AS 城市, count(a) AS 景点数量
ORDER BY 景点数量 DESC;

// 24. 统计各类型节点数量
MATCH (n)
RETURN labels(n) AS 节点类型, count(n) AS 数量;

// 25. 统计各类型关系数量
MATCH ()-[r]->()
RETURN type(r) AS 关系类型, count(r) AS 数量;

// ===========================================
// 八、路径查询
// ===========================================

// 26. 查找从总结点到布达拉宫的路径
MATCH path = (s:SummaryNode)-[*..3]->(a:Attraction {name: '布达拉宫'})
RETURN path;

// 27. 查找北京到故宫的路径
MATCH path = (c:City {name: '北京'})-[*..2]->(a:Attraction {name: '故宫'})
RETURN path;

// ===========================================
// 九、组合查询
// ===========================================

// 28. 一日游推荐：北京中轴线
MATCH (c:City {name: '北京'})-[:HAS_ATTRACTION]->(a:Attraction)
WHERE a.category IN ['皇城古迹', '公园']
AND (a.name CONTAINS '故宫' OR a.name CONTAINS '天安门' OR a.name CONTAINS '景山')
RETURN a.name AS 景点, a.description AS 描述, a.ticket_price AS 票价;

// 29. 美食之旅：北京小吃
MATCH (c:City {name: '北京'})-[:HAS_FOOD]->(f:Food)
WHERE f.category = '小吃'
RETURN f.name AS 小吃, f.description AS 描述;

// 30. 西藏朝圣之旅：寺庙景点
MATCH (sr:SubRegion)-[:HAS_ATTRACTION]->(a:Attraction)
WHERE a.category = '寺庙'
RETURN sr.name AS 地区, a.name AS 寺庙, a.description AS 描述;
