# main/schemas/llm_answers_schemas.py
"""
Pydantic схемы для валидации ответов от LLM (Google Gemini).

Используются для структурированного извлечения данных из ответов
языковой модели с гарантией типов и формата.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class IsResumeSchema(BaseModel):
    """
    Схема для классификации письма (резюме или нет).
    
    Используется в методе GeminiService.is_resume() для валидации
    ответа LLM о том, является ли письмо резюме.
    
    Attributes:
        is_resume: "0" - не резюме, "1" - резюме
    """
    is_resume: Literal[
        "0",
        "1"
    ] = Field(
        description="is this mail a cv: 0-it is not cv, 1-yes, it is cv"
    )


class CandidateInfoFromResume(BaseModel):
    """
    Схема для извлечения структурированных данных кандидата из резюме.
    
    Используется в методе GeminiService.get_candidate_info_from_resume()
    для валидации и структурирования данных, извлеченных из резюме.
    
    Attributes:
        full_name: Полное имя кандидата
        programming_languages: Список языков программирования (по одному на строку)
        work_experience: История работы (компания и длительность на строку)
        technologies: Стек технологий (по одному на строку)
        education: Образование (каждое учреждение на новой строке)
        soft_skills: Оценка soft skills или их список
        spoken_languages: Языки и уровень владения (язык уровень на строку)
        email: Email адрес (опционально)
        phone: Номер телефона (опционально)
        telegram: Telegram username или ссылка (опционально)
        
    Note:
        Все поля со списками используют формат с переносами строк (\\n),
        а не запятые, для лучшей структурированности.
    """
    full_name: str = Field(
        description="Full name of the candidate extracted from the resume."
    )

    programming_languages: str = Field(
        description="List of programming languages known by the candidate. "
                    "Format: one language per line. "
                    "Example: 'Python\nJavaScript\nC++'"
    )

    work_experience: str = Field(
        description="Work history including company name and duration. "
                    "Format: 'Company Name Duration' per line. "
                    "Example: 'ElevenLabs 1.5 years\nMbank 2 years'"
    )

    technologies: str = Field(
        description="Technological stack, frameworks, and libraries. "
                    "Format: one technology per line. "
                    "Example: 'Django\nFastAPI\nPostgreSQL'"
    )

    education: str = Field(
        description="Educational background (university, degree, courses). "
                    "Format: each institution/degree on a new line."
    )

    soft_skills: str = Field(
        description="Assessment of soft skills based on the cover letter and resume tone. "
                    "List key soft skills or the evaluation summary, separated by newlines."
    )

    spoken_languages: str = Field(
        description="Spoken languages and proficiency levels. "
                    "Format: 'Language Level' per line. "
                    "Example: 'English B2\nRussian Native'"
    )

    email: Optional[str] = Field(
        description="Contact email address of the candidate. If not found, return null or empty string.",
        default=None
    )

    phone: Optional[str] = Field(
        description="Contact phone number of the candidate. If not found, return null or empty string.",
        default=None
    )

    telegram: Optional[str] = Field(
        description="Telegram username or profile link. If not found, return null or empty string.",
        default=None
    )


class IsRelevantCandidate(BaseModel):
    """
    Схема для оценки релевантности кандидата для вакансии.
    
    Используется в методе GeminiService.is_candidate_relevant_for_position()
    для валидации ответа LLM о соответствии кандидата требованиям позиции.
    
    Attributes:
        is_relevant: "0" - не подходит, "1" - подходит
        
    Note:
        LLM сравнивает навыки и опыт кандидата с требованиями вакансии
        и возвращает бинарную оценку релевантности.
    """
    is_relevant: Literal["0", "1"] = Field(
        description=(
            "Compare the candidate's skills and experience with the position requirements. "
            "Return '1' if there is a strong match, '0' if the candidate is unqualified or irrelevant."
        )
    )


class ExpectedSalaryFromInterview(BaseModel):
    """
    Схема для извлечения ожидаемой зарплаты из транскрипции интервью.
    
    Используется в методе GeminiService.extract_salary_from_transcription()
    для извлечения информации о зарплате из текста интервью.
    
    Attributes:
        expected_salary: Ожидаемая зарплата кандидата (текстовая строка)
                       Может содержать диапазон, валюту, условия и т.д.
                       Например: "150000-200000 рублей", "$5000-7000", "от 200к"
                       
    Note:
        Если зарплата не упоминалась в интервью, возвращается пустая строка.
    """
    expected_salary: str = Field(
        description=(
            "Extract the expected salary mentioned by the candidate during the interview. "
            "Include the amount, currency, and any conditions if mentioned. "
            "If salary was not discussed, return empty string. "
            "Examples: '150000-200000 рублей', '$5000-7000', 'от 200к', '200-250 тысяч'"
        ),
        default=""
    )