import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from collectors import CollectionManager, ToolBbrowserAdapter, ScraplingAdapter

router = APIRouter()

class CollectRequest(BaseModel):
    engine: str
    source: str
    task: str
    url: Optional[str] = None
    keyword: Optional[str] = None
    mock: bool = False

@router.post("/run")
async def collect_run(request: Request, body: CollectRequest):
    loop = asyncio.get_running_loop()
    
    async def event_generator():
        queue = asyncio.Queue()
        
        def sync_collect():
            try:
                manager = CollectionManager()
                if not body.mock:
                    manager.register_collector('toolbbrowser', ToolBbrowserAdapter())
                    manager.register_collector('scrapling', ScraplingAdapter())
                else:
                    manager.register_collector('toolbbrowser', ToolBbrowserAdapter({'mock': True}))
                    manager.register_collector('scrapling', ScraplingAdapter({'mock': True}))
                
                engine = body.engine
                task_config = {
                    'source_site': body.source,
                    'task_type': body.task,
                }
                if body.url:
                    task_config['url'] = body.url
                if body.keyword:
                    task_config['keyword'] = body.keyword
                
                if engine == 'auto':
                    selected_engine = manager.auto_select_engine(task_config)
                    if not selected_engine:
                        loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": "无法自动选择合适的引擎"})
                        loop.call_soon_threadsafe(queue.put_nowait, None)
                        return
                    engine = selected_engine
                    loop.call_soon_threadsafe(queue.put_nowait, {"type": "progress", "message": f"自动选择引擎: {engine}"})
                
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "progress", "message": "采集中..."})
                
                result = manager.collect(
                    engine=engine,
                    task_config=task_config
                )
                
                if result.status == 'success':
                    loop.call_soon_threadsafe(queue.put_nowait, {
                        "type": "result", 
                        "status": "success", 
                        "item_count": result.item_count,
                        "normalized_file": result.normalized_file_path
                    })
                else:
                    loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": result.error_message})
                
                loop.call_soon_threadsafe(queue.put_nowait, None)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(e)})
                loop.call_soon_threadsafe(queue.put_nowait, None)

        task = loop.run_in_executor(None, sync_collect)
        
        while True:
            item = await queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/engines")
async def get_engines():
    manager = CollectionManager()
    manager.register_collector('toolbbrowser', ToolBbrowserAdapter())
    manager.register_collector('scrapling', ScraplingAdapter())
    
    engines = []
    for name in manager.list_collectors():
        collector = manager.get_collector(name)
        health = collector.health_check()
        engines.append({
            "name": name,
            "health": health,
            "available": health.get('cli_available', False) or health.get('module_available', False)
        })
        
    return {"engines": engines}

@router.get("/stats")
async def get_collect_stats():
    manager = CollectionManager()
    stats = manager.get_statistics()
    return stats
