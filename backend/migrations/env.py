from logging.config import fileConfig
from sqlmodel import SQLModel
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import settings
from app.model import *

target_metadata = SQLModel.metadata

def run_migrations_offline() -> None:
    url = settings.database_url_sync
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    from sqlalchemy import create_engine
    connectable = create_engine(settings.database_url_sync.replace("sqlite:///../../", "sqlite:///"))
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()