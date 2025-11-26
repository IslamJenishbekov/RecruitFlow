import io
import logging

from django.core.files.base import ContentFile

from ..models import *
from ..services import llm_service, doc_reader_service

logger = logging.getLogger(__name__)
llm = llm_service.GeminiService()

class CandidateOperations:
    @staticmethod
    def create_candidate_from_email(user_id: int, message: dict):
        logger.info("Создание клиента по сообщению с почты")
        candidate_info = llm.get_candidate_info_from_resume(message['subject'], message['text'],
                                                            message['file_content'])
        candidate_info_str = "\n".join([f"{k}: {v}" for k, v in candidate_info.items()])
        logger.info(f"Модель смогла вытащить следующую информацию: {candidate_info}")
        positions = Position.objects.filter(project__users__id=user_id).distinct()

        for position in positions:
            if llm.is_candidate_relevant_for_position(candidate_info_str, position.requirements):
                logger.info(f"Сотрудник подходит под вакансию: {position.id}")
                prog_langs = candidate_info.get('programming_languages', '').replace('\n', ', ')[:100]
                langs = candidate_info.get('spoken_languages', '').replace('\n', ', ')[:255]

                candidate = Candidate.objects.create(
                    position=position,
                    full_name=candidate_info.get('full_name', 'Без имени'),
                    experience=candidate_info.get('work_experience', ''),
                    programming_language=prog_langs,
                    used_technologies=candidate_info.get('technologies', ''),
                    education=candidate_info.get('education', ''),
                    soft_skills=candidate_info.get('soft_skills', ''),
                    languages=langs,
                    gmail=candidate_info.get('email'),
                    telegram=candidate_info.get('telegram', ''),
                    phone_number=candidate_info.get('phone'),
                    status='new'
                )

                # --- СОХРАНЕНИЕ ФАЙЛА ---
                # Проверяем, есть ли байты файла в сообщении
                if message.get('file_payload') and message.get('file_name'):
                    try:
                        # ContentFile превращает байты в "файл" для Django
                        file_content = ContentFile(message['file_payload'])

                        # Метод save автоматически сохранит файл на диск/S3 и обновит поле в БД
                        candidate.cv_file.save(message['file_name'], file_content)
                        logger.info(f"Файл {message['file_name']} сохранен для кандидата {candidate.id}")
                    except Exception as e:
                        logger.error(f"Ошибка сохранения файла: {e}")

                break

    @staticmethod
    def create_candidate_from_single_document(uploaded_file, position: Position):
        logger.info(f"Создание файла по готовому документу")
        filename = uploaded_file.name
        file_bytes = uploaded_file.read()
        extracted_text = doc_reader_service.DocumentReader.read_document(filename, file_bytes)
        candidate_info = llm.get_candidate_info_from_resume("Empty", "Empty", extracted_text)
        prog_langs = candidate_info.get('programming_languages', '').replace('\n', ', ')[:100]
        langs = candidate_info.get('spoken_languages', '').replace('\n', ', ')[:255]

        candidate = Candidate.objects.create(
            position=position,
            full_name=candidate_info.get('full_name', 'Без имени'),
            experience=candidate_info.get('work_experience', ''),
            programming_language=prog_langs,
            used_technologies=candidate_info.get('technologies', ''),
            education=candidate_info.get('education', ''),
            soft_skills=candidate_info.get('soft_skills', ''),
            languages=langs,
            gmail=candidate_info.get('email'),
            telegram=candidate_info.get('telegram', '') or "",
            phone_number=candidate_info.get('phone'),
            status='new'
        )

        # --- СОХРАНЕНИЕ ФАЙЛА ---
        try:
            # ContentFile превращает байты в "файл" для Django
            file_content = ContentFile(file_bytes)

            # Метод save автоматически сохранит файл на диск/S3 и обновит поле в БД
            candidate.cv_file.save(filename, file_content)
            logger.info(f"Файл {filename} сохранен для кандидата {candidate.id}")
        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {e}")



