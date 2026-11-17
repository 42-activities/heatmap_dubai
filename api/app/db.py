import os

from sqlalchemy import create_engine


def engine():
    return create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True, connect_args={"connect_timeout": 3})
