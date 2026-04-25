"""SQLAlchemy セッション管理。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """アプリ共通の Declarative Base。"""

    pass


def get_db():
    """FastAPI 依存性注入用の DB セッションを提供する。

    Args:
        なし。

    Returns:
        リクエストスコープで利用する DB セッションのジェネレーター。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
