from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date
import httpx
import json

from app.database import get_db
from app.models.user import User, UsageLog
from app.services.auth import get_current_user
from app.services.token_pool import TokenPool
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
    # 获取一个 token 来查询模型
    token_info = await TokenPool.get_token_for_request(db, user)
    if not token_info:
        return {"object": "list", "data": []}
    
    token_id, token = token_info
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{settings.antigravity_api_base}/models",
                headers={"Authorization": f"Bearer {token}"}
            )
            return response.json()
    except Exception as e:
        return {"object": "list", "data": [], "error": str(e)}


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """聊天补全 API"""
    await check_quota(user, db)
    
    body = await request.json()
    model = body.get("model", "")
    stream = body.get("stream", False)
    
    # 获取 token
    token_info = await TokenPool.get_token_for_request(db, user, model)
    if not token_info:
        raise HTTPException(status_code=503, detail="没有可用的 Token，请上传或等待")
    
    token_id, token = token_info
    
    # 记录使用
    log = UsageLog(user_id=user.id, token_id=token_id, model=model)
    db.add(log)
    await db.commit()
    
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            if stream:
                async def stream_response():
                    try:
                        async with client.stream(
                            "POST",
                            f"{settings.antigravity_api_base}/chat/completions",
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Content-Type": "application/json"
                            },
                            json=body
                        ) as response:
                            if response.status_code != 200:
                                error_text = await response.aread()
                                await TokenPool.report_failure(db, token_id, error_text.decode())
                                yield f"data: {json.dumps({'error': error_text.decode()})}\n\n"
                                return
                            
                            async for chunk in response.aiter_bytes():
                                yield chunk
                            
                            await TokenPool.report_success(db, token_id)
                    except Exception as e:
                        await TokenPool.report_failure(db, token_id, str(e))
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                
                return StreamingResponse(
                    stream_response(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive"
                    }
                )
            else:
                response = await client.post(
                    f"{settings.antigravity_api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json=body
                )
                
                if response.status_code != 200:
                    await TokenPool.report_failure(db, token_id, response.text)
                    raise HTTPException(status_code=response.status_code, detail=response.text)
                
                await TokenPool.report_success(db, token_id)
                return response.json()
    
    except httpx.TimeoutException:
        await TokenPool.report_failure(db, token_id, "请求超时")
        raise HTTPException(status_code=504, detail="请求超时")
    except Exception as e:
        await TokenPool.report_failure(db, token_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))
