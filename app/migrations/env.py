# app/migrations/env.py

import sys
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

config = context.config

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # 這是 /app
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from models import Base
from database import DATABASE_URL

# 在 Alembic 運行時加載 .env 檔案
from dotenv import load_dotenv
load_dotenv()

target_metadata = Base.metadata

db_user = os.getenv('POSTGRES_USER')
db_password = os.getenv('POSTGRES_PASSWORD')
db_host = os.getenv('POSTGRES_HOST')
db_port = os.getenv('POSTGRES_PORT')
db_name = os.getenv('POSTGRES_DB')

if not DATABASE_URL: 
     DATABASE_URL = (
        f"postgresql+psycopg2://{db_user}:"
        f"{db_password}@{db_host}:"
        f"{db_port}/{db_name}"
    )


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    config.set_main_option('sqlalchemy.url', DATABASE_URL) 

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()