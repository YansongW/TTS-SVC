from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '1a2b3c4d5e6f'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 创建batch_task表
    op.create_table(
        'batch_task',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), default='Pending'),
        sa.Column('progress', sa.Integer(), default=0),
        sa.Column('total_tasks', sa.Integer(), default=0),
        sa.Column('completed_tasks', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建task表
    op.create_table(
        'task',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('pitch', sa.Float(), default=1.0),
        sa.Column('speed', sa.Float(), default=1.0),
        sa.Column('melody', sa.String(50), default='default'),
        sa.Column('status', sa.String(20), default='Pending'),
        sa.Column('error_message', sa.Text()),
        sa.Column('tts_output', sa.String(200)),
        sa.Column('svc_output', sa.String(200)),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('batch_id', sa.Integer(), sa.ForeignKey('batch_task.id')),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('task')
    op.drop_table('batch_task')
