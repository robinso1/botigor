from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.user import User
from bot.core.config import settings
from bot.services.distribution import DistributionService
from bot.services.parser import LeadParser
from bot.models.lead import Lead
import logging

router = Router()
lead_parser = LeadParser()
logger = logging.getLogger(__name__)

def get_main_keyboard(is_admin: bool = False) -> types.ReplyKeyboardMarkup:
    """Create main keyboard markup."""
    buttons = [
        [
            types.KeyboardButton(text="📋 Категории"),
            types.KeyboardButton(text="🏢 Города")
        ],
        [
            types.KeyboardButton(text="📊 Мои настройки"),
            types.KeyboardButton(text="🎮 Демо режим")
        ],
        [
            types.KeyboardButton(text="ℹ️ Помощь")
        ]
    ]
    
    if is_admin:
        buttons.append([types.KeyboardButton(text="👑 Админ панель")])
    
    return types.ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

@router.message(Command("start"))
async def cmd_start(message: types.Message, session: AsyncSession):
    """Handle /start command."""
    logger.info(f"Processing /start command for user {message.from_user.id}")
    
    try:
        # Check if user exists
        query = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        logger.info(f"User query result: {user}")
        is_admin = message.from_user.id in settings.ADMIN_IDS
        
        if not user:
            logger.info(f"Creating new user: {message.from_user.id}")
            # Create new user
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
                categories=[],
                cities=[],
                is_active=True,
                is_demo=False
            )
            session.add(user)
            await session.flush()
            logger.info(f"New user created: {user.telegram_id}")
            
            welcome_text = (
                "👋 Добро пожаловать в систему распределения заявок!\n\n"
                "Для начала работы вам нужно:\n"
                "1. Выбрать категории заявок\n"
                "2. Выбрать города\n\n"
                "После этого вы начнете получать заявки согласно вашим настройкам.\n\n"
                "Используйте кнопки меню ниже для управления настройками."
            )
        else:
            logger.info(f"User already exists: {user.telegram_id}")
            welcome_text = (
                "👋 С возвращением!\n\n"
                "Ваши текущие настройки:\n"
                f"📋 Категории: {', '.join(user.categories) if user.categories else 'не выбраны'}\n"
                f"🏢 Города: {', '.join(user.cities) if user.cities else 'не выбраны'}\n\n"
                "Используйте кнопки меню для управления настройками."
            )
        
        # Always show keyboard
        keyboard = get_main_keyboard(is_admin)
        logger.info(f"Sending welcome message to user {message.from_user.id}")
        await message.answer(welcome_text, reply_markup=keyboard)
        await session.commit()
        logger.info(f"Start command completed successfully for user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error in start command for user {message.from_user.id}: {str(e)}", exc_info=True)
        await session.rollback()
        await message.answer(
            "❌ Произошла ошибка при обработке команды.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
        # Notify admins about the error
        for admin_id in settings.ADMIN_IDS:
            try:
                await message.bot.send_message(
                    admin_id,
                    f"❌ Ошибка при обработке команды /start:\n"
                    f"Пользователь: {message.from_user.id}\n"
                    f"Ошибка: {str(e)}"
                )
            except Exception as notify_error:
                logger.error(f"Failed to notify admin {admin_id}: {str(notify_error)}")

@router.message(F.text == "ℹ️ Помощь")
async def handle_help(message: types.Message):
    """Handle help button."""
    help_text = (
        "🔍 Доступные команды:\n\n"
        "📋 Категории - выбор категорий заявок\n"
        "🏢 Города - выбор городов\n"
        "📊 Мои настройки - текущие настройки\n"
        "🎮 Демо режим - включить/выключить тестовые заявки\n"
        "ℹ️ Помощь - справка\n\n"
        "ℹ️ Демо-режим позволяет получать тестовые заявки для ознакомления с работой бота.\n\n"
        "По всем вопросам обращайтесь к администратору."
    )
    await message.answer(help_text)

@router.message(F.text == "📊 Мои настройки")
async def handle_status(message: types.Message, session: AsyncSession):
    """Handle status button."""
    query = select(User).where(User.telegram_id == message.from_user.id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации.")
        return
    
    status_text = (
        "📊 Ваши текущие настройки:\n\n"
        f"👤 ID: {user.telegram_id}\n"
        f"📋 Категории: {', '.join(user.categories) if user.categories else 'не выбраны'}\n"
        f"🏢 Города: {', '.join(user.cities) if user.cities else 'не выбраны'}\n"
        f"📱 Статус: {'активен' if user.is_active else 'не активен'}\n"
        f"🎮 Демо режим: {'включен' if user.is_demo else 'выключен'}"
    )
    await message.answer(status_text)

@router.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_group_message(message: types.Message, session: AsyncSession):
    """Handle messages in groups to parse leads."""
    try:
        # Parse lead data from message
        lead_data = await lead_parser.parse_message(message)
        if not lead_data:
            logger.info(f"Message {message.message_id} in chat {message.chat.id} was not recognized as a lead")
            return

        # Create lead and distribute it
        lead = Lead(**lead_data)
        session.add(lead)
        await session.commit()
        
        # Distribute lead
        distribution_service = DistributionService(session)
        distributions = await distribution_service.distribute_lead(lead)
        
        if not distributions:
            logger.warning(f"No eligible users found for lead {lead.id}")
        else:
            logger.info(f"Lead {lead.id} distributed to {len(distributions)} users")
            
    except Exception as e:
        logger.error(f"Error processing message {message.message_id} in chat {message.chat.id}: {str(e)}")
        # Можно также отправить уведомление администраторам
        for admin_id in settings.ADMIN_IDS:
            try:
                await message.bot.send_message(
                    admin_id,
                    f"❌ Ошибка при обработке заявки:\n"
                    f"Чат: {message.chat.title} ({message.chat.id})\n"
                    f"Сообщение ID: {message.message_id}\n"
                    f"Ошибка: {str(e)}"
                )
            except Exception as notify_error:
                logger.error(f"Failed to notify admin {admin_id}: {str(notify_error)}")

@router.message(F.chat.type == "private")
async def handle_private_message(message: types.Message):
    """Handle messages in private chat."""
    # Пропускаем сообщения, которые уже обработаны другими хендлерами
    if message.text in [
        "📋 Категории", "🏢 Города", "📊 Мои настройки",
        "🎮 Демо режим", "ℹ️ Помощь", "👑 Админ панель"
    ]:
        return
        
    await message.answer(
        "👋 Используйте кнопки меню для управления настройками:",
        reply_markup=get_main_keyboard(message.from_user.id in settings.ADMIN_IDS)
    ) 