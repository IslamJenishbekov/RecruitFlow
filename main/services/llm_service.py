# main/services/llm_service.py
import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import ValidationError

# Импортируем вашу схему
from main.schemas.llm_answers_schemas import *

logger = logging.getLogger(__name__)
load_dotenv()


class GeminiService:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            logger.info("Создание единственного экземпляра GeminiService...")
            cls._instance = super(GeminiService, cls).__new__(cls)
        else:
            logger.info("Возвращение существующего экземпляра GeminiService...")
        return cls._instance

    def __init__(
            self,
            model_name: str = "gemini-2.0-flash"
    ):
        if GeminiService._initialized:
            return

        logger.info(f"Инициализация GeminiService (модель: {model_name})...")

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY не найден! Укажи его в .env или передай явно.")

        self.model = model_name
        # Инициализация клиента нового SDK
        self.client = genai.Client(api_key=api_key)
        GeminiService._initialized = True
        logger.info("GeminiService успешно инициализирован.")

    def is_resume(self, title: str, content: str, file_content: str) -> bool:
        """
        Определяет, является ли письмо резюме, используя LLM и Pydantic схему.
        Возвращает True, если это резюме (1), и False, если нет (0).
        """

        # Формируем промпт из всех источников данных
        user_prompt = f"""
        Analyze the following email data and determine if it is a Resume/CV or a Job Application.

        Email Subject: {title}

        Email Body:
        {content}

        Attachment Content:
        {file_content[:10000]}  # Limit text length to avoid token overflow
        """

        system_instruction = (
            "You are an expert HR Data Classifier. "
            "Your task is to analyze the input and determine if it contains a candidate's Resume/CV "
            "or is a direct job application. "
            "Ignore spam, marketing, and unrelated business emails."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=IsResumeSchema,
                    temperature=0.7
                )
            )

            if response.parsed:
                result: IsResumeSchema = response.parsed
                logger.info(f"LLM Analysis Result: {result.is_resume}")

                # Конвертируем строковый "0"/"1" в Python bool
                return result.is_resume == "1"

            logger.warning("LLM вернула пустой parsed-ответ.")
            return False

        except ValidationError as e:
            logger.error(f"Ошибка валидации Pydantic: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при запросе к Gemini API: {e}")
            return False

    def get_candidate_info_from_resume(self, title: str, content: str, file_content: str) -> dict:
        """
        Извлекает структурированные данные кандидата из текста резюме и письма.
        Возвращает словарь (dict), соответствующий схеме CandidateInfoFromResume.
        В случае ошибки возвращает пустой словарь.
        """

        # Формируем промпт. Важно дать приоритет файлу (резюме), а тело письма использовать как дополнение.
        user_prompt = f"""
        Extract detailed candidate information from the provided Resume text and Email context.

        PRIMARY SOURCE (Resume):
        {file_content[:20000]}  # Берем первые 20к символов, чтобы влезло в контекст

        SECONDARY SOURCE (Email Context):
        Subject: {title}
        Body: {content}

        INSTRUCTIONS:
        1. Extract data strictly according to the requested schema.
        2. For list fields, ensure elements are separated by NEW LINE characters (\\n), not commas.
        3. If specific data is missing, leave the field empty or null.
        """

        system_instruction = (
            "You are an expert HR Resume Parser AI. "
            "Your goal is to structure unstructured resume data into a standardized JSON format. "
            "Be precise with names, dates, and technical stacks. "
            "Do not invent information. If a skill is not listed, do not add it."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=CandidateInfoFromResume,
                    temperature=0.7
                )
            )

            if response.parsed:
                result: CandidateInfoFromResume = response.parsed
                logger.info(f"Данные кандидата успешно извлечены: {result.full_name}")

                # Превращаем Pydantic объект в обычный словарь Python
                return result.model_dump()

            logger.warning("LLM не смогла распарсить данные кандидата (пустой ответ).")
            return {}

        except ValidationError as e:
            logger.error(f"Ошибка валидации структуры данных кандидата: {e}")
            return {}
        except Exception as e:
            logger.error(f"Критическая ошибка при парсинге резюме через Gemini: {e}")
            return {}

    def is_candidate_relevant_for_position(self, candidate_info: str, position_requirements: str) -> bool:
        """
        Оценивает, подходит ли кандидат под требования вакансии.
        :param candidate_info: Строка или JSON с данными кандидата (навыки, опыт и т.д.)
        :param position_requirements: Текст требований вакансии
        :return: True, если кандидат релевантен, иначе False.
        """

        # Если требований нет, считаем, что кандидат подходит (или наоборот, зависит от бизнес-логики)
        # Для MVP логично: если требований нет, берем всех.
        if not position_requirements or not position_requirements.strip():
            logger.warning("Требования к вакансии пусты. Кандидат считается релевантным по умолчанию.")
            return True

        user_prompt = f"""
        Please evaluate the relevance of the candidate for the specific job position based on the provided data.

        JOB POSITION REQUIREMENTS:
        {position_requirements}

        CANDIDATE PROFILE:
        {candidate_info}
        """

        system_instruction = (
            "You are an expert HR Recruiter performing an initial resume screening. "
            "Compare the Candidate Profile against the Job Position Requirements. "
            "Look for matching technical skills, experience level, and relevant background. "
            "Ignore minor formatting issues. Focus on the core stack and qualifications."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=IsRelevantCandidate,  # Используем схему Literal["0", "1"]
                    temperature=0.7
                )
            )

            if response.parsed:
                result: IsRelevantCandidate = response.parsed
                is_relevant = result.is_relevant == "1"

                logger.info(f"Релевантность кандидата: {'✅ Подходит' if is_relevant else '❌ Не подходит'}")
                return is_relevant

            logger.warning("LLM вернула пустой ответ при проверке релевантности.")
            return False

        except ValidationError as e:
            logger.error(f"Ошибка валидации ответа LLM (релевантность): {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка Gemini при проверке релевантности: {e}")
            return False