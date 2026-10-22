"""sprint 4: report jobs, model management, knowledge base, embeddings, suggestion events

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-22 18:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

# SQLite reflects the 0001 unique constraint on model_registry.version without a name.
NAMING = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def _old_version_constraint() -> str:
    return "model_registry_version_key" if op.get_bind().dialect.name == "postgresql" else "uq_model_registry_version"


def upgrade() -> None:
    op.create_table('training_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('trigger', sa.String(length=10), nullable=False),
    sa.Column('force', sa.Boolean(), nullable=False),
    sa.Column('requested_by', sa.Integer(), nullable=True),
    sa.Column('feedback_count', sa.Integer(), nullable=False),
    sa.Column('logs', sa.Text(), nullable=False),
    sa.Column('result', sa.JSON(), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )

    with op.batch_alter_table('model_registry', schema=None, naming_convention=NAMING) as batch_op:
        batch_op.drop_constraint(_old_version_constraint(), type_='unique')
        batch_op.add_column(sa.Column('model_type', sa.String(length=20), nullable=False, server_default='classifier'))
        batch_op.add_column(sa.Column('train_size', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('feedback_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('status', sa.String(length=12), nullable=False, server_default='candidate'))
        batch_op.add_column(sa.Column('artifact_path', sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column('training_run_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('activated_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('activated_at', sa.DateTime(), nullable=True))
        batch_op.create_unique_constraint('uq_model_registry_type_version', ['model_type', 'version'])
        batch_op.create_foreign_key('fk_model_registry_training_run', 'training_runs', ['training_run_id'], ['id'],
                                    ondelete='SET NULL')
        batch_op.create_foreign_key('fk_model_registry_activated_by', 'users', ['activated_by'], ['id'],
                                    ondelete='SET NULL')
    op.execute("UPDATE model_registry SET status = 'active' WHERE is_active")
    op.execute("UPDATE model_registry SET status = 'archived' WHERE NOT is_active")

    with op.batch_alter_table('requests', schema=None) as batch_op:
        batch_op.add_column(sa.Column('suggestions_shown', sa.JSON(), nullable=True))

    op.create_table('report_jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=8), nullable=False),
    sa.Column('filters', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('file_key', sa.String(length=200), nullable=True),
    sa.Column('file_size', sa.Integer(), nullable=True),
    sa.Column('row_count', sa.Integer(), nullable=True),
    sa.Column('requested_by', sa.Integer(), nullable=False),
    sa.Column('unit_scope', sa.Integer(), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['unit_scope'], ['units.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('report_jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_report_jobs_requested_by'), ['requested_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_report_jobs_created_at'), ['created_at'], unique=False)

    op.create_table('faq_articles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=80), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('unit_id', sa.Integer(), nullable=True),
    sa.Column('language', sa.String(length=2), nullable=False),
    sa.Column('tags', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('views', sa.Integer(), nullable=False),
    sa.Column('helpful_yes', sa.Integer(), nullable=False),
    sa.Column('helpful_no', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('approved_by', sa.Integer(), nullable=True),
    sa.Column('source_request_id', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('published_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['source_request_id'], ['requests.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('faq_articles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_faq_articles_slug'), ['slug'], unique=False)
        batch_op.create_index(batch_op.f('ix_faq_articles_category_id'), ['category_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_faq_articles_unit_id'), ['unit_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_faq_articles_status'), ['status'], unique=False)

    op.create_table('faq_article_versions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('article_id', sa.Integer(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('language', sa.String(length=2), nullable=False),
    sa.Column('tags', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('editor_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['article_id'], ['faq_articles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['editor_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('faq_article_versions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_faq_article_versions_article_id'), ['article_id'], unique=False)

    op.create_table('reply_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('unit_id', sa.Integer(), nullable=True),
    sa.Column('language', sa.String(length=2), nullable=False),
    sa.Column('usage_count', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('reply_templates', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reply_templates_category_id'), ['category_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_reply_templates_unit_id'), ['unit_id'], unique=False)

    op.create_table('content_embeddings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('entity_type', sa.String(length=10), nullable=False),
    sa.Column('entity_id', sa.String(length=20), nullable=False),
    sa.Column('language', sa.String(length=2), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('unit_id', sa.Integer(), nullable=True),
    sa.Column('provider', sa.String(length=80), nullable=False),
    sa.Column('dim', sa.Integer(), nullable=False),
    sa.Column('vector', sa.LargeBinary(), nullable=False),
    sa.Column('text_hash', sa.String(length=40), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('entity_type', 'entity_id', name='uq_embedding_entity')
    )
    with op.batch_alter_table('content_embeddings', schema=None) as batch_op:
        batch_op.create_index('ix_embedding_lookup', ['entity_type', 'language'], unique=False)

    op.create_table('suggestion_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('request_id', sa.String(length=20), nullable=True),
    sa.Column('session_id', sa.String(length=40), nullable=True),
    sa.Column('type', sa.String(length=12), nullable=False),
    sa.Column('item_id', sa.String(length=40), nullable=False),
    sa.Column('action', sa.String(length=10), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('unit_id', sa.Integer(), nullable=True),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('suggestion_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_suggestion_events_request_id'), ['request_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_suggestion_events_session_id'), ['session_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_suggestion_events_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_suggestion_events_unit_id'), ['unit_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_suggestion_events_created_at'), ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('suggestion_events')
    op.drop_table('content_embeddings')
    op.drop_table('reply_templates')
    op.drop_table('faq_article_versions')
    op.drop_table('faq_articles')
    op.drop_table('report_jobs')
    with op.batch_alter_table('requests', schema=None) as batch_op:
        batch_op.drop_column('suggestions_shown')
    # Only one row per version can survive the old unique(version) constraint.
    op.execute("DELETE FROM model_registry WHERE model_type <> 'classifier'")
    with op.batch_alter_table('model_registry', schema=None) as batch_op:
        batch_op.drop_constraint('fk_model_registry_activated_by', type_='foreignkey')
        batch_op.drop_constraint('fk_model_registry_training_run', type_='foreignkey')
        batch_op.drop_constraint('uq_model_registry_type_version', type_='unique')
        batch_op.drop_column('activated_at')
        batch_op.drop_column('activated_by')
        batch_op.drop_column('training_run_id')
        batch_op.drop_column('artifact_path')
        batch_op.drop_column('status')
        batch_op.drop_column('feedback_count')
        batch_op.drop_column('train_size')
        batch_op.drop_column('model_type')
        batch_op.create_unique_constraint(_old_version_constraint(), ['version'])
    op.drop_table('training_runs')
