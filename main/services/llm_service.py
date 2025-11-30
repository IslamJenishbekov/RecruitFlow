# main/services/llm_service.py
"""
Сервис для работы с Google Gemini API.

Предоставляет функциональность для:
- Классификации писем (резюме/не резюме)
- Извлечения структурированных данных из резюме
- Оценки релевантности кандидатов для вакансий
"""
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
    """
    Сервис для работы с Google Gemini API (Singleton паттерн).
    
    Использует Google Gemini 2.0 Flash для анализа текста, классификации
    и извлечения структурированных данных из резюме кандидатов.
    
    Attributes:
        _instance: Единственный экземпляр сервиса (Singleton)
        _initialized: Флаг инициализации
        model: Название используемой модели Gemini
        client: Клиент Google Gemini API
    """
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """
        Создает единственный экземпляр сервиса (Singleton паттерн).
        
        Returns:
            GeminiService: Единственный экземпляр сервиса
        """
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
        """
        Инициализирует сервис Gemini.
        
        Args:
            model_name: Название модели Gemini (по умолчанию "gemini-2.0-flash")
            
        Raises:
            ValueError: Если GOOGLE_API_KEY не найден в переменных окружения
        """
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
        
        Анализирует тему письма, тело письма и содержимое вложений,
        чтобы определить, содержит ли письмо резюме кандидата.
        
        Args:
            title: Тема письма
            content: Текст письма
            file_content: Извлеченный текст из вложений (первые 10000 символов)
            
        Returns:
            bool: True, если письмо содержит резюме, False в противном случае
            
        Note:
            В случае ошибки API или валидации возвращает False
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
        
        Парсит резюме и извлекает следующую информацию:
        - ФИО, контакты (email, телефон, Telegram)
        - Опыт работы, навыки, стек технологий
        - Образование, языки, soft skills
        
        Args:
            title: Тема письма (используется как дополнительный контекст)
            content: Текст письма (вторичный источник)
            file_content: Основной текст резюме из вложений (первые 20000 символов)
            
        Returns:
            dict: Словарь с данными кандидата согласно схеме CandidateInfoFromResume.
                  В случае ошибки возвращает пустой словарь.
                  
        Note:
            Приоритет отдается содержимому файла резюме, текст письма используется
            как дополнительный контекст.
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
        
        Сравнивает профиль кандидата с требованиями позиции, анализируя:
        - Совпадение технических навыков
        - Уровень опыта
        - Релевантность фона
        
        Args:
            candidate_info: Строка или JSON с данными кандидата (навыки, опыт и т.д.)
            position_requirements: Текст требований вакансии
            
        Returns:
            bool: True, если кандидат релевантен для позиции, False в противном случае.
                  Если требования пусты, возвращает True (кандидат считается подходящим).
                  
        Note:
            Если требования к вакансии пусты, кандидат автоматически считается релевантным.
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

    def extract_salary_from_transcription(self, transcription: str) -> str:
        """
        Извлекает ожидаемую зарплату из транскрипции интервью.
        
        Анализирует текст транскрипции интервью и извлекает информацию
        о зарплате, которую упомянул кандидат во время собеседования.
        
        Args:
            transcription: Полный текст транскрипции интервью
            
        Returns:
            str: Ожидаемая зарплата в текстовом формате (например, "150000-200000 рублей").
                 Пустая строка, если зарплата не упоминалась или не была найдена.
                 
        Example:
            "150000-200000 рублей" или "$5000-7000" или "от 200к"
            
        Note:
            В случае ошибки API или валидации возвращает пустую строку.
        """
        if not transcription or not transcription.strip():
            logger.warning("Транскрипция пуста, невозможно извлечь зарплату.")
            return ""

        user_prompt = f"""
        Analyze the following interview transcription and extract the expected salary 
        mentioned by the candidate during the interview.

        INTERVIEW TRANSCRIPTION:
        {transcription[:15000]}  # Ограничиваем длину для экономии токенов

        INSTRUCTIONS:
        1. Look for any mentions of salary, compensation, or expected payment
        2. Extract the exact amount, range, or conditions mentioned
        3. Include currency if mentioned (рубли, dollars, USD, etc.)
        4. If salary was not discussed, return empty string
        5. Preserve the format as mentioned (e.g., "150-200 тысяч", "$5000-7000")
        """

        system_instruction = (
            "You are an expert HR assistant extracting salary information from interview transcripts. "
            "Your task is to identify and extract the exact salary expectations mentioned by the candidate. "
            "Be precise with numbers, ranges, and currency. If no salary was discussed, return empty string."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=ExpectedSalaryFromInterview,
                    temperature=0.3  # Низкая температура для более точного извлечения
                )
            )

            if response.parsed:
                result: ExpectedSalaryFromInterview = response.parsed
                salary = result.expected_salary.strip()
                
                if salary:
                    logger.info(f"Извлечена зарплата из транскрипции: {salary}")
                else:
                    logger.info("Зарплата не найдена в транскрипции.")
                
                return salary

            logger.warning("LLM вернула пустой ответ при извлечении зарплаты.")
            return ""

        except ValidationError as e:
            logger.error(f"Ошибка валидации при извлечении зарплаты: {e}")
            return ""
        except Exception as e:
            logger.error(f"Ошибка Gemini при извлечении зарплаты: {e}")
            return ""