import logging
import os
import traceback

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class DiarizationService():
    _instance = None  # Атрибут класса для хранения единственного экземпляра

    def __new__(cls, *args, **kwargs):
        # Он отвечает за создание объекта
        if cls._instance is None:
            logger.info("Экземпляр DiarizationService еще не создан. Создаем новый.")
            # Если экземпляра нет, создаем его стандартным способом
            cls._instance = super().__new__(cls)
        else:
            logger.info("Экземпляр DiarizationService уже существует. Возвращаем его.")

        # Всегда возвращаем единственный экземпляр
        return cls._instance

    def __init__(self):
        from pyannote.audio import Pipeline
        logger.info("Начинаем инициализацию DiarizationService")

        try:
            token = os.getenv("HUGGING_FACE_TOKEN")
            if not token:
                logger.error("HUGGING_FACE_TOKEN не найден в переменных окружения!")

            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=token)

            if self.pipeline is None:
                logger.error("Не удалось загрузить Pipeline (вернулся None). Проверьте права доступа на HuggingFace.")
            else:
                logger.info("Diarization service started SUCCESS")

        except Exception as e:
            logger.error(f"ОШИБКА при загрузке модели диаризации: {e}")
            # Вывод полного трейсбека, чтобы понять причину
            logger.error(traceback.format_exc())
            raise e  # Пробрасываем ошибку дальше, чтобы увидеть её влияние


    def get_timestamps(self, audio_filepath: str) -> dict:
        # 1. Запускаем диаризацию
        logger.info("DiarizationService начал доставать временные метки")
        try:
            diarization = self.pipeline(audio_filepath)
        except Exception as e:
                logger.error(e)
        logger.info(f"Закончили DiarizationService")
        result = {}

        # 2. Правильно итерируемся по результатам (Pyannote 3.x)
        # itertracks возвращает (segment, track, label)
        for segment, _, speaker in diarization.itertracks(yield_label=True):
            result[(round(segment.start, 2), round(segment.end, 2))] = speaker

        return result

