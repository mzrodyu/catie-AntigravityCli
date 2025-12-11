from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.database import get_db
from app.models.user import User, Token
from app.services.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user
)
from app.services.crypto import encrypt_token, decrypt_token
from app.services.token_pool import TokenPool
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register")
async def register(
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    if not settings.allow_registration:
        raise HTTPException(status_code=403, detail="注册已关闭")
    
    # 检查用户名
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建用户
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        daily_quota=settings.default_daily_quota
    )
    db.add(user)
    await db.commit()
    
    token = create_access_token({"sub": username})
    return {"access_token": token, "token_type": "bearer", "message": "注册成功"}


@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="账号已被禁用")
    
    user.last_login = datetime.utcnow()
    await db.commit()
    
    token = create_access_token({"sub": username})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "daily_quota": user.daily_quota
        }
    }


@router.get("/me")
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取当前用户信息"""
    # 统计 token 数量
    result = await db.execute(select(Token).where(Token.user_id == user.id))
    tokens = result.scalars().all()
    
    return {
        "id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "daily_quota": user.daily_quota,
        "token_count": len(tokens),
        "public_token_count": len([t for t in tokens if t.is_public]),
        "created_at": user.created_at.isoformat() if user.created_at else None
    }


@router.get("/tokens")
async def list_my_tokens(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取我的 Token 列表"""
    result = await db.execute(
        select(Token).where(Token.user_id == user.id).order_by(Token.created_at.desc())
    )
    tokens = result.scalars().all()
    
    return [{
        "id": t.id,
        "email": t.email,
        "is_active": t.is_active,
        "is_public": t.is_public,
        "supports_claude": t.supports_claude,
        "supports_gemini": t.supports_gemini,
        "success_count": t.success_count,
        "failure_count": t.failure_count,
        "last_used": t.last_used.isoformat() if t.last_used else None,
        "last_error": t.last_error,
        "created_at": t.created_at.isoformat() if t.created_at else None
    } for t in tokens]


@router.post("/tokens")
async def upload_token(
    token: str = Form(...),
    is_public: bool = Form(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """上传 Token"""
    # 验证 token
    verify_result = await TokenPool.verify_token(token)
    
    if not verify_result["valid"]:
        raise HTTPException(status_code=400, detail=f"Token 无效: {verify_result.get('error', '未知错误')}")
    
    # 加密存储
    encrypted = encrypt_token(token)
    
    # 创建记录
    new_token = Token(
        user_id=user.id,
        token=encrypted,
        is_active=True,
        is_public=is_public,
        supports_claude=verify_result.get("supports_claude", False),
        supports_gemini=verify_result.get("supports_gemini", False)
    )
    db.add(new_token)
    
    # 如果捐赠到公共池，奖励额度
    if is_public:
        reward = settings.quota_claude + settings.quota_gemini
        user.daily_quota += reward
        print(f"[Token上传] 用户 {user.username} 捐赠 Token，获得 {reward} 额度", flush=True)
    
    await db.commit()
    
    return {
        "message": "Token 上传成功",
        "supports_claude": verify_result.get("supports_claude", False),
        "supports_gemini": verify_result.get("supports_gemini", False),
        "models": verify_result.get("models", [])
    }


@router.patch("/tokens/{token_id}")
async def update_token(
    token_id: int,
    is_public: bool = Form(None),
    is_active: bool = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新 Token 状态"""
    result = await db.execute(
        select(Token).where(Token.id == token_id, Token.user_id == user.id)
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token 不存在")
    
    if is_public is not None:
        if is_public and not token.is_public:
            # 捐赠奖励
            if token.is_active:
                reward = settings.quota_claude + settings.quota_gemini
                user.daily_quota += reward
                print(f"[Token捐赠] 用户 {user.username} 获得 {reward} 额度", flush=True)
        elif not is_public and token.is_public:
            # 取消捐赠扣除
            deduct = settings.quota_claude + settings.quota_gemini
            if user.daily_quota - settings.default_daily_quota >= deduct:
                user.daily_quota = max(settings.default_daily_quota, user.daily_quota - deduct)
        token.is_public = is_public
    
    if is_active is not None:
        token.is_active = is_active
    
    await db.commit()
    return {"message": "更新成功"}


@router.delete("/tokens/{token_id}")
async def delete_token(
    token_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除 Token"""
    result = await db.execute(
        select(Token).where(Token.id == token_id, Token.user_id == user.id)
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token 不存在")
    
    # 如果是公共 token，扣除额度
    if token.is_public:
        deduct = settings.quota_claude + settings.quota_gemini
        if user.daily_quota - settings.default_daily_quota >= deduct:
            user.daily_quota = max(settings.default_daily_quota, user.daily_quota - deduct)
    
    await db.delete(token)
    await db.commit()
    return {"message": "删除成功"}
