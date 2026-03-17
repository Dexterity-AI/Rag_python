// ============================================
// 旅游图数据库 - Neo4j 导入脚本
// 包含北京、南京、上海、西藏完整数据
// ============================================

// 第一步: 清理现有数据 (取消注释执行)
// MATCH (n) DETACH DELETE n;

// 第二步: 创建约束和索引
CREATE CONSTRAINT city_id IF NOT EXISTS FOR (c:City) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT region_id IF NOT EXISTS FOR (r:Region) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT subregion_id IF NOT EXISTS FOR (sr:SubRegion) REQUIRE sr.id IS UNIQUE;
CREATE CONSTRAINT attraction_id IF NOT EXISTS FOR (a:Attraction) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT food_id IF NOT EXISTS FOR (f:Food) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT restaurant_id IF NOT EXISTS FOR (r:Restaurant) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT hotel_id IF NOT EXISTS FOR (h:Hotel) REQUIRE h.id IS UNIQUE;
CREATE CONSTRAINT specialty_id IF NOT EXISTS FOR (s:Specialty) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT festival_id IF NOT EXISTS FOR (f:Festival) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT summary_id IF NOT EXISTS FOR (s:SummaryNode) REQUIRE s.id IS UNIQUE;

CREATE INDEX city_name IF NOT EXISTS FOR (c:City) ON (c.name);
CREATE INDEX attraction_name IF NOT EXISTS FOR (a:Attraction) ON (a.name);
CREATE INDEX attraction_category IF NOT EXISTS FOR (a:Attraction) ON (a.category);

// ============================================
// 第三步: 创建总结点和城市/地区节点
// ============================================

CREATE (s:SummaryNode {
    id: 'summary_node',
    name: '热门旅游城市',
    description: '中国热门旅游目的地汇总'
});

// 北京
CREATE (beijing:City {
    id: 'beijing',
    name: '北京',
    type: 'City',
    description: '中国首都，拥有三千多年历史的古都。传统与现代交融，皇城遗迹主要集中在二环以内',
    best_time: '3-5月和9-11月，春天百花盛开，秋天红叶银杏',
    consumption_level: '较高',
    highlights: '故宫、长城、天坛、颐和园、南锣鼓巷、798艺术区'
});

// 南京
CREATE (nanjing:City {
    id: 'nanjing',
    name: '南京',
    type: 'City',
    description: '十朝都会，六朝古都，金陵帝王州。古称金陵，有紫金山麓、秦淮河畔的烟水气',
    best_time: '3-5月和9-11月',
    consumption_level: '中等',
    highlights: '中山陵、夫子庙、总统府、南京博物院'
});

// 上海
CREATE (shanghai:City {
    id: 'shanghai',
    name: '上海',
    type: 'City',
    description: '国际化大都市，东方明珠，十里洋场。中西合璧，各有精彩',
    best_time: '3-5月和9-11月',
    consumption_level: '较高',
    highlights: '外滩、东方明珠、新天地、田子坊'
});

// 西藏
CREATE (tibet:Region {
    id: 'tibet',
    name: '西藏',
    type: 'Region',
    description: '世界屋脊，雪域高原，神圣净土。美得极致，高得极致，神圣得极致',
    best_time: '7-9月',
    consumption_level: '较高',
    highlights: '布达拉宫、纳木错、珠穆朗玛峰、冈仁波齐'
});

// ============================================
// 第四步: 创建西藏子地区节点
// ============================================

CREATE (lhasa:SubRegion {id: 'lhasa', name: '拉萨市', parent_region: 'tibet', description: '西藏首府，大多数人到西藏的第一站'});
CREATE (nyingchi:SubRegion {id: 'nyingchi', name: '林芝地区', parent_region: 'tibet', description: '西藏小江南，雅鲁藏布大峡谷所在'});
CREATE (shannan:SubRegion {id: 'shannan', name: '山南地区', parent_region: 'tibet', description: '藏文化发源地，桑耶寺所在'});
CREATE (shigatse:SubRegion {id: 'shigatse', name: '日喀则地区', parent_region: 'tibet', description: '后藏，珠穆朗玛峰所在'});
CREATE (ngari:SubRegion {id: 'ngari', name: '阿里地区', parent_region: 'tibet', description: '高原上的高原，冈仁波齐神山所在'});
CREATE (nagqu:SubRegion {id: 'nagqu', name: '那曲地区', parent_region: 'tibet', description: '离天最近的地方，羌塘草原'});
CREATE (chamdo:SubRegion {id: 'chamdo', name: '昌都地区', parent_region: 'tibet', description: '西藏东北部，来古冰川所在'});

// ============================================
// 第五步: 创建北京景点节点
// ============================================

