from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models.user import User
from bot.services.subscription import SubscriptionService
from bot.services.payment import PaymentService
from aiogram.utils.keyboard import InlineKeyboardBuilder
import json
import logging

router = Router()
logger = logging.getLogger(__name__)

class SubscriptionStates(StatesGroup):
    selecting_plan = State()
    confirming_payment = State()

def get_subscription_keyboard() -> types.InlineKeyboardMarkup:
    """Create subscription keyboard markup."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Тарифы", callback_data="subscription:plans")
    builder.button(text="📊 Моя подписка", callback_data="subscription:status")
    builder.adjust(1)
    return builder.as_markup()

def get_plans_keyboard() -> types.InlineKeyboardMarkup:
    """Create plans keyboard markup."""
    builder = InlineKeyboardBuilder()
    
    for plan_id, plan in settings.SUBSCRIPTION_PLANS.items():
        builder.button(
            text=f"{plan['name']} - {plan['price']}₽",
            callback_data=f"plan:{plan_id}"
        )
    
    builder.button(text="🔙 Назад", callback_data="subscription:back")
    builder.adjust(1)
    return builder.as_markup()

@router.message(F.text == "💳 Подписка")
async def handle_subscription(message: types.Message, session: AsyncSession):
    """Handle subscription button."""
    query = select(User).where(User.telegram_id == message.from_user.id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации.")
        return
    
    subscription_service = SubscriptionService(session)
    subscription = await subscription_service.get_user_subscription(user.id)
    
    if subscription:
        await message.answer(
            f"📊 Ваша подписка:\n\n"
            f"Тариф: {subscription.plan_name}\n"
            f"Действует до: {subscription.expires_at.strftime('%d.%m.%Y')}\n\n"
            "Выберите действие:",
            reply_markup=get_subscription_keyboard()
        )
    else:
        await message.answer(
            "У вас нет активной подписки.\n"
            "Выберите тариф для продолжения работы:",
            reply_markup=get_plans_keyboard()
        )

@router.callback_query(lambda c: c.data == "subscription:plans")
async def handle_plans(callback: types.CallbackQuery):
    """Handle plans button."""
    plans_text = "📋 Доступные тарифы:\n\n"
    
    for plan in settings.SUBSCRIPTION_PLANS.values():
        plans_text += (
            f"🔸 {plan['name']} - {plan['price']}₽\n"
            f"{plan['description']}\n\n"
        )
    
    await callback.message.edit_text(
        plans_text,
        reply_markup=get_plans_keyboard()
    )

@router.callback_query(lambda c: c.data == "subscription:status")
async def handle_status(callback: types.CallbackQuery, session: AsyncSession):
    """Handle subscription status button."""
    query = select(User).where(User.telegram_id == callback.from_user.id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    subscription_service = SubscriptionService(session)
    subscription = await subscription_service.get_user_subscription(user.id)
    
    if subscription:
        plan = settings.SUBSCRIPTION_PLANS[subscription.plan_name]
        status_text = (
            f"📊 Ваша подписка\n\n"
            f"Тариф: {plan['name']}\n"
            f"Стоимость: {subscription.price}₽\n"
            f"Начало: {subscription.starts_at.strftime('%d.%m.%Y')}\n"
            f"Действует до: {subscription.expires_at.strftime('%d.%m.%Y')}\n\n"
            f"{plan['description']}"
        )
    else:
        status_text = (
            "❌ У вас нет активной подписки.\n\n"
            "Выберите тариф для продолжения работы:"
        )
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_plans_keyboard()
    )

@router.callback_query(lambda c: c.data.startswith("plan:"))
async def handle_plan_selection(callback: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    """Handle plan selection."""
    try:
        plan_id = callback.data.split(":")[1]
        plan = settings.SUBSCRIPTION_PLANS[plan_id]
        
        query = select(User).where(User.telegram_id == callback.from_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        # Создаем платеж
        payment_service = PaymentService(session)
        payment = await payment_service.create_payment(
            user_id=user.id,
            plan_name=plan_id,
            return_url=f"https://t.me/{callback.bot.username}?start=payment_{payment['payment_id']}"
        )
        
        # Сохраняем информацию о платеже в состоянии
        await state.update_data(payment_id=payment["payment_id"])
        
        # Создаем клавиатуру для оплаты
        builder = InlineKeyboardBuilder()
        builder.button(
            text="💳 Оплатить",
            url=payment["confirmation_url"]
        )
        builder.button(
            text="🔄 Проверить оплату",
            callback_data=f"check_payment:{payment['payment_id']}"
        )
        builder.button(
            text="❌ Отменить",
            callback_data=f"cancel_payment:{payment['payment_id']}"
        )
        builder.adjust(1)
        
        await callback.message.edit_text(
            f"💳 Оформление подписки\n\n"
            f"Тариф: {plan['name']}\n"
            f"Стоимость: {plan['price']}₽\n\n"
            f"{plan['description']}\n\n"
            "Для оплаты нажмите кнопку 'Оплатить' и следуйте инструкциям.\n"
            "После оплаты нажмите 'Проверить оплату'.",
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error creating payment: {str(e)}", exc_info=True)
        await callback.message.edit_text(
            "❌ Произошла ошибка при создании платежа.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору.",
            reply_markup=get_subscription_keyboard()
        )

@router.callback_query(lambda c: c.data.startswith("check_payment:"))
async def handle_check_payment(callback: types.CallbackQuery, session: AsyncSession):
    """Handle payment check button."""
    try:
        payment_id = callback.data.split(":")[1]
        payment_service = PaymentService(session)
        payment_status = await payment_service.get_payment_status(payment_id)
        
        if not payment_status:
            await callback.answer("❌ Платеж не найден", show_alert=True)
            return
        
        if payment_status["status"] == "succeeded":
            await callback.message.edit_text(
                "✅ Оплата прошла успешно!\n\n"
                "Ваша подписка активирована.",
                reply_markup=get_subscription_keyboard()
            )
        elif payment_status["status"] == "canceled":
            await callback.message.edit_text(
                "❌ Платеж отменен.\n\n"
                "Выберите тариф для повторной попытки:",
                reply_markup=get_plans_keyboard()
            )
        else:
            await callback.answer(
                "⏳ Платеж все еще обрабатывается.\n"
                "Пожалуйста, подождите или попробуйте проверить позже.",
                show_alert=True
            )
            
    except Exception as e:
        logger.error(f"Error checking payment: {str(e)}", exc_info=True)
        await callback.answer(
            "❌ Произошла ошибка при проверке платежа.\n"
            "Пожалуйста, попробуйте позже.",
            show_alert=True
        )

@router.callback_query(lambda c: c.data.startswith("cancel_payment:"))
async def handle_cancel_payment(callback: types.CallbackQuery, session: AsyncSession):
    """Handle payment cancellation button."""
    try:
        payment_id = callback.data.split(":")[1]
        payment_service = PaymentService(session)
        
        if await payment_service.cancel_payment(payment_id):
            await callback.message.edit_text(
                "✅ Платеж успешно отменен.\n\n"
                "Выберите тариф для повторной попытки:",
                reply_markup=get_plans_keyboard()
            )
        else:
            await callback.answer(
                "❌ Не удалось отменить платеж.\n"
                "Возможно, он уже обработан или отменен.",
                show_alert=True
            )
            
    except Exception as e:
        logger.error(f"Error canceling payment: {str(e)}", exc_info=True)
        await callback.answer(
            "❌ Произошла ошибка при отмене платежа.\n"
            "Пожалуйста, попробуйте позже.",
            show_alert=True
        )

@router.callback_query(lambda c: c.data == "subscription:back")
async def handle_subscription_back(callback: types.CallbackQuery):
    """Handle back button in subscription menu."""
    await callback.message.edit_text(
        "💳 Управление подпиской\n\n"
        "Выберите действие:",
        reply_markup=get_subscription_keyboard()
    ) 