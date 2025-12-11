from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date

from app.database import get_db
from app.models.user import User, Token, UsageLog
from app.services.token_pool import TokenPool
from app.config import settings

router = APIRouter(prefix="/api/public", tags=["公开接口"])


@router.get("/stats")
async def get_public_stats(db: AsyncSession = Depends(get_db)):
    """获取公开统计信息"""
    # 用户数
    user_result = await db.execute(select(func.count(User.id)))
    user_count = user_result.scalar() or 0
    
    # Token 池统计
    pool_stats = await TokenPool.get_pool_stats(db)
    
    # 今日请求数
    today = date.today()
    today_result = await db.execute(
        select(func.count(UsageLog.id)).where(func.date(UsageLog.created_at) == today)
    )
    today_requests = today_result.scalar() or 0
    
    # 总请求数
    total_result = await db.execute(select(func.count(UsageLog.id)))
    total_requests = total_result.scalar() or 0
    
    return {
        "users": user_count,
        "tokens": pool_stats,
        "today_requests": today_requests,
        "total_requests": total_requests
    }


@router.get("/announcement")
async def get_announcement():
    """获取公告"""
    if not settings.announcement_enabled:
        return {"enabled": False}
    
    return {
        "enabled": True,
        "title": settings.announcement_title,
        "content": settings.announcement_content
    }