// 皇城古迹
CREATE (:Attraction {id: 'bj_gugong', name: '故宫', city_id: 'beijing', category: '皇城古迹', description: '世界五大宫殿之首，明清两代皇宫', ticket_price: '40-60元', address: '东城区景山前街4号'});
CREATE (:Attraction {id: 'bj_tiantan', name: '天坛', city_id: 'beijing', category: '皇城古迹', description: '明清两代祭天之地，天圆地方建筑', ticket_price: '10-35元', address: '崇文区天坛内东里7号'});
CREATE (:Attraction {id: 'bj_yiheyuan', name: '颐和园', city_id: 'beijing', category: '皇家园林', description: '中国古典园林之首，万寿山昆明湖', ticket_price: '20-60元', address: '海淀区新建宫门路19号'});
CREATE (:Attraction {id: 'bj_yuanmingyuan', name: '圆明园', city_id: 'beijing', category: '皇家园林', description: '万园之园遗址，西洋楼残迹', ticket_price: '10-25元', address: '海淀区清华西路28号'});
CREATE (:Attraction {id: 'bj_gulou', name: '鼓楼钟楼', city_id: 'beijing', category: '皇城古迹', description: '元明清三代报时中心', ticket_price: '20元', address: '东城区钟楼湾临字9号'});
CREATE (:Attraction {id: 'bj_tiananmen', name: '天安门广场', city_id: 'beijing', category: '皇城古迹', description: '世界最大城市广场，观升旗仪式', ticket_price: '15元', address: '东城区东长安街'});
CREATE (:Attraction {id: 'bj_mingshisanling', name: '明十三陵', city_id: 'beijing', category: '皇城古迹', description: '明朝13位皇帝陵寝', ticket_price: '25-65元', address: '昌平区长岭镇'});

// 长城
CREATE (:Attraction {id: 'bj_badaling', name: '八达岭长城', city_id: 'beijing', category: '长城', description: '明长城保存最好的一段，不到长城非好汉', ticket_price: '40-45元', address: '延庆县八达岭镇'});
CREATE (:Attraction {id: 'bj_juyongguan', name: '居庸关长城', city_id: 'beijing', category: '长城', description: '天下第一雄关，云台建筑精美', ticket_price: '40-45元', address: '昌平区南口镇'});
CREATE (:Attraction {id: 'bj_mutianyu', name: '慕田峪长城', city_id: 'beijing', category: '长城', description: '山势险峻，景观壮美', ticket_price: '45元', address: '怀柔区三渡河镇'});
CREATE (:Attraction {id: 'bj_simatai', name: '司马台长城', city_id: 'beijing', category: '长城', description: '唯一保留明代原貌长城，以险著称', ticket_price: '40元', address: '密云县古北口镇'});
CREATE (:Attraction {id: 'bj_jinshanling', name: '金山岭长城', city_id: 'beijing', category: '长城', description: '敌楼密集，摄影爱好者天堂', ticket_price: '65元', address: '承德滦平县'});

// 胡同街区
CREATE (:Attraction {id: 'bj_nanluoguxiang', name: '南锣鼓巷', city_id: 'beijing', category: '胡同街区', description: '北京最热闹时尚的胡同区，文艺青年聚集地', ticket_price: '免费', address: '东城区南锣鼓巷'});
CREATE (:Attraction {id: 'bj_houhai', name: '什刹海(后海)', city_id: 'beijing', category: '胡同街区', description: '老北京胡同汇集，京味儿酒吧区', ticket_price: '免费', address: '西城区什刹海'});
CREATE (:Attraction {id: 'bj_wangfujing', name: '王府井', city_id: 'beijing', category: '商业街区', description: '品尝老字号和购物好去处', ticket_price: '免费', address: '东城区王府井大街'});
CREATE (:Attraction {id: 'bj_sanlitun', name: '三里屯', city_id: 'beijing', category: '酒吧街', description: '著名酒吧一条街，夜生活中心', ticket_price: '免费', address: '朝阳区三里屯路'});

// 公园
CREATE (:Attraction {id: 'bj_jingshanpark', name: '景山公园', city_id: 'beijing', category: '公园', description: '北京城中轴线最高点，俯瞰故宫', ticket_price: '2元', address: '西城区景山西街44号'});
CREATE (:Attraction {id: 'bj_beihaipark', name: '北海公园', city_id: 'beijing', category: '公园', description: '皇家园林，白塔标志', ticket_price: '5-20元', address: '西城区文津街1号'});
CREATE (:Attraction {id: 'bj_xiangshanpark', name: '香山公园', city_id: 'beijing', category: '公园', description: '红叶如火，西山晴雪', ticket_price: '5-10元', address: '海淀区香山买卖街40号'});
CREATE (:Attraction {id: 'bj_zhiwuyuan', name: '北京植物园', city_id: 'beijing', category: '公园', description: '四时植物常开不败，樱桃沟', ticket_price: '10-50元', address: '海淀区香山南辛村20号'});

// 古寺
CREATE (:Attraction {id: 'bj_yonghegong', name: '雍和宫', city_id: 'beijing', category: '古寺', description: '北京规模最大喇嘛寺', ticket_price: '25元', address: '东城区雍和宫大街20号'});
CREATE (:Attraction {id: 'bj_tanzhesi', name: '潭柘寺', city_id: 'beijing', category: '古寺', description: '先有潭柘寺后有北京城', ticket_price: '55元', address: '门头沟区潭柘寺镇'});
CREATE (:Attraction {id: 'bj_hongluosi', name: '红螺寺', city_id: 'beijing', category: '古寺', description: '求姻缘求子灵验', ticket_price: '54元', address: '怀柔区红螺东路2号'});

