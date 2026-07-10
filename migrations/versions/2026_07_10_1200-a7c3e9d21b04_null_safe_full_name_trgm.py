"""rebuild full_name trigram indexes on the NULL-safe expression

The ``full_name`` hybrid now renders as
``btrim(coalesce(first_name,'') || ' ' || coalesce(last_name,''))`` so that a
NULL half-name yields the other half instead of NULL (SQL) / TypeError (Python).
A Postgres expression index is only used when the query expression matches it
verbatim, so the trigram indexes from e37117210965 have to be rebuilt on the new
expression — otherwise every "search by name" silently degrades to a seq scan.

``concat_ws`` is not an option here: it is STABLE, not IMMUTABLE, and Postgres
refuses to index it. ``coalesce``/``||``/``btrim`` are all IMMUTABLE.

Revision ID: a7c3e9d21b04
Revises: e37117210965
Create Date: 2026-07-10 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c3e9d21b04"
down_revision: Union[str, None] = "e37117210965"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD = "({table}.first_name || ' ' || {table}.last_name)"
_NEW = (
    "(btrim(coalesce({table}.first_name, '') || ' ' || "
    "coalesce({table}.last_name, '')))"
)


def _rebuild(table: str, expression: str) -> None:
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_full_name_trgm")
    op.execute(
        f"CREATE INDEX ix_{table}_full_name_trgm ON {table} "
        f"USING gin ({expression.format(table=table)} gin_trgm_ops)"
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for table in ("students", "teachers"):
        _rebuild(table, _NEW)


def downgrade() -> None:
    for table in ("students", "teachers"):
        _rebuild(table, _OLD)
