import os
import glob
import json
import urllib.parse
from datetime import datetime
from fastapi import APIRouter, HTTPException

from config.config import PROJECT_ROOT

router = APIRouter()

@router.get("/files", summary="获取文件列表")
async def get_files(type: str = "normalized", source: str = "scrapling", page: int = 1, size: int = 20):
    """
    获取数据文件列表

    - type: 数据类型 (normalized|raw)
    - source: 数据来源 (scrapling|toolbbrowser)
    - page: 页码
    - size: 每页数量
    """
    data_dir = os.path.join(PROJECT_ROOT, "data", source, type)

    if not os.path.exists(data_dir):
        return {"total": 0, "files": []}

    files = []
    pattern = os.path.join(data_dir, "*.json")
    for filepath in glob.glob(pattern):
        stat = os.stat(filepath)
        filename = os.path.basename(filepath)
        files.append({
            "filename": filename,
            "path": filepath,
            "size_kb": round(stat.st_size / 1024, 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })

    # Sort by modified time descending
    files.sort(key=lambda x: x["modified"], reverse=True)

    total = len(files)
    start_idx = (page - 1) * size
    end_idx = start_idx + size

    return {
        "total": total,
        "files": files[start_idx:end_idx]
    }


@router.get("/content")
async def get_file_content(path: str):
    """获取文件内容，通过 query 参数传递路径"""
    # URL 解码路径
    filepath = urllib.parse.unquote(path)

    # 规范化路径（解决 .. 等相对路径问题）
    filepath = os.path.normpath(filepath)
    data_dir = os.path.normpath(os.path.join(PROJECT_ROOT, "data"))

    # 使用 realpath 解析所有符号链接和相对路径
    real_filepath = os.path.realpath(filepath)
    real_data_dir = os.path.realpath(data_dir)

    # 调试信息
    print(f"[DEBUG] Requested filepath: {filepath}")
    print(f"[DEBUG] Data directory: {data_dir}")
    print(f"[DEBUG] Real filepath: {real_filepath}")
    print(f"[DEBUG] Real data dir: {real_data_dir}")
    print(f"[DEBUG] File exists: {os.path.exists(real_filepath)}")

    # 检查文件是否存在
    if not os.path.exists(real_filepath):
        raise HTTPException(status_code=404, detail=f"File not found: {filepath}")

    # 使用 startswith 检查，确保路径以 data 目录开头
    if not real_filepath.startswith(real_data_dir):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: file {real_filepath} is outside data directory {real_data_dir}"
        )

    try:
        # 使用 real_filepath 打开文件，确保符号链接被正确解析
        with open(real_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # If data is list and has items, slice to 20
        if isinstance(data, list):
            data = data[:20]
        elif isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            data["items"] = data["items"][:20]

        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