// 后奥运
CREATE (:Attraction {id: 'bj_niaochao', name: '鸟巢(国家体育场)', city_id: 'beijing', category: '后奥运', description: '2008奥运标志性建筑', ticket_price: '50-80元', address: '朝阳区国家体育场南路1号'});
CREATE (:Attraction {id: 'bj_shuilifang', name: '水立方(国家游泳中心)', city_id: 'beijing', category: '后奥运', description: '奥运游泳馆，嬉水乐园', ticket_price: '30-200元', address: '朝阳区天辰东路11号'});
CREATE (:Attraction {id: 'bj_aolinpike', name: '奥林匹克森林公园', city_id: 'beijing', category: '后奥运', description: '亚洲最大城市绿化景观', ticket_price: '免费', address: '朝阳区奥运中心区北部'});

// 博物馆
CREATE (:Attraction {id: 'bj_guojiabowuguan', name: '国家博物馆', city_id: 'beijing', category: '博物馆', description: '四羊方尊后母戊鼎镇馆', ticket_price: '免费预约', address: '东城区东长安街16号'});
CREATE (:Attraction {id: 'bj_shoudubowuguan', name: '首都博物馆', city_id: 'beijing', category: '博物馆', description: '北京历史文化展示', ticket_price: '免费预约', address: '西城区复兴门外大街16号'});
CREATE (:Attraction {id: 'bj_junshiBowuguan', name: '军事博物馆', city_id: 'beijing', category: '博物馆', description: '军事装备历史展览', ticket_price: '免费', address: '海淀区复兴路9号'});

// 学府与艺术区
CREATE (:Attraction {id: 'bj_qinghua', name: '清华大学', city_id: 'beijing', category: '学府', description: '水木清华，最高学府', ticket_price: '免费', address: '海淀区清华园1号'});
CREATE (:Attraction {id: 'bj_beida', name: '北京大学', city_id: 'beijing', category: '学府', description: '未名湖畔，百年燕园', ticket_price: '免费', address: '海淀区颐和园路5号'});
CREATE (:Attraction {id: 'bj_798', name: '798艺术区', city_id: 'beijing', category: '艺术区', description: '工厂改造，艺术画廊聚集', ticket_price: '免费', address: '朝阳区酒仙桥路4号'});

// 亲子游乐
CREATE (:Attraction {id: 'bj_dongwuyuan', name: '北京动物园', city_id: 'beijing', category: '亲子', description: '国宝熊猫馆，陪伴北京人成长', ticket_price: '10-20元', address: '西城区西直门外大街137号'});
CREATE (:Attraction {id: 'bj_huanleggu', name: '北京欢乐谷', city_id: 'beijing', category: '游乐园', description: '主题生态游乐园', ticket_price: '230元', address: '朝阳区东四环小武基北路'});
CREATE (:Attraction {id: 'bj_kejiguan', name: '中国科学技术馆', city_id: 'beijing', category: '科普场所', description: '互动科普体验', ticket_price: '30元', address: '朝阳区北辰东路5号'});

// 名人故居
CREATE (:Attraction {id: 'bj_gongwangfu', name: '恭王府', city_id: 'beijing', category: '老街故居', description: '和珅宅邸，北京保存最完整王府', ticket_price: '40-70元', address: '西城区前海西街17号'});
CREATE (:Attraction {id: 'bj_kongmiao', name: '孔庙国子监', city_id: 'beijing', category: '老街故居', description: '元明清三代国家最高学府', ticket_price: '30元', address: '东城区国子监街13号'});

// ============================================
// 第六步: 创建南京景点节点（选取主要景点）
// ============================================

CREATE (:Attraction {id: 'nj_zhongshanling', name: '中山陵', city_id: 'nanjing', category: '历史遗迹', description: '孙中山先生陵墓', ticket_price: '免费预约', address: '玄武区石象路7号'});
CREATE (:Attraction {id: 'nj_mingxiaoling', name: '明孝陵', city_id: 'nanjing', category: '历史遗迹', description: '明太祖陵墓，明皇陵之首', ticket_price: '70元', address: '钟山风景区'});
CREATE (:Attraction {id: 'nj_fuzimiao', name: '夫子庙', city_id: 'nanjing', category: '历史遗迹', description: '秦淮河畔标志性建筑', ticket_price: '30元', address: '秦淮河北岸贡院街'});
CREATE (:Attraction {id: 'nj_laomendong', name: '老门东', city_id: 'nanjing', category: '历史街区', description: '老街巷吃喝玩乐', ticket_price: '免费', address: '秦淮区剪子巷'});
CREATE (:Attraction {id: 'nj_bowuyuan', name: '南京博物院', city_id: 'nanjing', category: '博物馆', description: '中国三大博物院之一', ticket_price: '免费', address: '秦淮区中山东路321号'});
CREATE (:Attraction {id: 'nj_jimingsi', name: '鸡鸣寺', city_id: 'nanjing', category: '寺庙', description: '南朝第一寺，赏春樱', ticket_price: '10元', address: '玄武区鸡鸣寺路1号'});
CREATE (:Attraction {id: 'nj_xuanwuhu', name: '玄武湖', city_id: 'nanjing', category: '自然风光', description: '金陵明珠，江南皇家园林', ticket_price: '免费', address: '玄武区玄武巷1号'});
CREATE (:Attraction {id: 'nj_zongtongfu', name: '总统府', city_id: 'nanjing', category: '历史建筑', description: '中国近代史遗址博物馆', ticket_price: '40元', address: '玄武区长江路292号'});
CREATE (:Attraction {id: 'nj_xianfeng', name: '先锋书店', city_id: 'nanjing', category: '文化设施', description: '全球最美书店', ticket_price: '免费', address: '鼓楼区广州路173号'});
CREATE (:Attraction {id: 'nj_datusha', name: '侵华日军南京大屠杀遇难同胞纪念馆', city_id: 'nanjing', category: '纪念馆', description: '铭记历史勿忘国耻', ticket_price: '免费', address: '建邺区水西门大街418号'});

