# gemini_service.py
from dotenv import load_dotenv
import logging
import os
from typing import Optional
from google import genai
from google.genai import types

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

        #genai.configure(api_key=api_key)
        self.model = model_name
        self.client = genai.Client()
        GeminiService._initialized = True
        logger.info("GeminiService успешно инициализирован с официальным google.generativeai")

    def get_answer(
        self,
        user_query: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Получить ответ от Gemini.

        Args:
            user_query: запрос пользователя
            system_prompt: системная инструкция (поддерживается только в gemini-1.5-pro и выше)

        Returns:
            Текст ответа модели
        """
        logger.info(f"Запрос к Gemini: {user_query[:120]}...")
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=f"{system_prompt}{user_query}",
            )
            logger.info("Ответ от Gemini успешно получен.")
            return response.text

        except Exception as e:
            logger.error(f"Ошибка при запросе к Gemini: {e}")
            raise


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    gemini = GeminiService()

    system = "Ты — лаконичный и остроумный помощник. Отвечай максимально кратко, но точно."
    query = "Почему коты всегда падают на лапы?"

    print(gemini.get_answer(query, system))
