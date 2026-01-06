from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask_sqlalchemy import SQLAlchemy
import os

DATABASE_URL = os.environ.get("POSTGRES_URI") or os.environ.get(
    "DATABASE_URL", "postgresql://user:password@localhost:5432/produtos_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Instância do SQLAlchemy para uso no Flask
db = SQLAlchemy()
