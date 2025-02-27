from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.core.config import settings
from bot.models.user import User
from bot.models.lead import Lead, LeadDistribution
from datetime import datetime, timedelta
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in settings.ADMIN_IDS

def get_admin_keyboard() -> types.InlineKeyboardMarkup:
    """Create admin keyboard markup."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.button(text="👥 Пользователи", callback_data="admin:users")
    builder.button(text="⚙️ Настройки", callback_data="admin:settings")
    builder.adjust(1)
    return builder.as_markup()

@router.message(F.text == "👑 Админ панель")
async def handle_admin(message: types.Message):
    """Handle admin panel button."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    await message.answer(
        "🔧 Админ-панель\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )

@router.callback_query(lambda c: c.data == "admin:stats")
async def handle_admin_stats(callback: types.CallbackQuery, session: AsyncSession):
    """Handle admin stats button."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    # Get total leads count
    total_leads = await session.scalar(select(func.count(Lead.id)))
    
    # Get leads count by status
    leads_by_status = {}
    for status in settings.LEAD_STATUSES:
        count = await session.scalar(
            select(func.count(Lead.id)).where(Lead.status == status)
        )
        leads_by_status[status] = count
    
    # Get leads count for last 24 hours
    last_24h = await session.scalar(
        select(func.count(Lead.id)).where(
            Lead.created_at >= datetime.utcnow() - timedelta(days=1)
        )
    )
    
    # Get total users count
    total_users = await session.scalar(select(func.count(User.id)))
    
    stats_text = (
        "📊 Статистика:\n\n"
        f"📝 Всего заявок: {total_leads}\n"
        f"🕒 За последние 24 часа: {last_24h}\n"
        f"👥 Всего пользователей: {total_users}\n\n"
        "📋 По статусам:\n"
    )
    
    for status, count in leads_by_status.items():
        status_name = settings.LEAD_STATUSES[status]
        stats_text += f"- {status_name}: {count}\n"
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_keyboard()
    )

@router.callback_query(lambda c: c.data == "admin:users")
async def handle_admin_users(callback: types.CallbackQuery, session: AsyncSession):
    """Handle admin users button."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    # Get all users with their leads count
    users = await session.execute(
        select(User, func.count(LeadDistribution.id))
        .outerjoin(LeadDistribution)
        .group_by(User.id)
    )
    users = users.all()
    
    if not users:
        await callback.message.edit_text(
            "👥 Пользователей пока нет.",
            reply_markup=get_admin_keyboard()
        )
        return
    
    users_text = "👥 Список пользователей:\n\n"
    for user, leads_count in users:
        status = "✅ активен" if user.is_active else "❌ не активен"
        users_text += (
            f"ID: {user.telegram_id}\n"
            f"Имя: {user.full_name or 'не указано'}\n"
            f"Username: {user.username or 'не указан'}\n"
            f"Статус: {status}\n"
            f"Категории: {', '.join(user.categories) if user.categories else 'не выбраны'}\n"
            f"Города: {', '.join(user.cities) if user.cities else 'не выбраны'}\n"
            f"Получено заявок: {leads_count}\n"
            "-------------------\n"
        )
    
    # Split message if it's too long
    if len(users_text) > 4096:
        parts = [users_text[i:i+4096] for i in range(0, len(users_text), 4096)]
        for i, part in enumerate(parts):
            if i == 0:
                await callback.message.edit_text(
                    part,
                    reply_markup=get_admin_keyboard()
                )
            else:
                await callback.message.answer(part)
    else:
        await callback.message.edit_text(
            users_text,
            reply_markup=get_admin_keyboard()
        )

@router.callback_query(lambda c: c.data == "admin:settings")
async def handle_admin_settings(callback: types.CallbackQuery):
    """Handle admin settings button."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    settings_text = (
        "⚙️ Настройки бота:\n\n"
        f"📊 Интервал распределения: {settings.DISTRIBUTION_INTERVAL} часа\n"
        f"👥 Максимум получателей: {settings.MAX_RECIPIENTS}\n\n"
        "📋 Доступные категории:\n" + "\n".join(f"- {cat}" for cat in settings.CATEGORIES) + "\n\n"
        "🏢 Доступные города:\n" + "\n".join(f"- {city}" for city in settings.CITIES)
    )
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=get_admin_keyboard()
    ) 