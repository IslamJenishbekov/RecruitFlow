import logging
logger = logging.getLogger(__name__)

class ASRService:
    _instance = None  # Атрибут класса для хранения единственного экземпляра

    def __new__(cls, *args, **kwargs):
        # Он отвечает за создание объекта
        if cls._instance is None:
            logger.info("Экземпляр ASRService еще не создан. Создаем новый.")
            # Если экземпляра нет, создаем его стандартным способом
            cls._instance = super().__new__(cls)
        else:
            logger.info("Экземпляр ASRService уже существует. Возвращаем его.")

        # Всегда возвращаем единственный экземпляр
        return cls._instance

    def __init__(self, model_name="v2_rnnt"):
        import gigaam
        logger.info("Первичная инициализация ASRService...")
        self.model = gigaam.load_model(model_name)
        self._initialized = True  # Ставим флаг, что инициализация прошла
        logger.info("ASR модель успешно создана и готова к работе")

    def transcribe(self, audio_filepath: str) -> str:
        text = self.model.transcribe(audio_filepath)
        logger.info(f"Для аудиофайла: {audio_filepath} - транскрибация: {text}")
        return text


if __name__ == "__main__":
    service = ASRService()