"""
Сервис для диаризации речи (разделение речи по спикерам).

Использует модель pyannote/speaker-diarization-3.1 для определения
временных меток, когда говорит каждый спикер в аудиозаписи.
"""
import logging
import os
import traceback

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class DiarizationService:
    """
    Сервис для диаризации речи (разделение по спикерам).
    
    Определяет, кто и когда говорит в аудиозаписи, возвращая
    временные метки для каждого спикера.
    
    Реализует паттерн Singleton для переиспользования загруженной модели.
    
    Attributes:
        _instance: Единственный экземпляр сервиса (Singleton)
        pipeline: Загруженный pipeline pyannote для диаризации
    """
    _instance = None  # Атрибут класса для хранения единственного экземпляра

    def __new__(cls, *args, **kwargs):
        """
        Создает единственный экземпляр сервиса (Singleton паттерн).
        
        Returns:
            DiarizationService: Единственный экземпляр сервиса
        """
        if cls._instance is None:
            logger.info("Экземпляр DiarizationService еще не создан. Создаем новый.")
            cls._instance = super().__new__(cls)
        else:
            logger.info("Экземпляр DiarizationService уже существует. Возвращаем его.")

        return cls._instance

    def __init__(self):
        """
        Инициализирует сервис диаризации и загружает модель pyannote.
        
        Загружает модель "pyannote/speaker-diarization-3.1" из HuggingFace.
        
        Raises:
            ValueError: Если HUGGING_FACE_TOKEN не найден в переменных окружения
            Exception: При ошибках загрузки модели или проблемах с доступом к HuggingFace
        """
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
        """
        Получает временные метки для каждого спикера в аудиофайле.
        
        Анализирует аудиофайл и определяет, когда говорит каждый спикер,
        возвращая словарь с временными метками.
        
        Args:
            audio_filepath: Путь к аудиофайлу для анализа
            
        Returns:
            dict: Словарь формата {(start_time, end_time): "speaker_id", ...}
                  где start_time и end_time - время в секундах (округлено до 2 знаков),
                  speaker_id - идентификатор спикера (например, "SPEAKER_00")
                  
        Example:
            {
                (0.0, 5.2): "SPEAKER_00",
                (5.2, 12.8): "SPEAKER_01",
                (12.8, 18.5): "SPEAKER_00"
            }
            
        Raises:
            Exception: При ошибках обработки аудиофайла
        """
        logger.info("DiarizationService начал доставать временные метки")
        try:
            diarization = self.pipeline(audio_filepath)
        except Exception as e:
                logger.error(e)
        logger.info(f"Закончили DiarizationService")
        result = {}

        # Правильно итерируемся по результатам (Pyannote 3.x)
        # itertracks возвращает (segment, track, label)
        for segment, _, speaker in diarization.itertracks(yield_label=True):
            result[(round(segment.start, 2), round(segment.end, 2))] = speaker

        return result

