from pydub import AudioSegment
import os
import logging
logger = logging.getLogger(__name__)


def get_transcription(audio_path):
    from . import diarization_service, asr_service
    logger.info(f"Инициализация моделей диаризации и ASR")
    asr, diarization = asr_service.ASRService(), diarization_service.DiarizationService()
    logger.info(f"Загрузка аудиофайла: {audio_path}")
    full_audio = AudioSegment.from_file(audio_path)

    # 2. Получаем таймстемпы диаризации
    # Ожидается формат: {(start, end): "Speaker_1", ...}
    timestamps = diarization.get_timestamps(audio_path)
    transcription = ""

    # 3. Проходим по всем сегментам
    for timestamp in timestamps:
        speaker = timestamps[timestamp]
        start, end = timestamp[0], timestamp[1]

        # Формируем имя временного файла
        # Используем abspath, чтобы избежать проблем с путями
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        temp_filename = f"{base_name}_{start}_{end}.wav"

        try:
            # Сохраняем кусок
            save_chunk(full_audio, start, end, temp_filename)

            # Распознаем текст
            text = asr.transcribe(temp_filename)

            # Добавляем к общему тексту
            line = f"{speaker} [{start}-{end}]: {text}\n"
            transcription += line

        except Exception as e:
            logger.error(f"Ошибка при обработке сегмента {start}-{end}: {e}")

        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    return transcription

def save_chunk(audiosegment, start_sec, end_sec, output_path):
    """
    Вырезает кусок аудио и сохраняет его.
    pydub работает в миллисекундах, поэтому умножаем секунды на 1000.
    """
    t1 = start_sec * 1000
    t2 = end_sec * 1000

    # Срез аудио
    chunk = audiosegment[t1:t2]

    # Сохранение (формат определяется расширением файла или параметром format)
    chunk.export(output_path, format="wav")