from sqlmodel import create_engine, Session
from sqlalchemy_utils import database_exists, create_database
from core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
)


def get_db():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def check_database_has_create():
    if not database_exists(engine.url):
        create_database(engine.url)
