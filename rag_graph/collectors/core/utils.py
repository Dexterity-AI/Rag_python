"""
采集工具函数
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import re


def timestamp_now() -> str:
    """生成ISO格式时间戳字符串，适合用于文件名"""
    now = datetime.utcnow()
    return now.strftime('%Y-%m-%dT%H-%M-%S-%f')[:-3] + 'Z'


def generate_filename(
    source_site: str,
    task_type: str,
    extension: str = 'json',
    suffix: Optional[str] = None,
    stage: str = 'raw'
) -> str:
    """
    生成标准化文件名

    Args:
        source_site: 来源站点，如 'zhihu', 'weibo'
        task_type: 任务类型，如 'hot', 'search', 'article'
        extension: 文件扩展名
        suffix: 可选后缀
        stage: 数据阶段: 'raw', 'normalized', 'processed'

    Returns:
        文件名，如: 'zhihu_hot_raw_2024-03-17T12-30-45-123Z.json'
    """
    parts = [source_site, task_type]

    if suffix:
        parts.append(suffix)

    if stage:
        parts.append(stage)

    parts.append(timestamp_now())

    filename = '_'.join(parts)
    return f"{filename}.{extension}"


def ensure_dir(path: Path) -> Path:
    """确保目录存在，不存在则创建"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(name: str) -> str:
    """清理字符串，使其适合作为文件名"""
    # 替换非法字符为下划线
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    # 限制长度
    if len(name) > 100:
        name = name[:100]
    return name.strip()


def parse_heat_value(heat_str: str) -> Optional[int]:
    """
    解析热度字符串为数值

    Args:
        heat_str: 如 "5802万热度", "1.2k", "10万"

    Returns:
        数值或None
    """
    if not heat_str:
        return None

    # 移除非数字字符，保留小数点和单位
    heat_str = heat_str.strip()

    # 匹配数字部分
    import re
    match = re.search(r'([\d.]+)', heat_str)
    if not match:
        return None

    num = float(match.group(1))

    # 处理单位
    if '万' in heat_str:
        num *= 10000
    elif 'k' in heat_str.lower():
        num *= 1000
    elif '百万' in heat_str:
        num *= 1000000
    elif '亿' in heat_str:
        num *= 100000000

    return int(num)


def safe_json_loads(data: str, default=None):
    """安全解析JSON"""
    import json
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


def merge_dicts(base: dict, override: dict) -> dict:
    """合并两个字典，override的值优先"""
    result = base.copy()
    result.update(override)
    return result