// ============================================
// 第七步: 创建上海景点节点（选取主要景点）
// ============================================

CREATE (:Attraction {id: 'sh_waitan', name: '外滩', city_id: 'shanghai', category: '城市风光', description: '万国建筑博览群', ticket_price: '免费', address: '黄浦区'});
CREATE (:Attraction {id: 'sh_dongfangmingzhu', name: '东方明珠', city_id: 'shanghai', category: '现代建筑', description: '上海地标', ticket_price: '120-180元', address: '浦东新区世纪大道1号'});
CREATE (:Attraction {id: 'sh_yuyuan', name: '豫园', city_id: 'shanghai', category: '园林', description: '明代园林，城市山林', ticket_price: '30-40元', address: '黄浦区安仁街132号'});
CREATE (:Attraction {id: 'sh_xintiandi', name: '新天地', city_id: 'shanghai', category: '商业街区', description: '石库门建筑改造，小资地标', ticket_price: '免费', address: '黄浦区太仓路181弄'});
CREATE (:Attraction {id: 'sh_tianzifang', name: '田子坊', city_id: 'shanghai', category: '创意园区', description: '创意工作室聚集地', ticket_price: '免费', address: '黄浦区泰康路'});
CREATE (:Attraction {id: 'sh_nanjinglu', name: '南京路', city_id: 'shanghai', category: '商业街区', description: '中国第一商业街', ticket_price: '免费', address: '黄浦区'});
CREATE (:Attraction {id: 'sh_bowuguan', name: '上海博物馆', city_id: 'shanghai', category: '博物馆', description: '中国四大博物馆之一', ticket_price: '免费', address: '黄浦区人民大道201号'});
CREATE (:Attraction {id: 'sh_zhujiajiao', name: '朱家角', city_id: 'shanghai', category: '古镇', description: '上海四大历史文化名镇之一', ticket_price: '免费', address: '青浦区'});
CREATE (:Attraction {id: 'sh_jinmao', name: '金茂大厦', city_id: 'shanghai', category: '现代建筑', description: '88层观光厅', ticket_price: '120元', address: '浦东新区世纪大道88号'});
CREATE (:Attraction {id: 'sh_huanqiu', name: '上海环球金融中心', city_id: 'shanghai', category: '现代建筑', description: '世界最高观景平台', ticket_price: '120-150元', address: '浦东新区世纪大道100号'});

// ============================================
// 第八步: 创建西藏景点节点
// ============================================

// 拉萨
CREATE (:Attraction {id: 'lhasa_budala', name: '布达拉宫', city_id: 'lhasa', category: '宫殿', description: '世界最高最雄伟宫殿，西藏象征', ticket_price: '100-200元', address: '拉萨市城关区北京中路35号'});
CREATE (:Attraction {id: 'lhasa_dazhao', name: '大昭寺', city_id: 'lhasa', category: '寺庙', description: '西藏的眼睛，释迦摩尼十二岁等身像', ticket_price: '35-85元', address: '拉萨市城关区八廓街'});
CREATE (:Attraction {id: 'lhasa_bakuo', name: '八廓街', city_id: 'lhasa', category: '历史街区', description: '拉萨最著名转经道和商业中心', ticket_price: '免费', address: '拉萨市城关区'});
CREATE (:Attraction {id: 'lhasa_zhebangsi', name: '哲蚌寺', city_id: 'lhasa', category: '寺庙', description: '格鲁派最大寺庙，雪顿节晒大佛', ticket_price: '50元', address: '拉萨市城关区'});
CREATE (:Attraction {id: 'lhasa_selasi', name: '色拉寺', city_id: 'lhasa', category: '寺庙', description: '藏区最著名辩经仪式', ticket_price: '50元', address: '拉萨市城关区色拉路1号'});
CREATE (:Attraction {id: 'lhasa_namucuo', name: '纳木错', city_id: 'lhasa', category: '湖泊', description: '西藏最大湖泊，世界最高咸水湖', ticket_price: '100-120元', address: '拉萨市当雄县'});

