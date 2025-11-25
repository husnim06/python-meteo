import os
import time

import dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

dotenv.load_dotenv()


class Base(DeclarativeBase):
    pass


def create_engine_with_retry(database_url: str, max_retries: int = 3) -> Engine:
    """Создает движок БД с повторными попытками"""
    for attempt in range(max_retries):
        try:
            engine = create_engine(
                database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # Проверка соединения перед использованием
            )

            with engine.connect() as conn:
                pass
            return engine
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2**attempt)

    raise RuntimeError("Не удалось подключиться к БД после нескольких попыток")


DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL переменная среды отсутствует")
engine = create_engine_with_retry(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
