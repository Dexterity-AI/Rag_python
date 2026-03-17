import json
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.get("/status")
async def get_status(request: Request):
    app_state = request.app.state
    ready = app_state.system_ready
    
    status = {
        "ready": ready,
        "neo4j": "未连接",
        "milvus": "未连接",
        "model": "未配置",
        "knowledge_base": {
            "total_cities": 0,
            "total_attractions": 0,
            "total_foods": 0,
            "total_documents": 0,
            "total_chunks": 0
        },
        "init_progress": app_state.init_progress
    }
    
    if hasattr(app_state, "rag_app") and app_state.rag_app:
        app_status = app_state.rag_app.get_status()
        status["neo4j"] = app_status.get("neo4j", "未连接")
        status["milvus"] = app_status.get("milvus", "未连接")
        status["model"] = app_status.get("model", "未配置")
        
        if ready and app_state.rag_app.data_module:
            try:
                stats = app_state.rag_app.data_module.get_statistics()
                status["knowledge_base"] = {
                    "total_cities": stats.get('total_cities', 0),
                    "total_attractions": stats.get('total_attractions', 0),
                    "total_foods": stats.get('total_foods', 0),
                    "total_documents": stats.get('total_documents', 0),
                    "total_chunks": stats.get('total_chunks', 0)
                }
            except Exception:
                pass
                
    return status

@router.get("/health")
async def get_health():
    checks = []
    
    # Check Neo4j
    try:
        from config.config import DEFAULT_CONFIG
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            DEFAULT_CONFIG.neo4j_uri,
            auth=(DEFAULT_CONFIG.neo4j_user, DEFAULT_CONFIG.neo4j_password)
        )
        driver.verify_connectivity()
        driver.close()
        checks.append({"name": "Neo4j", "status": True, "message": "连接正常"})
    except Exception as e:
        checks.append({"name": "Neo4j", "status": False, "message": str(e)})
        
    # Check Milvus
    try:
        from pymilvus import connections
        from config.config import DEFAULT_CONFIG
        connections.connect(
            alias="health_check_web",
            host=DEFAULT_CONFIG.milvus_host,
            port=DEFAULT_CONFIG.milvus_port
        )
        connections.disconnect("health_check_web")
        checks.append({"name": "Milvus", "status": True, "message": "连接正常"})
    except Exception as e:
        checks.append({"name": "Milvus", "status": False, "message": str(e)})
        
    # Check LLM API
    try:
        from config.config import DEFAULT_CONFIG
        if DEFAULT_CONFIG.llm_api_key and DEFAULT_CONFIG.llm_base_url:
            checks.append({"name": "LLM API", "status": True, "message": f"已配置 ({DEFAULT_CONFIG.llm_model})"})
        else:
            checks.append({"name": "LLM API", "status": False, "message": "未配置 API Key 或 Base URL"})
    except Exception as e:
        checks.append({"name": "LLM API", "status": False, "message": str(e)})
        
    all_passed = all(c["status"] for c in checks)
    return {
        "checks": checks,
        "all_passed": all_passed
    }

@router.get("/config")
async def get_config():
    from config.config import DEFAULT_CONFIG
    config_dict = DEFAULT_CONFIG.to_dict()
    
    # Hide sensitive info
    filtered_config = {}
    for k, v in config_dict.items():
        if "password" in k.lower() or "key" in k.lower():
            filtered_config[k] = "***" if v else "(未设置)"
        else:
            filtered_config[k] = v if v is not None else "(未设置)"
            
    return filtered_config

@router.post("/initialize")
async def initialize_system(request: Request):
    app_state = request.app.state
    
    if app_state.system_ready:
        return {"status": "already ready"}
        
    # Re-trigger if not ready and not currently running
    def init_rag():
        try:
            app_state.init_progress = "正在初始化系统模块..."
            if not app_state.rag_app.initialize():
                app_state.init_progress = "初始化系统模块失败"
                return
            
            app_state.init_progress = "正在加载知识库..."
            if not app_state.rag_app.build_knowledge_base():
                app_state.init_progress = "加载知识库失败"
                return
            
            app_state.system_ready = True
            app_state.init_progress = "初始化完成"
        except Exception as e:
            app_state.init_progress = f"初始化发生异常: {str(e)}"
            print(f"后台初始化异常: {e}")

    loop = asyncio.get_event_loop()
    app_state.init_task = loop.run_in_executor(None, init_rag)
    
    return {"status": "started"}
