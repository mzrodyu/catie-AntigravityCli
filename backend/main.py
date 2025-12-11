from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.database import init_db
from app.config import settings, load_config_from_db
from app.models.user import User
from app.services.auth import get_password_hash


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    print("🚀 AntigravityCli 启动中...", flush=True)
    await init_db()
    await load_config_from_db()
    await create_admin_user()
    print(f"✅ 服务启动完成 - http://{settings.host}:{settings.port}", flush=True)
    yield
    # 关闭时
    print("👋 服务关闭", flush=True)


app = FastAPI(
    title="AntigravityCli",
    description="Antigravity Token 捐赠云端",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
from app.routers import auth, proxy, public, oauth
app.include_router(auth.router)
app.include_router(proxy.router)
app.include_router(public.router)
app.include_router(oauth.router)

# 静态文件
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
    
    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(static_dir, "index.html"))
    
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = os.path.join(static_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))


async def create_admin_user():
    """创建管理员用户"""
    from app.database import async_session
    from sqlalchemy import select
    
    async with async_session() as db:
        result = await db.execute(select(User).where(User.username == settings.admin_username))
        if not result.scalar_one_or_none():
            admin = User(
                username=settings.admin_username,
                password_hash=get_password_hash(settings.admin_password),
                is_admin=True,
                daily_quota=999999
            )
            db.add(admin)
            await db.commit()
            print(f"✅ 管理员账号已创建: {settings.admin_username}", flush=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
