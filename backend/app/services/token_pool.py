from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, Tuple
import httpx
import random

from app.models.user import Token, User
from app.config import settings
from app.services.crypto import decrypt_token


class TokenPool:
    """Token 池管理"""
    
    @staticmethod
    async def get_token_for_request(
        db: AsyncSession,
        user: User,
        model: str = None
    ) -> Optional[Tuple[int, str]]:
        """获取一个可用的 token"""
        
        # 判断模型类型
        is_claude = model and "claude" in model.lower()
        is_gemini = model and "gemini" in model.lower()
        
        # 构建查询条件
        query = select(Token).where(
            Token.is_active == True,
            Token.is_public == True
        )
        
        # 按模型类型筛选
        if is_claude:
            query = query.where(Token.supports_claude == True)
        elif is_gemini:
            query = query.where(Token.supports_gemini == True)
        
        result = await db.execute(query)
        tokens = result.scalars().all()
        
        if not tokens:
            # 如果公共池没有，尝试用户自己的 token
            user_query = select(Token).where(
                Token.user_id == user.id,
                Token.is_active == True
            )
            if is_claude:
                user_query = user_query.where(Token.supports_claude == True)
            elif is_gemini:
                user_query = user_query.where(Token.supports_gemini == True)
            
            result = await db.execute(user_query)
            tokens = result.scalars().all()
        
        if not tokens:
            return None
        
        # 随机选择一个 token
        token = random.choice(tokens)
        decrypted = decrypt_token(token.token)
        
        return (token.id, decrypted)
    
    @staticmethod
    async def report_success(db: AsyncSession, token_id: int):
        """报告成功使用"""
        result = await db.execute(select(Token).where(Token.id == token_id))
        token = result.scalar_one_or_none()
        if token:
            token.success_count += 1
            token.last_used = func.now()
            token.last_error = None
            await db.commit()
    
    @staticmethod
    async def report_failure(db: AsyncSession, token_id: int, error: str):
        """报告使用失败"""
        result = await db.execute(select(Token).where(Token.id == token_id))
        token = result.scalar_one_or_none()
        if token:
            token.failure_count += 1
            token.last_error = error[:500] if error else None
            
            # 如果是认证错误，禁用 token
            if "401" in error or "403" in error or "unauthorized" in error.lower():
                token.is_active = False
                
                # 扣除用户额度
                if token.is_public and token.user_id:
                    user_result = await db.execute(select(User).where(User.id == token.user_id))
                    user = user_result.scalar_one_or_none()
                    if user:
                        deduct = settings.quota_claude + settings.quota_gemini
                        if user.daily_quota - settings.default_daily_quota >= deduct:
                            user.daily_quota = max(settings.default_daily_quota, user.daily_quota - deduct)
                            print(f"[Token失效] 用户 {user.username} 扣除 {deduct} 额度", flush=True)
            
            await db.commit()
    
    @staticmethod
    async def verify_token(token: str) -> dict:
        """验证 token 有效性"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # 尝试调用 models 接口验证
                response = await client.get(
                    f"{settings.antigravity_api_base}/models",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("data", [])
                    
                    supports_claude = any("claude" in m.get("id", "").lower() for m in models)
                    supports_gemini = any("gemini" in m.get("id", "").lower() for m in models)
                    
                    return {
                        "valid": True,
                        "supports_claude": supports_claude,
                        "supports_gemini": supports_gemini,
                        "models": [m.get("id") for m in models]
                    }
                else:
                    return {"valid": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    @staticmethod
    async def get_pool_stats(db: AsyncSession) -> dict:
        """获取 token 池统计"""
        # 总数
        total_result = await db.execute(select(func.count(Token.id)).where(Token.is_public == True))
        total = total_result.scalar() or 0
        
        # 有效数
        valid_result = await db.execute(
            select(func.count(Token.id)).where(Token.is_public == True, Token.is_active == True)
        )
        valid = valid_result.scalar() or 0
        
        # Claude 可用
        claude_result = await db.execute(
            select(func.count(Token.id)).where(
                Token.is_public == True, Token.is_active == True, Token.supports_claude == True
            )
        )
        claude = claude_result.scalar() or 0
        
        # Gemini 可用
        gemini_result = await db.execute(
            select(func.count(Token.id)).where(
                Token.is_public == True, Token.is_active == True, Token.supports_gemini == True
            )
        )
        gemini = gemini_result.scalar() or 0
        
        return {
            "total": total,
            "valid": valid,
            "invalid": total - valid,
            "claude": claude,
            "gemini": gemini
        }
