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
from bot.services.demo_data import is_working_hours
import logging

router = Router()
logger = logging.getLogger(__name__)

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
        "⬜️ - не выбрано\n\n"
        "После выбора всех нужных категорий нажмите кнопку ✅ Готово",
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
        "⬜️ - не выбрано\n\n"
        "После выбора всех нужных городов нажмите кнопку ✅ Готово",
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
    try:
        data = await state.get_data()
        selected_categories = data.get("selected_categories", [])
        
        if not selected_categories:
            await callback.answer("❗️ Выберите хотя бы одну категорию", show_alert=True)
            return
        
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            # Сохраняем предыдущие настройки для сравнения
            old_categories = user.categories
            
            # Обновляем категории
            user.categories = selected_categories
            await session.commit()
            await state.clear()
            
            # Формируем текст с изменениями
            changes_text = ""
            if old_categories:
                added = set(selected_categories) - set(old_categories)
                removed = set(old_categories) - set(selected_categories)
                if added:
                    changes_text += "\n➕ Добавлены: " + ", ".join(added)
                if removed:
                    changes_text += "\n➖ Удалены: " + ", ".join(removed)
            
            # Отправляем сообщение с обновленными настройками
            settings_text = (
                "✅ Категории успешно обновлены!" + changes_text + "\n\n"
                "📋 Ваши текущие настройки:\n"
                f"Категории: {', '.join(user.categories)}\n"
                f"Города: {', '.join(user.cities) if user.cities else 'не выбраны'}\n"
                f"Демо режим: {'включен' if user.is_demo else 'выключен'}"
            )
            
            await callback.message.edit_text(settings_text)
            
            # Если включен демо-режим, отправляем уведомление
            if user.is_demo and is_working_hours():
                distribution_service = DistributionService(session)
                demo_lead = await distribution_service.create_demo_lead()
                if demo_lead:
                    distribution = await distribution_service.create_distribution(
                        lead_id=demo_lead.id,
                        user_id=user.id
                    )
                    if distribution:
                        lead_text = distribution_service.format_lead_for_user(demo_lead, user)
                        await callback.message.answer(
                            "📨 Новая демо-заявка по обновленным настройкам:\n\n" + lead_text
                        )
            
    except Exception as e:
        logger.error(f"Error saving categories: {str(e)}", exc_info=True)
        await session.rollback()
        await callback.answer("❌ Ошибка при сохранении категорий", show_alert=True)

@router.callback_query(lambda c: c.data == "cities:done")
async def process_cities_done(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle cities selection completion."""
    try:
        data = await state.get_data()
        selected_cities = data.get("selected_cities", [])
        
        if not selected_cities:
            await callback.answer("❗️ Выберите хотя бы один город", show_alert=True)
            return
        
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            # Сохраняем предыдущие настройки для сравнения
            old_cities = user.cities
            
            # Обновляем города
            user.cities = selected_cities
            await session.commit()
            await state.clear()
            
            # Формируем текст с изменениями
            changes_text = ""
            if old_cities:
                added = set(selected_cities) - set(old_cities)
                removed = set(old_cities) - set(selected_cities)
                if added:
                    changes_text += "\n➕ Добавлены: " + ", ".join(added)
                if removed:
                    changes_text += "\n➖ Удалены: " + ", ".join(removed)
            
            # Отправляем сообщение с обновленными настройками
            settings_text = (
                "✅ Города успешно обновлены!" + changes_text + "\n\n"
                "📋 Ваши текущие настройки:\n"
                f"Категории: {', '.join(user.categories) if user.categories else 'не выбраны'}\n"
                f"Города: {', '.join(user.cities)}\n"
                f"Демо режим: {'включен' if user.is_demo else 'выключен'}"
            )
            
            await callback.message.edit_text(settings_text)
            
            # Если включен демо-режим, отправляем уведомление
            if user.is_demo and is_working_hours():
                distribution_service = DistributionService(session)
                demo_lead = await distribution_service.create_demo_lead()
                if demo_lead:
                    distribution = await distribution_service.create_distribution(
                        lead_id=demo_lead.id,
                        user_id=user.id
                    )
                    if distribution:
                        lead_text = distribution_service.format_lead_for_user(demo_lead, user)
                        await callback.message.answer(
                            "📨 Новая демо-заявка по обновленным настройкам:\n\n" + lead_text
                        )
            
    except Exception as e:
        logger.error(f"Error saving cities: {str(e)}", exc_info=True)
        await session.rollback()
        await callback.answer("❌ Ошибка при сохранении городов", show_alert=True)

@router.message(F.text == "🎮 Демо режим")
async def handle_demo(message: types.Message, session: AsyncSession):
    """Handle demo mode button."""
    try:
        query = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации.")
            return
        
        # Проверяем наличие категорий и городов
        if not user.categories or not user.cities:
            await message.answer(
                "❗️ Для активации демо-режима необходимо выбрать категории и города:\n\n"
                f"Категории: {', '.join(user.categories) if user.categories else '❌ не выбраны'}\n"
                f"Города: {', '.join(user.cities) if user.cities else '❌ не выбраны'}\n\n"
                "Пожалуйста, выберите категории и города в соответствующих разделах меню."
            )
            return
        
        # Переключаем режим
        user.is_demo = not user.is_demo
        await session.commit()
        
        if user.is_demo:
            # Проверяем рабочее время
            if not is_working_hours():
                await message.answer(
                    "ℹ️ Демо-режим активирован, но сейчас нерабочее время (9:00-21:00).\n"
                    "Вы начнете получать демо-заявки в рабочее время."
                )
                return
                
            # Создаем и отправляем первую демо-заявку
            distribution_service = DistributionService(session)
            demo_lead = await distribution_service.create_demo_lead()
            
            if demo_lead:
                # Создаем распределение для демо-заявки
                distribution = await distribution_service.create_distribution(
                    lead_id=demo_lead.id,
                    user_id=user.id
                )
                
                if distribution:
                    lead_text = distribution_service.format_lead_for_user(demo_lead, user)
                    await message.answer(
                        "✅ Демо-режим активирован!\n\n"
                        "Вот ваша первая демо-заявка:\n\n" + lead_text + "\n\n"
                        "Вы будете получать до 5 демо-заявок в день в рабочее время (9:00-21:00).\n"
                        "Для отключения демо-режима нажмите кнопку еще раз."
                    )
                else:
                    await message.answer(
                        "✅ Демо-режим активирован!\n\n"
                        "Вы будете получать до 5 демо-заявок в день в рабочее время (9:00-21:00).\n"
                        "Первая заявка придет в ближайшее время."
                    )
            else:
                await message.answer(
                    "✅ Демо-режим активирован!\n\n"
                    "Вы будете получать до 5 демо-заявок в день в рабочее время (9:00-21:00).\n"
                    "Первая заявка придет в ближайшее время."
                )
        else:
            await message.answer(
                "❌ Демо-режим отключен.\n"
                "Вы больше не будете получать тестовые заявки."
            )
            
    except Exception as e:
        logger.error(f"Error in demo mode: {str(e)}", exc_info=True)
        await session.rollback()
        await message.answer(
            "❌ Произошла ошибка при обработке демо-режима.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        ) 