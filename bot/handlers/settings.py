from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models.user import User
from bot.core.config import settings
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.services.distribution import DistributionService

router = Router()

class SettingsStates(StatesGroup):
    selecting_categories = State()
    selecting_cities = State()

def get_categories_keyboard(selected_categories=None):
    """Create inline keyboard with categories."""
    selected_categories = selected_categories or []
    builder = InlineKeyboardBuilder()
    
    for category in settings.CATEGORIES:
        status = "✅" if category in selected_categories else "⬜️"
        builder.button(
            text=f"{status} {category}",
            callback_data=f"category:{category}"
        )
    
    builder.button(text="✅ Готово", callback_data="categories:done")
    builder.adjust(1)
    return builder.as_markup()

def get_cities_keyboard(selected_cities=None):
    """Create inline keyboard with cities."""
    selected_cities = selected_cities or []
    builder = InlineKeyboardBuilder()
    
    for city in settings.CITIES:
        status = "✅" if city in selected_cities else "⬜️"
        builder.button(
            text=f"{status} {city}",
            callback_data=f"city:{city}"
        )
    
    builder.button(text="✅ Готово", callback_data="cities:done")
    builder.adjust(1)
    return builder.as_markup()

@router.message(F.text == "📋 Категории")
async def handle_categories(message: types.Message, state: FSMContext, session: AsyncSession):
    """Handle categories button."""
    query = select(User).where(User.telegram_id == message.from_user.id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации.")
        return
    
    await state.set_state(SettingsStates.selecting_categories)
    await state.update_data(selected_categories=user.categories or [])
    
    await message.answer(
        "📋 Выберите категории заявок:\n"
        "✅ - выбрано\n"
        "⬜️ - не выбрано",
        reply_markup=get_categories_keyboard(user.categories)
    )

@router.message(F.text == "🏢 Города")
async def handle_cities(message: types.Message, state: FSMContext, session: AsyncSession):
    """Handle cities button."""
    query = select(User).where(User.telegram_id == message.from_user.id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации.")
        return
    
    await state.set_state(SettingsStates.selecting_cities)
    await state.update_data(selected_cities=user.cities or [])
    
    await message.answer(
        "🏢 Выберите города:\n"
        "✅ - выбрано\n"
        "⬜️ - не выбрано",
        reply_markup=get_cities_keyboard(user.cities)
    )

@router.callback_query(lambda c: c.data.startswith("category:"))
async def process_category_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle category selection."""
    category = callback.data.split(":")[1]
    data = await state.get_data()
    selected_categories = data.get("selected_categories", [])
    
    if category in selected_categories:
        selected_categories.remove(category)
    else:
        selected_categories.append(category)
    
    await state.update_data(selected_categories=selected_categories)
    await callback.message.edit_reply_markup(
        reply_markup=get_categories_keyboard(selected_categories)
    )

@router.callback_query(lambda c: c.data.startswith("city:"))
async def process_city_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle city selection."""
    city = callback.data.split(":")[1]
    data = await state.get_data()
    selected_cities = data.get("selected_cities", [])
    
    if city in selected_cities:
        selected_cities.remove(city)
    else:
        selected_cities.append(city)
    
    await state.update_data(selected_cities=selected_cities)
    await callback.message.edit_reply_markup(
        reply_markup=get_cities_keyboard(selected_cities)
    )

@router.callback_query(lambda c: c.data == "categories:done")
async def process_categories_done(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle categories selection completion."""
    data = await state.get_data()
    selected_categories = data.get("selected_categories", [])
    
    query = select(User).where(User.telegram_id == callback.from_user.id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        user.categories = selected_categories
        await session.commit()
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ Выбранные категории:\n" + "\n".join(f"- {cat}" for cat in selected_categories)
    )

@router.callback_query(lambda c: c.data == "cities:done")
async def process_cities_done(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle cities selection completion."""
    data = await state.get_data()
    selected_cities = data.get("selected_cities", [])
    
    query = select(User).where(User.telegram_id == callback.from_user.id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        user.cities = selected_cities
        await session.commit()
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ Выбранные города:\n" + "\n".join(f"- {city}" for city in selected_cities)
    )

@router.message(F.text == "🎮 Демо режим")
async def handle_demo(message: types.Message, session: AsyncSession):
    """Handle demo mode button."""
    query = select(User).where(User.telegram_id == message.from_user.id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации.")
        return
    
    user.is_demo = not user.is_demo
    await session.commit()
    
    if user.is_demo:
        await message.answer(
            "✅ Демо-режим включен!\n\n"
            "Теперь вы будете получать тестовые заявки для ознакомления с работой бота.\n"
            "Для отключения демо-режима нажмите кнопку 🎮 Демо режим еще раз."
        )
        
        # Create and send demo lead
        distribution_service = DistributionService(session)
        demo_lead = await distribution_service.create_demo_lead()
        await distribution_service.distribute_lead(demo_lead, include_demo=True)
    else:
        await message.answer(
            "❌ Демо-режим отключен.\n\n"
            "Теперь вы будете получать только реальные заявки согласно вашим настройкам."
        ) 