// 林芝
CREATE (:Attraction {id: 'nyingchi_lulanglinhai', name: '鲁朗林海', city_id: 'nyingchi', category: '自然风光', description: '中国瑞士，云山雾海森林', ticket_price: '免费', address: '林芝地区'});
CREATE (:Attraction {id: 'nyingchi_nanjiabawa', name: '南迦巴瓦峰', city_id: 'nyingchi', category: '雪山', description: '中国最美山峰，羞女峰', ticket_price: '免费', address: '林芝地区'});
CREATE (:Attraction {id: 'nyingchi_yaluzangbu', name: '雅鲁藏布大峡谷', city_id: 'nyingchi', category: '峡谷', description: '世界第一大峡谷', ticket_price: '290元', address: '林芝地区'});
CREATE (:Attraction {id: 'nyingchi_basongcuo', name: '巴松错', city_id: 'nyingchi', category: '湖泊', description: '红教圣湖，高峡深谷中的翡翠', ticket_price: '120元', address: '林芝地区工布江达县'});

// 日喀则
CREATE (:Attraction {id: 'shigatse_zhashlunbu', name: '扎什伦布寺', city_id: 'shigatse', category: '寺庙', description: '历代班禅驻锡地，后藏最大寺庙', ticket_price: '100元', address: '日喀则市'});
CREATE (:Attraction {id: 'shigatse_everest', name: '珠穆朗玛峰', city_id: 'shigatse', category: '雪山', description: '世界第一高峰', ticket_price: '180元', address: '日喀则地区'});

// 阿里
CREATE (:Attraction {id: 'ngari_gangrenboqi', name: '冈仁波齐', city_id: 'ngari', category: '神山', description: '世界公认神山，多教圣地', ticket_price: '免费', address: '阿里地区普兰县'});
CREATE (:Attraction {id: 'ngari_mapangyongcuo', name: '玛旁雍错', city_id: 'ngari', category: '湖泊', description: '世界中心圣湖', ticket_price: '免费', address: '阿里地区普兰县'});
CREATE (:Attraction {id: 'ngari_guge', name: '古格王朝遗址', city_id: 'ngari', category: '历史遗迹', description: '神秘消失的古格王国', ticket_price: '100元', address: '阿里地区札达县'});

// 山南
CREATE (:Attraction {id: 'shannan_yangzhuoyongcuo', name: '羊卓雍错', city_id: 'shannan', category: '湖泊', description: '西藏三大圣湖之一', ticket_price: '40元', address: '山南地区浪卡子县'});
CREATE (:Attraction {id: 'shannan_sangyesi', name: '桑耶寺', city_id: 'shannan', category: '寺庙', description: '西藏第一座寺庙', ticket_price: '40元', address: '山南地区扎囊县'});

// 那曲
CREATE (:Attraction {id: 'nagqu_qiangtang', name: '羌塘草原', city_id: 'nagqu', category: '草原', description: '世界上海拔最高面积最大的草原', ticket_price: '免费', address: '那曲地区'});

// 昌都
CREATE (:Attraction {id: 'chamdo_laigu', name: '来古冰川', city_id: 'chamdo', category: '冰川', description: '世界三大冰川之一', ticket_price: '30元', address: '昌都地区八宿县'});

// ============================================
// 第九步: 创建美食节点
// ============================================

// 北京美食
CREATE (:Food {id: 'bj_kaoya', name: '北京烤鸭', city_id: 'beijing', category: '招牌菜', description: '北京最负盛名的菜品，皮脆肉嫩'});
CREATE (:Food {id: 'bj_shuanyanrou', name: '涮羊肉', city_id: 'beijing', category: '火锅', description: '铜锅涮肉，东来顺最出名'});
CREATE (:Food {id: 'bj_douzhir', name: '豆汁儿', city_id: 'beijing', category: '小吃', description: '北京地道小吃，口感独特'});
CREATE (:Food {id: 'bj_chaogan', name: '炒肝儿', city_id: 'beijing', category: '小吃', description: '鼓楼一拐弯儿姚记吃炒肝儿'});
CREATE (:Food {id: 'bj_luzhu', name: '卤煮', city_id: 'beijing', category: '小吃', description: '卤煮火烧，老北京传统美食'});
CREATE (:Food {id: 'bj_jiaoquan', name: '焦圈儿', city_id: 'beijing', category: '小吃', description: '配豆汁儿的经典搭档'});
CREATE (:Food {id: 'bj_lvdagunr', name: '驴打滚儿', city_id: 'beijing', category: '小吃', description: '黄米面裹豆沙，滚豆面'});

// 南京美食
CREATE (:Food {id: 'nj_yaxuefensi', name: '鸭血粉丝汤', city_id: 'nanjing', category: '小吃', description: '南京最著名小吃'});
CREATE (:Food {id: 'nj_yanshuiya', name: '盐水鸭', city_id: 'nanjing', category: '小吃', description: '南京特产，皮白肉嫩'});
CREATE (:Food {id: 'nj_tangbao', name: '汤包', city_id: 'nanjing', category: '小吃', description: '皮薄汁多'});

// 上海美食
CREATE (:Food {id: 'sh_shengjianbao', name: '生煎包', city_id: 'shanghai', category: '小吃', description: '上海最著名小吃，底脆馅鲜'});
CREATE (:Food {id: 'sh_tangbao_sh', name: '南翔小笼包', city_id: 'shanghai', category: '小吃', description: '皮薄汁多，南翔最负盛名'});

