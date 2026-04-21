"""add rides.target_coordinates (score contract fix)

Revision ID: c3d4e5f6a1b2
Revises: a1b2c3d4e5f6
Create Date: 2026-04-21 05:45:00.000000

Adds rides.target_coordinates (JSON, NOT NULL): server-computed stencil result
stored at ride-start time. Scoring now compares actual path against
ride.target_coordinates instead of blueprint.coordinates so transforms
(rotation/scale/translate) are honoured.

데이터 마이그레이션용 backfill (NOT a runtime fallback):
Existing rows get target_coordinates = blueprint.coordinates (identity stencil)
purely so the NOT NULL constraint can be applied without losing data. This is a
one-shot migration step. At runtime, scores.py must NOT fall back to
blueprint.coordinates — it only reads ride.target_coordinates. The runtime
"no-target" path is handled earlier in start_ride (rides.py), which copies
blueprint.coordinates into ride.target_coordinates when the client omits both
target_lat and target_lng.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c3d4e5f6a1b2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add column as nullable so existing rows don't break on the ALTER.
    op.add_column(
        "rides",
        sa.Column("target_coordinates", sa.JSON(), nullable=True),
    )

    # 2. Backfill existing rows with blueprint.coordinates (identity stencil).
    bind = op.get_bind()
    rides = sa.table(
        "rides",
        sa.column("id", sa.Integer),
        sa.column("blueprint_id", sa.Integer),
        sa.column("target_coordinates", sa.JSON),
    )
    blueprints = sa.table(
        "blueprints",
        sa.column("id", sa.Integer),
        sa.column("coordinates", sa.JSON),
    )

    existing = bind.execute(
        sa.select(rides.c.id, blueprints.c.coordinates).select_from(
            rides.join(blueprints, rides.c.blueprint_id == blueprints.c.id)
        )
    ).fetchall()
    for ride_id, coords in existing:
        bind.execute(
            rides.update()
            .where(rides.c.id == ride_id)
            .values(target_coordinates=coords)
        )

    # 3. Tighten to NOT NULL (batch mode for SQLite compat).
    with op.batch_alter_table("rides") as batch_op:
        batch_op.alter_column("target_coordinates", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("rides") as batch_op:
        batch_op.drop_column("target_coordinates")
