from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.core.config import settings
from bot.models.user import User
from bot.models.lead import Lead, LeadDistribution
from bot.models.settings import BotSettings
from datetime import datetime, timedelta
from aiogram.utils.keyboard import InlineKeyboardBuilder
import json

router = Router()

class AdminSettingsStates(StatesGroup):
    editing_setting = State()

def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in settings.admin_ids_list

def get_admin_keyboard() -> types.InlineKeyboardMarkup:
    """Create admin keyboard markup."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.button(text="👥 Пользователи", callback_data="admin:users")
    builder.button(text="⚙️ Настройки", callback_data="admin:settings")
    builder.adjust(1)
    return builder.as_markup()

def get_settings_keyboard() -> types.InlineKeyboardMarkup:
    """Create settings keyboard markup."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Категории", callback_data="settings:categories")
    builder.button(text="🏢 Города", callback_data="settings:cities")
    builder.button(text="⏱ Интервал", callback_data="settings:interval")
    builder.button(text="👥 Макс. получателей", callback_data="settings:max_recipients")
    builder.button(text="🔙 Назад", callback_data="admin:back")
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
    
    # Получаем статистику за последние 24 часа и за все время
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    
    # Общее количество пользователей
    total_users = await session.scalar(select(func.count(User.id)))
    active_users = await session.scalar(select(func.count(User.id)).where(User.is_active == True))
    paid_users = await session.scalar(select(func.count(User.id)).where(User.is_paid == True))
    
    # Статистика по заявкам
    total_leads = await session.scalar(select(func.count(Lead.id)))
    today_leads = await session.scalar(
        select(func.count(Lead.id))
        .where(Lead.created_at >= day_ago)
    )
    
    # Статистика по распределениям
    total_distributions = await session.scalar(select(func.count(LeadDistribution.id)))
    today_distributions = await session.scalar(
        select(func.count(LeadDistribution.id))
        .where(LeadDistribution.sent_at >= day_ago)
    )
    
    # Статистика по категориям
    category_stats = await session.execute(
        select(Lead.category, func.count(Lead.id))
        .group_by(Lead.category)
    )
    category_stats = category_stats.all()
    
    # Статистика по городам
    city_stats = await session.execute(
        select(Lead.city, func.count(Lead.id))
        .group_by(Lead.city)
    )
    city_stats = city_stats.all()
    
    # Формируем текст статистики
    stats_text = (
        "📊 Статистика бота\n\n"
        f"👥 Пользователи:\n"
        f"- Всего: {total_users}\n"
        f"- Активных: {active_users}\n"
        f"- С оплатой: {paid_users}\n\n"
        f"📝 Заявки:\n"
        f"- Всего: {total_leads}\n"
        f"- За 24 часа: {today_leads}\n"
        f"- Распределений: {total_distributions}\n"
        f"- Распределений за 24ч: {today_distributions}\n\n"
        f"📋 По категориям:\n"
    )
    
    for category, count in category_stats:
        stats_text += f"- {category}: {count}\n"
    
    stats_text += "\n🏢 По городам:\n"
    for city, count in city_stats:
        stats_text += f"- {city}: {count}\n"
    
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
async def handle_admin_settings(callback: types.CallbackQuery, session: AsyncSession):
    """Handle admin settings button."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    # Получаем текущие настройки из базы
    settings_text = (
        "⚙️ Настройки бота:\n\n"
        f"📊 Интервал распределения: {settings.DISTRIBUTION_INTERVAL} часа\n"
        f"👥 Максимум получателей: {settings.MAX_RECIPIENTS}\n\n"
        "📋 Доступные категории:\n" + "\n".join(f"- {cat}" for cat in settings.CATEGORIES) + "\n\n"
        "🏢 Доступные города:\n" + "\n".join(f"- {city}" for city in settings.CITIES) + "\n\n"
        "Выберите настройку для редактирования:"
    )
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=get_settings_keyboard()
    )

@router.callback_query(lambda c: c.data.startswith("settings:"))
async def handle_setting_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle setting selection."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    setting = callback.data.split(":")[1]
    
    if setting == "interval":
        await state.set_state(AdminSettingsStates.editing_setting)
        await state.update_data(setting="DISTRIBUTION_INTERVAL")
        await callback.message.edit_text(
            "⏱ Введите новый интервал распределения (в часах):",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="🔙 Отмена", callback_data="admin:settings")
            ]])
        )
    elif setting == "max_recipients":
        await state.set_state(AdminSettingsStates.editing_setting)
        await state.update_data(setting="MAX_RECIPIENTS")
        await callback.message.edit_text(
            "👥 Введите максимальное количество получателей одной заявки:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="🔙 Отмена", callback_data="admin:settings")
            ]])
        )
    elif setting == "categories":
        # Показываем текущие категории с возможностью редактирования
        categories_text = (
            "📋 Текущие категории:\n\n" +
            "\n".join(f"- {cat}" for cat in settings.CATEGORIES) +
            "\n\nДля добавления категории отправьте её название."
        )
        await state.set_state(AdminSettingsStates.editing_setting)
        await state.update_data(setting="CATEGORIES")
        await callback.message.edit_text(
            categories_text,
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="🔙 Отмена", callback_data="admin:settings")
            ]])
        )
    elif setting == "cities":
        # Показываем текущие города с возможностью редактирования
        cities_text = (
            "🏢 Текущие города:\n\n" +
            "\n".join(f"- {city}" for city in settings.CITIES) +
            "\n\nДля добавления города отправьте его название."
        )
        await state.set_state(AdminSettingsStates.editing_setting)
        await state.update_data(setting="CITIES")
        await callback.message.edit_text(
            cities_text,
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="🔙 Отмена", callback_data="admin:settings")
            ]])
        )

@router.message(AdminSettingsStates.editing_setting)
async def process_setting_edit(message: types.Message, state: FSMContext, session: AsyncSession):
    """Process setting edit."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой функции.")
        return
    
    data = await state.get_data()
    setting_key = data.get("setting")
    
    if not setting_key:
        await state.clear()
        await message.answer("❌ Ошибка: настройка не выбрана")
        return
    
    try:
        if setting_key in ["DISTRIBUTION_INTERVAL", "MAX_RECIPIENTS"]:
            value = int(message.text)
            if value <= 0:
                raise ValueError("Значение должно быть положительным")
        elif setting_key in ["CATEGORIES", "CITIES"]:
            # Получаем текущий список
            query = select(BotSettings).where(BotSettings.key == setting_key)
            result = await session.execute(query)
            setting = result.scalar_one_or_none()
            
            if setting:
                current_list = setting.value
            else:
                current_list = getattr(settings, setting_key, [])
            
            # Добавляем новое значение
            if message.text not in current_list:
                current_list.append(message.text)
            value = current_list
        
        # Сохраняем настройку в базе
        query = select(BotSettings).where(BotSettings.key == setting_key)
        result = await session.execute(query)
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.value = value
        else:
            setting = BotSettings(
                key=setting_key,
                value=value,
                description=f"Setting for {setting_key}"
            )
            session.add(setting)
        
        await session.commit()
        
        # Обновляем значение в settings
        setattr(settings, setting_key, value)
        
        await message.answer(
            f"✅ Настройка {setting_key} успешно обновлена!",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
        
    except ValueError as e:
        await message.answer(
            f"❌ Ошибка: {str(e)}. Попробуйте еще раз или нажмите отмену.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="🔙 Отмена", callback_data="admin:settings")
            ]])
        )

@router.callback_query(lambda c: c.data == "admin:back")
async def handle_admin_back(callback: types.CallbackQuery):
    """Handle back button in admin panel."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к этой функции.", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔧 Админ-панель\n\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    ) 