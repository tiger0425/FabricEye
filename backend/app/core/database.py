"""
FabricEye AI验布系统 - 数据库连接模块
该模块负责配置 SQLAlchemy 异步引擎、SessionLocal 以及数据库初始化。
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import AsyncGenerator

from app.core.config import settings

# 创建异步数据库引擎
# SQLite 异步连接需要使用 aiosqlite
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 专用配置，允许在多线程中使用
    echo=True,  # 开发环境下打印 SQL 语句
)

# 创建异步会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 声明式基类，用于定义 ORM 模型
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入函数，用于获取数据库异步会话。
    
    Yields:
        AsyncSession: 异步数据库会话实例
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables() -> None:
    """
    初始化数据库表。
    在应用程序启动时调用，确保所有定义的模型表都已创建。
    """
    async with engine.begin() as conn:
        # 注意：在实际生产中，建议使用 Alembic 进行迁移管理
        # 这里直接使用 Base.metadata.create_all 的异步版本
        await conn.run_sync(Base.metadata.create_all)