// 西藏美食
CREATE (:Food {id: 'tibet_zanba', name: '糌粑', city_id: 'tibet', category: '主食', description: '青稞面炒熟后磨成的面粉，藏族主食'});
CREATE (:Food {id: 'tibet_suyoucha', name: '酥油茶', city_id: 'tibet', category: '饮品', description: '藏族传统饮品，高热量抗寒'});
CREATE (:Food {id: 'tibet_niurou', name: '牦牛肉', city_id: 'tibet', category: '肉食', description: '高原特产牛肉，风干牦牛肉'});

// ============================================
// 第十步: 创建餐厅节点
// ============================================

// 北京餐厅
CREATE (:Restaurant {id: 'bj_quanjude', name: '全聚德', city_id: 'beijing', type: '烤鸭店', description: '北京烤鸭第一品牌，创立于1864年', address: '前门、王府井等多家'});
CREATE (:Restaurant {id: 'bj_donglaisshun', name: '东来顺', city_id: 'beijing', type: '火锅', description: '涮羊肉老字号，铜锅涮肉', address: '王府井等多家'});
CREATE (:Restaurant {id: 'bj_huguosixiaochi', name: '护国寺小吃', city_id: 'beijing', type: '小吃店', description: '北京传统小吃汇聚', address: '护国寺街'});
CREATE (:Restaurant {id: 'bj_yaojichaogan', name: '姚记炒肝', city_id: 'beijing', type: '小吃店', description: '鼓楼一拐弯儿姚记吃炒肝儿', address: '鼓楼东大街'});
CREATE (:Restaurant {id: 'bj_guijie', name: '簋街', city_id: 'beijing', type: '美食街', description: '24小时营业的深夜食堂', address: '东直门'});

// 南京餐厅
CREATE (:Restaurant {id: 'nj_dapaidang', name: '南京大牌档', city_id: 'nanjing', type: '餐厅', description: '南京本地特色餐厅', address: '多家分店'});

// 上海餐厅
CREATE (:Restaurant {id: 'sh_laofandian', name: '老饭店', city_id: 'shanghai', type: '餐厅', description: '本帮佳肴老字号', address: '城隍庙'});
CREATE (:Restaurant {id: 'sh_chenghuangmiao', name: '城隍庙美食', city_id: 'shanghai', type: '美食街', description: '上海传统小吃聚集地', address: '城隍庙'});

// 拉萨餐厅
CREATE (:Restaurant {id: 'lhasa_magiaimi', name: '玛吉阿米', city_id: 'lhasa', type: '餐厅', description: '六世达赖情人居住地改建', address: '八廓街'});
CREATE (:Restaurant {id: 'lhasa_guangming', name: '光明港琼甜茶馆', city_id: 'lhasa', type: '茶馆', description: '拉萨最著名甜茶馆', address: '八廓街附近'});

// ============================================
// 第十一步: 创建住宿节点
// ============================================

// 北京住宿
CREATE (:Hotel {id: 'bj_beijingfandian', name: '北京饭店', city_id: 'beijing', type: '五星级', description: '长安街百年老饭店，接待国宾', area: '王府井'});
CREATE (:Hotel {id: 'bj_houhai', name: '后海民宿', city_id: 'beijing', type: '民宿', description: '胡同四合院特色住宿', area: '什刹海'});
CREATE (:Hotel {id: 'bj_nanluoguxiang', name: '南锣鼓巷青旅', city_id: 'beijing', type: '青年旅舍', description: '文艺青年聚集地', area: '南锣鼓巷'});

// 南京住宿
CREATE (:Hotel {id: 'nj_jinlingfandian', name: '金陵饭店', city_id: 'nanjing', type: '五星级', description: '南京地标性酒店', area: '新街口'});

// 上海住宿
CREATE (:Hotel {id: 'sh_hepingfandian', name: '和平饭店', city_id: 'shanghai', type: '五星级', description: '外滩百年老酒店', area: '外滩'});

// 拉萨住宿
CREATE (:Hotel {id: 'lhasa_lasafandian', name: '拉萨饭店', city_id: 'lhasa', type: '四星级', description: '拉萨条件最好酒店', area: '拉萨市区'});
CREATE (:Hotel {id: 'lhasa_pingcuokangsan', name: '平措康桑青年旅舍', city_id: 'lhasa', type: '青年旅舍', description: '拉萨著名青旅', area: '北京东路'});

// ============================================
// 第十二步: 创建节庆节点
// ============================================

CREATE (:Festival {id: 'nj_qinhuaideng', name: '秦淮灯会', city_id: 'nanjing', time: '春节至元宵', description: '夫子庙灯火满市井'});
CREATE (:Festival {id: 'sh_guojiyishujie', name: '上海国际艺术节', city_id: 'shanghai', time: '10-11月', description: '国际文化艺术盛会'});
CREATE (:Festival {id: 'tibet_xuedun', name: '雪顿节', city_id: 'tibet', time: '藏历7月', description: '西藏最盛大节日，晒大佛藏戏'});
CREATE (:Festival {id: 'tibet_zanglixinnian', name: '藏历新年', city_id: 'tibet', time: '藏历1月', description: '西藏最隆重节日'});

// ============================================
// 第十三步: 创建特产节点
// ============================================

CREATE (:Specialty {id: 'nj_yunjin_sp', name: '云锦', city_id: 'nanjing', category: '工艺品', description: '南京三宝之一，寸锦寸金'});
CREATE (:Specialty {id: 'tibet_tangka', name: '唐卡', city_id: 'tibet', category: '工艺品', description: '藏族传统绘画艺术'});

