from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import httpx
import secrets
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User, Token
from app.services.auth import get_current_user, get_current_admin
from app.services.crypto import encrypt_token
from app.config import settings

router = APIRouter(prefix="/api/oauth", tags=["OAuth认证"])

# OAuth 配置
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Antigravity 需要的 scope
OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# 存储 OAuth state
oauth_states = {}


class OAuthConfig(BaseModel):
    client_id: str
    client_secret: str


class ManualTokenInput(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int = 3600
    is_public: bool = False


class CallbackURLRequest(BaseModel):
    callback_url: str
    is_public: bool = False


@router.get("/config")
async def get_oauth_config(admin: User = Depends(get_current_admin)):
    """获取 OAuth 配置状态"""
    return {
        "configured": bool(settings.google_client_id and settings.google_client_secret),
        "client_id": settings.google_client_id[:20] + "..." if settings.google_client_id else None
    }


@router.post("/config")
async def set_oauth_config(
    config: OAuthConfig,
    admin: User = Depends(get_current_admin)
):
    """设置 OAuth 配置"""
    settings.google_client_id = config.client_id
    settings.google_client_secret = config.client_secret
    return {"message": "配置已更新"}


@router.get("/auth-url")
async def get_auth_url(user: User = Depends(get_current_user)):
    """获取 OAuth 认证链接"""
    if not settings.google_client_id:
        raise HTTPException(status_code=400, detail="未配置 OAuth Client ID")
    
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {"user_id": user.id}
    
    # 使用 localhost:8080 作为回调（Antigravity 标准）
    redirect_uri = "http://localhost:8080"
    
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(OAUTH_SCOPES),
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    
    from urllib.parse import urlencode
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    return {"auth_url": auth_url, "state": state}


@router.post("/callback")
async def oauth_callback(
    request: CallbackURLRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """处理 OAuth 回调 URL"""
    from urllib.parse import urlparse, parse_qs
    
    parsed = urlparse(request.callback_url)
    params = parse_qs(parsed.query)
    
    code = params.get("code", [None])[0]
    if not code:
        raise HTTPException(status_code=400, detail="回调 URL 中没有 code 参数")
    
    # 交换 token
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": "http://localhost:8080",
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Token 交换失败: {response.text}")
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3600)
            
            if not access_token or not refresh_token:
                raise HTTPException(status_code=400, detail="未获取到完整的 Token")
            
            # 获取用户邮箱
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            email = None
            if userinfo_response.status_code == 200:
                email = userinfo_response.json().get("email")
            
            # 获取 project_id
            project_id = ""
            try:
                projects_response = await client.get(
                    "https://cloudresourcemanager.googleapis.com/v1/projects",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if projects_response.status_code == 200:
                    projects = projects_response.json().get("projects", [])
                    if projects:
                        for p in projects:
                            if "default" in p.get("projectId", "").lower():
                                project_id = p.get("projectId")
                                break
                        if not project_id:
                            project_id = projects[0].get("projectId", "")
                        print(f"[OAuth] 获取到 project_id: {project_id}", flush=True)
                        
                        # 启用必需的 API 服务
                        for service in ["geminicloudassist.googleapis.com", "cloudaicompanion.googleapis.com"]:
                            try:
                                await client.post(
                                    f"https://serviceusage.googleapis.com/v1/projects/{project_id}/services/{service}:enable",
                                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                                    json={}
                                )
                            except:
                                pass
            except Exception as e:
                print(f"[OAuth] 获取 project_id 失败: {e}", flush=True)
            
            # 检查是否已存在
            existing = await db.execute(
                select(Token).where(Token.user_id == user.id, Token.email == email)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail=f"该邮箱 {email} 的 Token 已存在")
            
            # 计算过期时间戳
            import time
            expires_at = int(time.time()) + expires_in
            
            # 构建 token 格式: access_token|||refresh_token|||expires_at
            stored_token = f"{access_token}|||{refresh_token}|||{expires_at}"
            
            # 保存 Token
            new_token = Token(
                user_id=user.id,
                token=encrypt_token(stored_token),
                email=email,
                project_id=project_id,
                is_active=True,
                is_public=request.is_public,
                supports_claude=True,
                supports_gemini=True,
            )
            db.add(new_token)
            
            # 奖励额度
            if request.is_public:
                reward = settings.quota_claude + settings.quota_gemini
                user.daily_quota += reward
                print(f"[OAuth] 用户 {user.username} 获取凭证 {email}，获得 {reward} 额度", flush=True)
            
            await db.commit()
            
            return {
                "message": "Token 获取成功",
                "email": email,
                "supports_claude": True,
                "supports_gemini": True
            }
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="请求超时")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


class ManualTokenInputWithProject(BaseModel):
    access_token: str
    refresh_token: str
    project_id: str = ""
    expires_in: int = 3600
    is_public: bool = False


@router.post("/manual")
async def manual_token_input(
    token_input: ManualTokenInputWithProject,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """手动填入 Token"""
    import time
    
    # 尝试获取邮箱和 project_id
    email = None
    project_id = token_input.project_id
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 获取邮箱
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {token_input.access_token}"}
            )
            if response.status_code == 200:
                email = response.json().get("email")
            
            # 如果没有提供 project_id，尝试获取
            if not project_id:
                try:
                    projects_response = await client.get(
                        "https://cloudresourcemanager.googleapis.com/v1/projects",
                        headers={"Authorization": f"Bearer {token_input.access_token}"}
                    )
                    if projects_response.status_code == 200:
                        projects = projects_response.json().get("projects", [])
                        if projects:
                            project_id = projects[0].get("projectId", "")
                            print(f"[Manual] 自动获取 project_id: {project_id}", flush=True)
                except:
                    pass
    except:
        pass
    
    # 计算过期时间戳
    expires_at = int(time.time()) + token_input.expires_in
    
    # 构建 token 格式: access_token|||refresh_token|||expires_at
    stored_token = f"{token_input.access_token}|||{token_input.refresh_token}|||{expires_at}"
    
    # 保存 Token
    new_token = Token(
        user_id=user.id,
        token=encrypt_token(stored_token),
        email=email,
        project_id=project_id,
        is_active=True,
        is_public=token_input.is_public,
        supports_claude=True,
        supports_gemini=True,
    )
    db.add(new_token)
    
    # 奖励额度
    if token_input.is_public:
        reward = settings.quota_claude + settings.quota_gemini
        user.daily_quota += reward
        print(f"[Manual] 用户 {user.username} 手动添加凭证，获得 {reward} 额度", flush=True)
    
    await db.commit()
    
    return {
        "message": "Token 添加成功",
        "email": email,
        "project_id": project_id
    }
