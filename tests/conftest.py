import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from models import Model if False else User
from settings import Model


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Model.metadata.create_all(bind=engine)
    with Session(engine, expire_on_commit=False) as db:
        yield db
    Model.metadata.drop_all(bind=engine)
    engine.dispose()
