import os

from sqlalchemy import (
    Column,
    DateTime,
    create_engine, func, MetaData
)
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base

from databases import Database
from sqlalchemy.orm import declared_attr, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

# databases query builder
database = Database(DATABASE_URL)

# SQLAlchemy
engine = create_engine(DATABASE_URL)
LocalSession = sessionmaker(engine)
metadata = MetaData()


def get_db_session():
    with LocalSession() as db:
        yield db
