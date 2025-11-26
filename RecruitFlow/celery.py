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
app.conf.beat_schedule = {
    'check-mail-every-5-minutes': {
        'task': 'main.tasks.check_email_task',
        'schedule': 300.0,
    },
}