# main/apps.py
import os
import threading
from django.apps import AppConfig


# class MainConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'main'  # Убедитесь, что имя совпадает с папкой вашего приложения
#
#     def ready(self):
#         """
#         Метод выполняется один раз при запуске Django.
#         """
#         # Проверка: RUN_MAIN устанавливается Django только в основном процессе сервера.
#         # Без этой проверки бот запустится дважды (один раз в 'watcher', второй в 'worker')
#         # или запустится при выполнении команд типа 'makemigrations', что нам не нужно.
#         if os.environ.get('RUN_MAIN') == 'true':
#             # Импортируем функцию запуска здесь, чтобы модели успели загрузиться
#             from main.services.telegram_service import start_bot_service
#
#             print("⚙️ Инициализация сервиса ботов...")
#
#             # Запускаем сервис в отдельном потоке (Daemon),
#             # чтобы он не блокировал основной сайт
#             bot_thread = threading.Thread(target=start_bot_service)
#             bot_thread.daemon = True
#             bot_thread.start()
