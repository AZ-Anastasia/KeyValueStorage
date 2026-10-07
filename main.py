import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from sqlalchemy import delete
from app.database import SecretModel, engine, Base, async_session_maker
from app.routers import router as secrets_router


async def clean_expired_records_worker():
    CHECK_INTERVAL = 60

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL)

            async with async_session_maker() as session:
                async with session.begin():
                    now = datetime.now(timezone.utc)

                    stmt = delete(SecretModel).where(SecretModel.expires_at < now)
                    result = await session.execute(stmt)

                    if result.rowcount > 0:
                        print(
                            f"[{datetime.now()}] [TTL] Удалено просроченных строк: {result.rowcount}"
                        )

        except Exception as e:
            print(f"[TTL Ошибка] Не удалось очистить базу: {e}")
            await asyncio.sleep(15)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ttl_task=asyncio.create_task(clean_expired_records_worker())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    ttl_task.cancel()
    await engine.dispose()


app = FastAPI(title="Key-Value Storage TTL", lifespan=lifespan, docs_url="/docs")
app.include_router(secrets_router)