// ============================================
// 第十四步: 创建关系
// ============================================

// 总结点连接各城市/地区
MATCH (s:SummaryNode {id: 'summary_node'}), (c:City {id: 'beijing'})
CREATE (s)-[:IS_POPULAR_DESTINATION {region: '华北地区'}]->(c);

MATCH (s:SummaryNode {id: 'summary_node'}), (c:City {id: 'nanjing'})
CREATE (s)-[:IS_POPULAR_DESTINATION {region: '华东地区'}]->(c);

MATCH (s:SummaryNode {id: 'summary_node'}), (c:City {id: 'shanghai'})
CREATE (s)-[:IS_POPULAR_DESTINATION {region: '华东地区'}]->(c);

MATCH (s:SummaryNode {id: 'summary_node'}), (r:Region {id: 'tibet'})
CREATE (s)-[:IS_POPULAR_DESTINATION {region: '西南地区'}]->(r);

// 西藏连接子地区
MATCH (r:Region {id: 'tibet'}), (sr:SubRegion {id: 'lhasa'})
CREATE (r)-[:HAS_SUBREGION {position: '首府'}]->(sr);

MATCH (r:Region {id: 'tibet'}), (sr:SubRegion {id: 'nyingchi'})
CREATE (r)-[:HAS_SUBREGION {position: '东南部'}]->(sr);

MATCH (r:Region {id: 'tibet'}), (sr:SubRegion {id: 'shannan'})
CREATE (r)-[:HAS_SUBREGION {position: '南部'}]->(sr);

MATCH (r:Region {id: 'tibet'}), (sr:SubRegion {id: 'shigatse'})
CREATE (r)-[:HAS_SUBREGION {position: '西南部'}]->(sr);

MATCH (r:Region {id: 'tibet'}), (sr:SubRegion {id: 'ngari'})
CREATE (r)-[:HAS_SUBREGION {position: '西部'}]->(sr);

MATCH (r:Region {id: 'tibet'}), (sr:SubRegion {id: 'nagqu'})
CREATE (r)-[:HAS_SUBREGION {position: '北部'}]->(sr);

MATCH (r:Region {id: 'tibet'}), (sr:SubRegion {id: 'chamdo'})
CREATE (r)-[:HAS_SUBREGION {position: '东北部'}]->(sr);

// 城市拥有景点关系
MATCH (c:City {id: 'beijing'}), (a:Attraction)
WHERE a.city_id = 'beijing'
CREATE (c)-[:HAS_ATTRACTION]->(a);

MATCH (c:City {id: 'nanjing'}), (a:Attraction)
WHERE a.city_id = 'nanjing'
CREATE (c)-[:HAS_ATTRACTION]->(a);

MATCH (c:City {id: 'shanghai'}), (a:Attraction)
WHERE a.city_id = 'shanghai'
CREATE (c)-[:HAS_ATTRACTION]->(a);

// 西藏子地区拥有景点关系
MATCH (sr:SubRegion {id: 'lhasa'}), (a:Attraction)
WHERE a.city_id = 'lhasa'
CREATE (sr)-[:HAS_ATTRACTION]->(a);

MATCH (sr:SubRegion {id: 'nyingchi'}), (a:Attraction)
WHERE a.city_id = 'nyingchi'
CREATE (sr)-[:HAS_ATTRACTION]->(a);

MATCH (sr:SubRegion {id: 'shannan'}), (a:Attraction)
WHERE a.city_id = 'shannan'
CREATE (sr)-[:HAS_ATTRACTION]->(a);

MATCH (sr:SubRegion {id: 'shigatse'}), (a:Attraction)
WHERE a.city_id = 'shigatse'
CREATE (sr)-[:HAS_ATTRACTION]->(a);

MATCH (sr:SubRegion {id: 'ngari'}), (a:Attraction)
WHERE a.city_id = 'ngari'
CREATE (sr)-[:HAS_ATTRACTION]->(a);

MATCH (sr:SubRegion {id: 'nagqu'}), (a:Attraction)
WHERE a.city_id = 'nagqu'
CREATE (sr)-[:HAS_ATTRACTION]->(a);

MATCH (sr:SubRegion {id: 'chamdo'}), (a:Attraction)
WHERE a.city_id = 'chamdo'
CREATE (sr)-[:HAS_ATTRACTION]->(a);

// 城市拥有美食关系
MATCH (c:City {id: 'beijing'}), (f:Food)
WHERE f.city_id = 'beijing'
CREATE (c)-[:HAS_FOOD]->(f);

MATCH (c:City {id: 'nanjing'}), (f:Food)
WHERE f.city_id = 'nanjing'
CREATE (c)-[:HAS_FOOD]->(f);

MATCH (c:City {id: 'shanghai'}), (f:Food)
WHERE f.city_id = 'shanghai'
CREATE (c)-[:HAS_FOOD]->(f);

MATCH (r:Region {id: 'tibet'}), (f:Food)
WHERE f.city_id = 'tibet'
CREATE (r)-[:HAS_FOOD]->(f);

