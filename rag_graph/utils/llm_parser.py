"""
LLM响应解析工具
提供统一的JSON解析和响应处理功能
"""

import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def extract_json_from_markdown(content: str) -> Optional[str]:
    """
    从Markdown代码块中提取JSON内容

    Args:
        content: 可能包含Markdown代码块的文本

    Returns:
        提取的JSON字符串，如果没有找到则返回None
    """
    if not content:
        return None

    content = content.strip()

    # 清理 markdown 代码块
    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    # 提取JSON内容
    json_start = content.find('{')
    json_end = content.rfind('}')

    if json_start == -1 or json_end == -1 or json_end <= json_start:
        return None

    return content[json_start:json_end + 1]


def parse_llm_json_response(content: str,
                            default_value: Optional[Dict] = None) -> Optional[Dict]:
    """
    解析LLM返回的JSON响应
    处理常见的格式问题（Markdown代码块、多余文本等）

    Args:
        content: LLM响应内容
        default_value: 解析失败时返回的默认值

    Returns:
        解析后的字典，失败时返回default_value
    """
    if not content:
        logger.warning("LLM返回空响应")
        return default_value

    try:
        json_str = extract_json_from_markdown(content)
        if json_str is None:
            logger.warning(f"响应中未找到有效的JSON: {content[:200]}")
            return default_value

        return json.loads(json_str)

    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失败: {e}, 内容: {content[:200]}")
        return default_value
    except Exception as e:
        logger.warning(f"解析LLM响应时出错: {e}")
        return default_value


def safe_json_loads(content: str,
                   required_fields: Optional[list] = None) -> tuple[bool, Optional[Dict]]:
    """
    安全地解析JSON并验证必需字段

    Args:
        content: JSON字符串
        required_fields: 必需的字段列表

    Returns:
        (是否成功, 解析结果或None)
    """
    result = parse_llm_json_response(content)

    if result is None:
        return False, None

    if required_fields:
        missing = [f for f in required_fields if f not in result]
        if missing:
            logger.warning(f"JSON缺少必需字段: {missing}")
            return False, result

    return True, result
