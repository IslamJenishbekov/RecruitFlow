"""
Сервис для автоматического распознавания речи (ASR - Automatic Speech Recognition).

Использует модель GigaAM для транскрибации аудиофайлов в текст.
Реализует паттерн Singleton для оптимизации использования памяти.
"""
import logging
logger = logging.getLogger(__name__)

class ASRService:
    """
    Сервис для распознавания речи с использованием модели GigaAM.
    
    Реализует паттерн Singleton для переиспользования загруженной модели,
    что позволяет избежать повторной загрузки тяжелой ML модели.
    
    Attributes:
        _instance: Единственный экземпляр сервиса (Singleton)
        model: Загруженная модель GigaAM для распознавания речи
        _initialized: Флаг инициализации модели
    """
    _instance = None  # Атрибут класса для хранения единственного экземпляра

    def __new__(cls, *args, **kwargs):
        """
        Создает единственный экземпляр сервиса (Singleton паттерн).
        
        Returns:
            ASRService: Единственный экземпляр сервиса
        """
        if cls._instance is None:
            logger.info("Экземпляр ASRService еще не создан. Создаем новый.")
            cls._instance = super().__new__(cls)
        else:
            logger.info("Экземпляр ASRService уже существует. Возвращаем его.")

        return cls._instance

    def __init__(self, model_name="v2_rnnt"):
        """
        Инициализирует сервис ASR и загружает модель GigaAM.
        
        Args:
            model_name: Название модели GigaAM для загрузки (по умолчанию "v2_rnnt")
            
        Note:
            Модель загружается только при первом создании экземпляра.
            Последующие вызовы используют уже загруженную модель.
        """
        import gigaam
        logger.info("Первичная инициализация ASRService...")
        self.model = gigaam.load_model(model_name)
        self._initialized = True  # Ставим флаг, что инициализация прошла
        logger.info("ASR модель успешно создана и готова к работе")

    def transcribe(self, audio_filepath: str) -> str:
        """
        Транскрибирует аудиофайл в текст.
        
        Принимает путь к аудиофайлу и возвращает распознанный текст.
        
        Args:
            audio_filepath: Путь к аудиофайлу для транскрибации
            
        Returns:
            str: Распознанный текст из аудиофайла
            
        Raises:
            FileNotFoundError: Если файл не найден
            Exception: При ошибках распознавания речи
        """
        text = self.model.transcribe(audio_filepath)
        logger.info(f"Для аудиофайла: {audio_filepath} - транскрибация: {text}")
        return text


if __name__ == "__main__":
    service = ASRService()