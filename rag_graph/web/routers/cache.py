from fastapi import APIRouter
from cache import get_cache_manager

router = APIRouter()

@router.get("/stats")
async def get_cache_stats():
    cache_manager = get_cache_manager()
    return cache_manager.get_stats()

@router.delete("/clear")
async def clear_cache(vector: bool = False, graph: bool = False, llm: bool = False, all: bool = False):
    cache_manager = get_cache_manager()
    
    if all:
        cache_manager.clear_all()
        return {"status": "success", "message": "All caches cleared"}
        
    cleared = []
    if vector:
        cache_manager.clear_vector_cache()
        cleared.append("vector")
    if graph:
        cache_manager.clear_graph_cache()
        cleared.append("graph")
    if llm:
        cache_manager.clear_llm_cache()
        cleared.append("llm")
        
    return {"status": "success", "cleared": cleared}
