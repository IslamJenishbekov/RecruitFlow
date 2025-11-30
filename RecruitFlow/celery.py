"""
Конфигурация Celery для асинхронных задач.

Настраивает Celery для работы с Django и определяет расписание
периодических задач через Celery Beat.
"""
import os

from celery import Celery
from celery.schedules import crontab

# Указываем Django, где искать настройки
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RecruitFlow.settings')

app = Celery('RecruitFlow')

# Загружаем настройки из settings.py, все переменные с префиксом CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим задачи (tasks.py) во всех приложениях
app.autodiscover_tasks()

# --- РАСПИСАНИЕ (CRON) ---
# Расписание периодических задач Celery Beat
# check-mail-every-5-minutes: Проверяет почту пользователей каждые 5 минут
app.conf.beat_schedule = {
    'check-mail-every-5-minutes': {
        'task': 'main.tasks.check_email_task',
        'schedule': 300.0,  # Каждые 5 минут (300 секунд)
    },
}