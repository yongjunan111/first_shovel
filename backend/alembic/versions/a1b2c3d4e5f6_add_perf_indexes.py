"""add performance indexes + GiST placeholder

Revision ID: a1b2c3d4e5f6
Revises: 95d744d33874
Create Date: 2026-04-09 00:00:00.000000

Adds:
  - rides(user_id), rides(blueprint_id)      — for "my rides" and per-blueprint queries
  - scores(blueprint_id), scores(user_id)    — for ranking and user history
  - GiST index on blueprints.coordinates     — PostgreSQL/PostGIS only
    (no-op on SQLite; activate once column is migrated to GEOMETRY)
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy.engine import reflection


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '95d744d33874'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    # Standard B-tree indexes — work on both SQLite and PostgreSQL
    op.create_index('ix_rides_user_id', 'rides', ['user_id'])
    op.create_index('ix_rides_blueprint_id', 'rides', ['blueprint_id'])
    op.create_index('ix_scores_blueprint_id', 'scores', ['blueprint_id'])
    op.create_index('ix_scores_user_id', 'scores', ['user_id'])
    op.create_index('ix_blueprints_user_id', 'blueprints', ['user_id'])
    op.create_index('ix_blueprints_difficulty', 'blueprints', ['difficulty'])

    # GiST spatial index — PostgreSQL/PostGIS only
    # When coordinates column is migrated to GEOMETRY(LineString, 4326),
    # this index enables fast bounding-box and spatial queries.
    if _is_postgresql():
        op.execute(
            "CREATE INDEX ix_blueprints_coordinates_gist "
            "ON blueprints USING GIST (coordinates);"
        )


def downgrade() -> None:
    if _is_postgresql():
        op.execute("DROP INDEX IF EXISTS ix_blueprints_coordinates_gist;")

    op.drop_index('ix_blueprints_difficulty', table_name='blueprints')
    op.drop_index('ix_blueprints_user_id', table_name='blueprints')
    op.drop_index('ix_scores_user_id', table_name='scores')
    op.drop_index('ix_scores_blueprint_id', table_name='scores')
    op.drop_index('ix_rides_blueprint_id', table_name='rides')
    op.drop_index('ix_rides_user_id', table_name='rides')
