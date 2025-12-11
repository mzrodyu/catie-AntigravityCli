from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool

from app.config import settings

# SQLite 配置
engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={
        "check_same_thread": False,
        "timeout": 30
    },
    poolclass=StaticPool
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 启用 WAL 模式
    async with engine.begin() as conn:
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA busy_timeout=30000")


async def get_db():
    """获取数据库会话"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
