from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date
import json

from app.database import get_db
from app.models.user import User, UsageLog
from app.services.auth import get_current_user
from app.services.token_pool import TokenPool
from app.services.gemini_client import GeminiClient
from app.config import settings

router = APIRouter(prefix="/v1", tags=["API代理"])


async def check_quota(user: User, db: AsyncSession):
    """检查用户配额"""
    today = date.today()
    result = await db.execute(
        select(func.count(UsageLog.id)).where(
            UsageLog.user_id == user.id,
            func.date(UsageLog.created_at) == today
        )
    )
    today_usage = result.scalar() or 0
    
    if today_usage >= user.daily_quota:
        raise HTTPException(status_code=429, detail="已达到今日配额限制")
    
    return today_usage


@router.get("/models")
async def list_models(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取可用模型列表"""
    base_models = [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-3-pro-preview",
    ]
    
    models = []
    for base in base_models:
        models.append({"id": base, "object": "model", "owned_by": "google"})
        models.append({"id": f"假流式/{base}", "object": "model", "owned_by": "google"})
        models.append({"id": f"流式抗截断/{base}", "object": "model", "owned_by": "google"})
    
    return {"object": "list", "data": models}


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """聊天补全 API - 直接调用 Google Cloud API"""
    await check_quota(user, db)
    
    body = await request.json()
    model = body.get("model", "gemini-2.5-flash")
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    
    if not messages:
        raise HTTPException(status_code=400, detail="messages 不能为空")
    
    # 获取 token
    token_info = await TokenPool.get_token_for_request(db, user, model)
    if not token_info:
        raise HTTPException(status_code=503, detail="没有可用的 Token，请上传或等待")
    
    token_id, token_obj = token_info
    
    # 获取有效的 access_token（自动刷新）
    access_token = await TokenPool.get_access_token(token_obj, db)
    if not access_token:
        await TokenPool.report_failure(db, token_id, "Token 刷新失败")
        raise HTTPException(status_code=503, detail="Token 已失效，无法刷新")
    
    # 获取 project_id
    project_id = token_obj.project_id or ""
    
    print(f"[Proxy] 使用 Token #{token_id}, project_id: {project_id}, model: {model}", flush=True)
    
    # 记录使用
    log = UsageLog(user_id=user.id, token_id=token_id, model=model)
    db.add(log)
    await db.commit()
    
    # 创建 Gemini 客户端
    client = GeminiClient(access_token, project_id)
    
    try:
        if stream:
            async def stream_response():
                try:
                    async for chunk in client.chat_completions_stream(
                        model=model,
                        messages=messages,
                        **{k: v for k, v in body.items() if k not in ["model", "messages", "stream"]}
                    ):
                        yield chunk
                    await TokenPool.report_success(db, token_id)
                except Exception as e:
                    await TokenPool.report_failure(db, token_id, str(e))
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return StreamingResponse(
                stream_response(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            result = await client.chat_completions(
                model=model,
                messages=messages,
                **{k: v for k, v in body.items() if k not in ["model", "messages", "stream"]}
            )
            await TokenPool.report_success(db, token_id)
            return JSONResponse(content=result)
    
    except Exception as e:
        await TokenPool.report_failure(db, token_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))
