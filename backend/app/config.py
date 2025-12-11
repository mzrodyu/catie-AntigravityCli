from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 基础配置
    app_name: str = "AntigravityCli"
    secret_key: str = "antigravity-secret-key-change-me"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 5002
    
    # 数据库
    database_url: str = "sqlite+aiosqlite:///./antigravity.db"
    
    # 管理员
    admin_username: str = "admin"
    admin_password: str = "admin123"
    
    # 用户配额
    default_daily_quota: int = 100
    no_credential_quota: int = 0
    
    # Token奖励：按模型分类
    quota_claude: int = 500      # Claude模型额度
    quota_gemini: int = 300      # Gemini模型额度
    
    # 速率限制
    base_rpm: int = 5
    contributor_rpm: int = 10
    
    # 注册
    allow_registration: bool = True
    
    # Antigravity API
    antigravity_api_base: str = "http://127.0.0.1:8045/v1"
    
    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    
    # 公告
    announcement_enabled: bool = False
    announcement_title: str = ""
    announcement_content: str = ""
    
    class Config:
        env_file = ".env"


settings = Settings()


# 可持久化的配置项
PERSISTENT_CONFIG_KEYS = [
    "allow_registration",
    "default_daily_quota",
    "no_credential_quota",
    "quota_claude",
    "quota_gemini",
    "base_rpm",
    "contributor_rpm",
    "announcement_enabled",
    "announcement_title",
    "announcement_content",
]


async def load_config_from_db():
    """从数据库加载配置"""
    from app.database import async_session
    from app.models.user import SystemConfig
    from sqlalchemy import select
    
    async with async_session() as db:
        result = await db.execute(select(SystemConfig))
        configs = result.scalars().all()
        
        for config in configs:
            if hasattr(settings, config.key):
                value = config.value
                attr_type = type(getattr(settings, config.key))
                if attr_type == bool:
                    value = value.lower() in ('true', '1', 'yes')
                elif attr_type == int:
                    value = int(value)
                setattr(settings, config.key, value)
                print(f"[Config] 从数据库加载: {config.key} = {value}")


async def save_config_to_db(key: str, value):
    """保存单个配置到数据库"""
    from app.database import async_session
    from app.models.user import SystemConfig
    from sqlalchemy import select
    
    async with async_session() as db:
        result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        config = result.scalar_one_or_none()
        
        if config:
            config.value = str(value)
        else:
            config = SystemConfig(key=key, value=str(value))
            db.add(config)
        
        await db.commit()
