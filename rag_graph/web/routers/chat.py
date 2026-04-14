import json
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    stream: bool = True

@router.post("/stream")
async def chat_stream(request: Request, body: ChatRequest):
    app_state = request.app.state

    if not getattr(app_state, "system_ready", False):
        async def err_stream():
            yield f"data: {json.dumps({'type': 'error', 'content': '系统未就绪，请等待初始化完成'})}\n\n"
        return StreamingResponse(err_stream(), media_type="text/event-stream")

    rag_app = app_state.rag_app
    # 使用当前事件循环（线程安全）
    loop = asyncio.get_running_loop()
    question = body.question  # 本地副本避免闭包问题

    async def event_generator():
        queue = asyncio.Queue()
        cancelled = False

        def sync_generator():
            try:
                # 智能路由检索
                relevant_docs, analysis = rag_app.query_router.route_query(question, rag_app.config.top_k)
                if not relevant_docs:
                    loop.call_soon_threadsafe(queue.put_nowait, {"type": "chunk", "content": "抱歉，没有找到相关的旅游信息。请尝试其他问题。"})
                    loop.call_soon_threadsafe(queue.put_nowait, None)
                    return

                for chunk in rag_app.generation_module.generate_adaptive_answer_stream(question, relevant_docs):
                    if cancelled:  # 检查是否已取消
                        break
                    loop.call_soon_threadsafe(queue.put_nowait, {"type": "chunk", "content": chunk})

                loop.call_soon_threadsafe(queue.put_nowait, None)
            except Exception as e:
                if not cancelled:
                    loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "content": str(e)})
                    loop.call_soon_threadsafe(queue.put_nowait, None)

        # 在后台线程中运行同步生成器
        task = loop.run_in_executor(None, sync_generator)

        try:
            while True:
                # 使用 timeout 以便能够响应取消
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                if item is None:
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    break
                yield f"data: {json.dumps(item)}\n\n"
        except asyncio.CancelledError:
            # 客户端断开连接，取消后台任务
            nonlocal cancelled
            cancelled = True
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            raise  # 重新抛出以便 FastAPI 正确处理

@router.post("/query")
async def chat_query(request: Request, body: ChatRequest):
    app_state = request.app.state
    if not getattr(app_state, "system_ready", False):
        return {"error": "系统未就绪，请等待初始化完成"}
        
    rag_app = app_state.rag_app
    loop = asyncio.get_running_loop()
    
    import time
    start = time.time()
    
    def sync_query():
        return rag_app.query(body.question, stream=False)
        
    try:
        answer = await loop.run_in_executor(None, sync_query)
        elapsed_ms = int((time.time() - start) * 1000)
        return {"answer": answer, "elapsed_ms": elapsed_ms}
    except Exception as e:
        return {"error": str(e)}
