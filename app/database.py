from datetime import datetime, timedelta, timezone
from typing import List, Optional
from app.config import settings
from sqlalchemy import DateTime, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr

# asyncpg - фишка SQLAlchemy (для python).
# Если использовать его по умолчанию в настройках, то другие программы
# (утилиты бэкапа или миграций) просто сломаются
DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

# Флаг для вывода в консоль всех SQL-запросов для дебага
engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

def get_ttl_time(minutes: int=10):
    return lambda: datetime.now(timezone.utc)+timedelta(minutes=minutes)

# Сердце всей ORM-системы. Типо DbContext из EF
# Базовые настройки уже зашиты в DeclarativeBase
# Что здесь можно указывать:
# - авто генерация имен таблиц (чтобы не писать __tablename__ в каждом классе)
# - глобальные правила именования индексов и внешних ключей
class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower().replace("model", "")


# Описание таблицы в виде ООП-класса (Аналог DbSet из ASP.NET)
class SecretModel(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key_name: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    secret_value: Mapped[str] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_ttl_time(minutes=1),
        index=True
    )


# Для бизнес-логики
class VaultRepository:
    async def save_secret(self, key: str, value: str) -> None:
        async with async_session_maker() as session:
            # Автоматическое открытие транзакции и commit() в конце
            async with session.begin():
                query = select(SecretModel).where(SecretModel.key_name == key)
                result = await session.execute(query)
                # Получаем для объекта (строка из таблицы) из БД. Аналог FirstOrDefault()
                db_secret = result.scalar_one_or_none()

                if db_secret:
                    db_secret.secret_value = value
                else:
                    new_secret = SecretModel(key_name=key, secret_value=value)
                    session.add(new_secret)

    async def get_secret_by_key(self, key: str) -> Optional[str]:
        async with async_session_maker() as session:
            query = select(SecretModel).where(SecretModel.key_name == key)
            result = await session.execute(query)
            db_secret = result.scalar_one_or_none()
            return db_secret.secret_value if db_secret else None

    async def get_all_keys(self) -> List[str]:
        async with async_session_maker() as session:
            query = select(SecretModel.key_name)
            result = await session.execute(query)
            return list(result.scalars().all())