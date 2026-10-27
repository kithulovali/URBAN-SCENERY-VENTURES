import pytest
import models  # noqa: F401 - register all ORM models with the declarative metadata
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from settings import Model


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Model.metadata.create_all(bind=engine)
    try:
        with Session(engine, expire_on_commit=False) as db:
            yield db
    finally:
        Model.metadata.drop_all(bind=engine)
        engine.dispose()
