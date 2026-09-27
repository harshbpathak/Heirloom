"""Alembic environment wired to Heirloom's SQLAlchemy metadata.

Heirloom creates fresh per-repo databases with ``Base.metadata.create_all``;
Alembic exists for evolving existing databases between releases. Point
``sqlalchemy.url`` (or ``-x db=<path>``) at the database to upgrade.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from core.models.db_models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

db_override = context.get_x_argument(as_dictionary=True).get("db")
if db_override:
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_override}")


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (emits SQL)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
