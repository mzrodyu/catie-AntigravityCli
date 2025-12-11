from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date
import json
import httpx

from app.database import get_db
from app.models.user import User, UsageLog
from app.services.auth import get_current_user
from app.services.token_pool import TokenPool
from app.services.gemini_client import GeminiClient
from app.config import settings


def is_claude_model(model: str) -> bool:
    """判断是否是 Claude 模型"""
    return "claude" in model.lower()

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
    # Gemini 模型
    gemini_models = [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-3-pro-preview",
    ]
    
    # Claude 模型（通过 Antigravity 服务）
    claude_models = [
        "claude-4.5",
        "claude-4.5-op",
    ]
    
    models = []
    for base in gemini_models:
        models.append({"id": base, "object": "model", "owned_by": "google"})
        models.append({"id": f"假流式/{base}", "object": "model", "owned_by": "google"})
        models.append({"id": f"流式抗截断/{base}", "object": "model", "owned_by": "google"})
    
    for base in claude_models:
        models.append({"id": base, "object": "model", "owned_by": "anthropic"})
    
    return {"object": "list", "data": models}


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """聊天补全 API"""
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
    
    # 记录使用
    log = UsageLog(user_id=user.id, token_id=token_id, model=model)
    db.add(log)
    await db.commit()
    
    # Claude 模型 -> 转发到 Antigravity 服务
    if is_claude_model(model):
        return await proxy_to_antigravity(body, stream, token_id, db)
    
    # Gemini 模型 -> 直接调用 Google API
    access_token = await TokenPool.get_access_token(token_obj, db)
    if not access_token:
        await TokenPool.report_failure(db, token_id, "Token 刷新失败")
        raise HTTPException(status_code=503, detail="Token 已失效，无法刷新")
    
    project_id = token_obj.project_id or ""
    print(f"[Proxy] Gemini: Token #{token_id}, project_id: {project_id}, model: {model}", flush=True)
    
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


async def proxy_to_antigravity(body: dict, stream: bool, token_id: int, db: AsyncSession):
    """转发请求到 Antigravity 服务（用于 Claude 模型）"""
    from app.services.crypto import decrypt_token
    from app.models.user import Token
    
    # 获取原始 token
    result = await db.execute(select(Token).where(Token.id == token_id))
    token_obj = result.scalar_one_or_none()
    if not token_obj:
        raise HTTPException(status_code=503, detail="Token 不存在")
    
    decrypted = decrypt_token(token_obj.token)
    # 解析 token 格式
    token_data = TokenPool.parse_token_data(decrypted)
    antigravity_token = token_data["access_token"]
    
    print(f"[Proxy] Claude: 转发到 Antigravity 服务, model: {body.get('model')}", flush=True)
    
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            if stream:
                async def stream_response():
                    try:
                        async with client.stream(
                            "POST",
                            f"{settings.antigravity_api_base}/chat/completions",
                            headers={"Authorization": f"Bearer {antigravity_token}", "Content-Type": "application/json"},
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
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
                )
            else:
                response = await client.post(
                    f"{settings.antigravity_api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {antigravity_token}", "Content-Type": "application/json"},
                    json=body
                )
                if response.status_code != 200:
                    await TokenPool.report_failure(db, token_id, response.text)
                    raise HTTPException(status_code=response.status_code, detail=response.text)
                await TokenPool.report_success(db, token_id)
                return JSONResponse(content=response.json())
    except httpx.TimeoutException:
        await TokenPool.report_failure(db, token_id, "请求超时")
        raise HTTPException(status_code=504, detail="请求超时")
    except Exception as e:
        await TokenPool.report_failure(db, token_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))
