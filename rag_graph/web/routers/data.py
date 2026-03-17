import os
import glob
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException

from config.config import DEFAULT_CONFIG

router = APIRouter()

@router.get("/files")
async def get_files(type: str = "normalized", source: str = "scrapling", page: int = 1, size: int = 20):
    data_dir = os.path.join(DEFAULT_CONFIG.PROJECT_ROOT, "data", source, type)
    
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

@router.get("/files/{filename:path}")
async def get_file_content(filename: str):
    # Determine full path. If filename is an absolute path, use it directly (with security check)
    if os.path.isabs(filename):
        filepath = filename
    else:
        # For simplicity, fallback search in all data directories if needed
        # Or require full path passed from frontend (which we do in files list)
        filepath = filename
        
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
        
    if not filepath.startswith(os.path.join(DEFAULT_CONFIG.PROJECT_ROOT, "data")):
        raise HTTPException(status_code=403, detail="Access denied")
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # If data is list and has items, slice to 20
        if isinstance(data, list):
            data = data[:20]
        elif isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            data["items"] = data["items"][:20]
            
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