// 城市拥有餐厅关系
MATCH (c:City {id: 'beijing'}), (r:Restaurant)
WHERE r.city_id = 'beijing'
CREATE (c)-[:HAS_RESTAURANT]->(r);

MATCH (c:City {id: 'nanjing'}), (r:Restaurant)
WHERE r.city_id = 'nanjing'
CREATE (c)-[:HAS_RESTAURANT]->(r);

MATCH (c:City {id: 'shanghai'}), (r:Restaurant)
WHERE r.city_id = 'shanghai'
CREATE (c)-[:HAS_RESTAURANT]->(r);

MATCH (sr:SubRegion {id: 'lhasa'}), (r:Restaurant)
WHERE r.city_id = 'lhasa'
CREATE (sr)-[:HAS_RESTAURANT]->(r);

// 城市拥有住宿关系
MATCH (c:City {id: 'beijing'}), (h:Hotel)
WHERE h.city_id = 'beijing'
CREATE (c)-[:HAS_HOTEL]->(h);

MATCH (c:City {id: 'nanjing'}), (h:Hotel)
WHERE h.city_id = 'nanjing'
CREATE (c)-[:HAS_HOTEL]->(h);

MATCH (c:City {id: 'shanghai'}), (h:Hotel)
WHERE h.city_id = 'shanghai'
CREATE (c)-[:HAS_HOTEL]->(h);

MATCH (sr:SubRegion {id: 'lhasa'}), (h:Hotel)
WHERE h.city_id = 'lhasa'
CREATE (sr)-[:HAS_HOTEL]->(h);

// 城市拥有节庆关系
MATCH (c:City {id: 'nanjing'}), (f:Festival)
WHERE f.city_id = 'nanjing'
CREATE (c)-[:HAS_FESTIVAL]->(f);

MATCH (c:City {id: 'shanghai'}), (f:Festival)
WHERE f.city_id = 'shanghai'
CREATE (c)-[:HAS_FESTIVAL]->(f);

MATCH (r:Region {id: 'tibet'}), (f:Festival)
WHERE f.city_id = 'tibet'
CREATE (r)-[:HAS_FESTIVAL]->(f);

// 城市拥有特产关系
MATCH (c:City {id: 'nanjing'}), (sp:Specialty)
WHERE sp.city_id = 'nanjing'
CREATE (c)-[:HAS_SPECIALTY]->(sp);

MATCH (r:Region {id: 'tibet'}), (sp:Specialty)
WHERE sp.city_id = 'tibet'
CREATE (r)-[:HAS_SPECIALTY]->(sp);

// ============================================
// 第十五步: 创建景点之间的关系
// ============================================

// 北京皇城古迹关系
MATCH (a1:Attraction {id: 'bj_gugong'}), (a2:Attraction {id: 'bj_jingshanpark'})
CREATE (a1)-[:NEARBY {area: '中轴线', transport: '步行'}]->(a2);

MATCH (a1:Attraction {id: 'bj_gugong'}), (a2:Attraction {id: 'bj_tiananmen'})
CREATE (a1)-[:NEARBY {area: '中轴线', transport: '步行'}]->(a2);

MATCH (a1:Attraction {id: 'bj_beihaipark'}), (a2:Attraction {id: 'bj_houhai'})
CREATE (a1)-[:NEARBY {area: '什刹海', transport: '步行'}]->(a2);

// 北京后奥运景点关系
MATCH (a1:Attraction {id: 'bj_niaochao'}), (a2:Attraction {id: 'bj_shuilifang'})
CREATE (a1)-[:NEARBY {area: '奥林匹克公园', transport: '步行'}]->(a2);

MATCH (a1:Attraction {id: 'bj_niaochao'}), (a2:Attraction {id: 'bj_aolinpike'})
CREATE (a1)-[:NEARBY {area: '奥林匹克公园', transport: '步行'}]->(a2);

// 上海外滩周边
MATCH (a1:Attraction {id: 'sh_waitan'}), (a2:Attraction {id: 'sh_nanjinglu'})
CREATE (a1)-[:NEARBY {area: '外滩周边', transport: '步行'}]->(a2);

// 上海陆家嘴
MATCH (a1:Attraction {id: 'sh_dongfangmingzhu'}), (a2:Attraction {id: 'sh_jinmao'})
CREATE (a1)-[:NEARBY {area: '陆家嘴', transport: '步行'}]->(a2);

// 拉萨老城区
MATCH (a1:Attraction {id: 'lhasa_budala'}), (a2:Attraction {id: 'lhasa_dazhao'})
CREATE (a1)-[:NEARBY {area: '拉萨老城', transport: '步行'}]->(a2);

MATCH (a1:Attraction {id: 'lhasa_dazhao'}), (a2:Attraction {id: 'lhasa_bakuo'})
CREATE (a1)-[:NEARBY {area: '拉萨老城', transport: '步行'}]->(a2);

// 阿里神山圣湖
MATCH (a1:Attraction {id: 'ngari_gangrenboqi'}), (a2:Attraction {id: 'ngari_mapangyongcuo'})
CREATE (a1)-[:NEARBY {area: '神山圣湖', transport: '包车'}]->(a2);

// ============================================
// 完成! 
// ============================================

RETURN "旅游图数据库导入完成！" AS message;
