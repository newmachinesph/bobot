from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import settings

engine = create_async_engine(
    settings.async_database_url,
    echo=settings.ENVIRONMENT == "development",
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={"ssl": True},
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
