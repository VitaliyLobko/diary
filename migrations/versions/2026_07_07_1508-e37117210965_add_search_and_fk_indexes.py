"""add search and fk indexes

Revision ID: e37117210965
Revises: f1a2b3c4d5e6
Create Date: 2026-07-07 15:08:29.572660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e37117210965'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Foreign keys are not indexed automatically in PostgreSQL; these back the
    # joins used across the grade/discipline/student listings.
    op.create_index("ix_students_group_id", "students", ["group_id"])
    op.create_index("ix_grades_student_id", "grades", ["student_id"])
    op.create_index("ix_grades_discipline_id", "grades", ["discipline_id"])
    op.create_index("ix_disciplines_teacher_id", "disciplines", ["teacher_id"])
    # get_student_contacts filters by (person_id, person_types) together.
    op.create_index(
        "ix_contacts_person", "contacts", ["person_id", "person_types"]
    )

    # Trigram indexes so the "search by full name" ILIKE '%term%' queries can
    # use an index instead of scanning every row. The expression matches the
    # full_name hybrid: (first_name || ' ' || last_name).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX ix_students_full_name_trgm ON students "
        "USING gin ((first_name || ' ' || last_name) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_teachers_full_name_trgm ON teachers "
        "USING gin ((first_name || ' ' || last_name) gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_teachers_full_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_students_full_name_trgm")
    # The pg_trgm extension is left installed: other objects may rely on it and
    # dropping it is not something a schema downgrade should decide.
    op.drop_index("ix_contacts_person", table_name="contacts")
    op.drop_index("ix_disciplines_teacher_id", table_name="disciplines")
    op.drop_index("ix_grades_discipline_id", table_name="grades")
    op.drop_index("ix_grades_student_id", table_name="grades")
    op.drop_index("ix_students_group_id", table_name="students")
