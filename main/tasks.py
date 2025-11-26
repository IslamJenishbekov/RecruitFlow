import logging

from celery import shared_task
from repository import candidate

from .models import *
from .services import llm_service, mail_service

logger = logging.getLogger(__name__)
from collections import defaultdict

import redis

llm = llm_service.GeminiService()
redis_service = redis.Redis(host='localhost', port=6379, db=1)


@shared_task
def check_email_task():
    logger.info("--- ЗАПУСК ПАРСЕРА ПОЧТЫ ---")

    users = CustomUser.objects.exclude(gmail_password__isnull=True).exclude(gmail_password__exact='')

    # Используем список, чтобы хранить несколько писем для одного юзера
    resume_messages = defaultdict(list)

    for user in users:
        logger.info(f"Проверка почты для {user.username}...")
        try:
            messages = mail_service.MailService.get_last_messages(user.email, user.gmail_password)

            for message in messages:
                # Уникальный ID письма для Redis (лучше использовать message-id из заголовков, но пока так)
                message_id = f"{message['from']}_{str(message['date'])}"

                # Проверяем в Redis, было ли письмо обработано
                if redis_service.sismember("processed_emails", message_id):
                    continue  # Пропускаем, если уже видели

                # Добавляем в Redis (отмечаем как обработанное)
                redis_service.sadd("processed_emails", message_id)

                # Проверяем через LLM
                if llm.is_resume(message['subject'], message['text'], message['file_content']):
                    # Добавляем в список для этого юзера
                    resume_messages[user.id].append(message)

        except Exception as e:
            logger.error(f"Ошибка у юзера {user.username}: {e}")

    # Запускаем создание кандидатов
    if resume_messages:
        create_candidates(resume_messages)

    return "Проверка завершена"


def create_candidates(messages_dict: dict):
    # messages_dict теперь выглядит так: {user_id: [msg1, msg2], user_id2: [msg1]}
    for user_id, messages_list in messages_dict.items():
        for message in messages_list:
            candidate.Candidate.create_candidate_from_email(user_id, message)
