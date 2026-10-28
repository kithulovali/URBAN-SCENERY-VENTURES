import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL or DATABASE_URL == "None":
    DATABASE_URL = "sqlite:///./urban_ventures.db"

# Accept Turso's native libsql:// URL and convert it to SQLAlchemy's dialect URL.
if DATABASE_URL.startswith("libsql://"):
    DATABASE_URL = "sqlite+libsql://" + DATABASE_URL[len("libsql://"):]
    if "?" not in DATABASE_URL:
        DATABASE_URL += "?secure=true"
    elif "secure=" not in DATABASE_URL:
        DATABASE_URL += "&secure=true"

connect_args = {}
if DATABASE_URL.startswith("sqlite+libsql://"):
    auth_token = os.getenv("TURSO_AUTH_TOKEN", "").strip()
    if not auth_token:
        raise RuntimeError(
            "TURSO_AUTH_TOKEN is required when DATABASE_URL points to Turso"
        )
    connect_args["auth_token"] = auth_token
elif DATABASE_URL.startswith("sqlite:///"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)

class Model(DeclarativeBase):
    pass

sessionlocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    bind=engine,
)

def get_db():
    db = sessionlocal()
    try:
        yield db
    finally:
        db.close()
