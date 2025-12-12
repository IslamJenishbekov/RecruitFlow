# main/telegram_service.py
import asyncio
import threading
from typing import Dict
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from django.conf import settings
from asgiref.sync import sync_to_async

# Импорт модели пользователя и модели сессии
from django.contrib.auth import get_user_model
from main.models import BotInterviewSession  # <--- Импортируем модель сессии


class BotManager:
    """
    Singleton-сервис для управления Telegram ботами.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.active_bots = {}
        return cls._instance

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Общий обработчик сообщений (и /start, и обычного текста).
        """
        user = update.effective_user
        raw_username = user.username

        if not raw_username:
            await update.message.reply_text("У вас не установлен Username в Telegram. Я не могу найти ваше интервью.")
            return

        # Приводим юзернейм к тому же виду, как сохраняем в БД (без @)
        clean_username = raw_username.replace('@', '').strip()

        # 1. Асинхронная проверка наличия активной сессии в БД
        @sync_to_async
        def check_active_session():
            # Используем __iexact для нечувствительности к регистру
            return BotInterviewSession.objects.filter(
                telegram_username__iexact=clean_username,
                status='active'
            ).exists()

        has_session = await check_active_session()

        # 2. Логика ответа
        if has_session:
            await update.message.reply_text(
                "Звучит практично. Тесты действительно снимают эмоции. Давайте представим ситуацию: получили задачу: «Сделай модель, которая будет автоматически классифицировать обращения клиентов». Никаких данных, никакого ТЗ, только одно предложение. Ваши первые шаги?")
            # TODO: Здесь в будущем будет вызов логики самого интервью (OpenAI API)
        else:
            # Если это была команда /start, приветствуем, иначе говорим, что интервью нет
            if update.message.text and update.message.text.startswith('/start'):
                await update.message.reply_text(f"Привет, {user.first_name}! Для вас пока нет назначенных интервью.")
            else:
                await update.message.reply_text("У вас нет активных интервью. Дождитесь назначения от HR.")

        # Лог в консоль
        bot_username = context.bot.username
        print(f"📨 [BOT @{bot_username}] Сообщение от @{clean_username}. Активная сессия: {has_session}")

    async def start_bot(self, token: str):
        """Запуск одного бота"""
        if token in self.active_bots:
            return

        try:
            app = ApplicationBuilder().token(token).build()

            # Добавляем обработчик команды /start
            app.add_handler(CommandHandler("start", self._handle_message))

            # Добавляем обработчик ЛЮБОГО текста (чтобы отвечать "есть" не только на /start)
            # filters.TEXT & ~filters.COMMAND означает "текст, который не является командой"
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

            await app.initialize()
            await app.start()
            # Запускаем поллинг без блокировки (non-blocking)
            await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

            self.active_bots[token] = app
            print(f"✅ Бот с токеном {token[:10]}... успешно запущен")
        except Exception as e:
            print(f"❌ Ошибка запуска бота: {e}")

    async def run(self):
        """Основной цикл поиска токенов и запуска ботов"""
        User = get_user_model()
        print("🚀 Сервис Telegram ботов запущен (asyncio loop)")

        while True:
            # 1. Получаем токены из БД (асинхронно)
            @sync_to_async
            def get_tokens():
                # Берем токены, которые не пустые и не NULL
                return list(User.objects.filter(telegram_bot_token__isnull=False)
                            .exclude(telegram_bot_token__exact='')
                            .values_list('telegram_bot_token', flat=True))

            tokens = await get_tokens()

            # 2. Запускаем ботов для новых токенов
            for token in tokens:
                if token not in self.active_bots:
                    await self.start_bot(token)

            # 3. Ждем перед следующей проверкой
            await asyncio.sleep(10)


def start_bot_service():
    """Функция-точка входа для запуска в потоке"""
    # Создаем новый event loop для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    manager = BotManager()
    loop.run_until_complete(manager.run())
