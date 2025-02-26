"""add indexes for optimization

Revision ID: 49b2fbc00fe5
Revises: 49b2fbc00fe4
Create Date: 2024-02-26 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '49b2fbc00fe5'
down_revision = '49b2fbc00fe4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Индексы для таблицы users
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'])
    op.create_index('ix_users_is_active', 'users', ['is_active'])
    op.create_index('ix_users_last_lead_at', 'users', ['last_lead_at'])
    
    # Индексы для таблицы subscriptions
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_is_active', 'subscriptions', ['is_active'])
    op.create_index('ix_subscriptions_expires_at', 'subscriptions', ['expires_at'])
    op.create_index('ix_subscriptions_plan_name', 'subscriptions', ['plan_name'])
    
    # Индексы для таблицы leads
    op.create_index('ix_leads_category', 'leads', ['category'])
    op.create_index('ix_leads_city', 'leads', ['city'])
    op.create_index('ix_leads_created_at', 'leads', ['created_at'])
    op.create_index('ix_leads_status', 'leads', ['status'])
    
    # Индексы для таблицы lead_distributions
    op.create_index('ix_lead_distributions_lead_id', 'lead_distributions', ['lead_id'])
    op.create_index('ix_lead_distributions_user_id', 'lead_distributions', ['user_id'])
    op.create_index('ix_lead_distributions_sent_at', 'lead_distributions', ['sent_at'])
    
    # Индексы для таблицы payments
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])
    op.create_index('ix_payments_subscription_id', 'payments', ['subscription_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])
    op.create_index('ix_payments_created_at', 'payments', ['created_at'])


def downgrade() -> None:
    # Удаление индексов для таблицы users
    op.drop_index('ix_users_telegram_id')
    op.drop_index('ix_users_is_active')
    op.drop_index('ix_users_last_lead_at')
    
    # Удаление индексов для таблицы subscriptions
    op.drop_index('ix_subscriptions_user_id')
    op.drop_index('ix_subscriptions_is_active')
    op.drop_index('ix_subscriptions_expires_at')
    op.drop_index('ix_subscriptions_plan_name')
    
    # Удаление индексов для таблицы leads
    op.drop_index('ix_leads_category')
    op.drop_index('ix_leads_city')
    op.drop_index('ix_leads_created_at')
    op.drop_index('ix_leads_status')
    
    # Удаление индексов для таблицы lead_distributions
    op.drop_index('ix_lead_distributions_lead_id')
    op.drop_index('ix_lead_distributions_user_id')
    op.drop_index('ix_lead_distributions_sent_at')
    
    # Удаление индексов для таблицы payments
    op.drop_index('ix_payments_user_id')
    op.drop_index('ix_payments_subscription_id')
    op.drop_index('ix_payments_status')
    op.drop_index('ix_payments_created_at') 