from pyannote.audio import Pipeline
import logging
import os
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)


class DiarizationService():
    _instance = None  # Атрибут класса для хранения единственного экземпляра

    def __new__(cls, *args, **kwargs):
        # __new__ вызывается ПЕРЕД __init__
        # Он отвечает за создание объекта
        if cls._instance is None:
            logger.info("Экземпляр ASRService еще не создан. Создаем новый.")
            # Если экземпляра нет, создаем его стандартным способом
            cls._instance = super().__new__(cls)
        else:
            logger.info("Экземпляр ASRService уже существует. Возвращаем его.")

        # Всегда возвращаем единственный экземпляр
        return cls._instance

    def __init__(self):
        self.pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-community-1",
                        token=os.getenv("HUGGING_FACE_TOKEN"),)

    def get_timestamps(self, audio_filepath: str) -> dict:
        result = {}
        output = self.pipeline(audio_filepath)
        for turn, speaker in output.speaker_diarization:
            result[(turn.start, turn.end)] = speaker
        return result

