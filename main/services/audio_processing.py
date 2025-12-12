"""
Модуль для обработки аудиофайлов и получения транскрипций с диаризацией.

Объединяет функциональность ASR (распознавание речи) и диаризации
для создания полной транскрипции интервью с указанием спикеров.
"""
from pydub import AudioSegment
import os
import logging
logger = logging.getLogger(__name__)


def get_transcription(audio_path):
    """
    Получает полную транскрипцию аудиофайла с разделением по спикерам.
    
    Обрабатывает аудиофайл в следующем порядке:
    1. Загружает аудиофайл
    2. Выполняет диаризацию для определения спикеров
    3. Разрезает аудио на сегменты по спикерам
    4. Транскрибирует каждый сегмент отдельно
    5. Объединяет результаты в единую транскрипцию
    
    Args:
        audio_path: Путь к аудиофайлу для обработки
        
    Returns:
        str: Полная транскрипция в формате:
             "SPEAKER_00 [start-end]: текст\nSPEAKER_01 [start-end]: текст\n..."
             
    Example:
        "SPEAKER_00 [0.0-5.2]: Здравствуйте, расскажите о себе\n
         SPEAKER_01 [5.2-12.8]: Меня зовут Иван, работаю Python разработчиком\n"
         
    Note:
        Временные файлы сегментов автоматически удаляются после обработки.
        
    Raises:
        FileNotFoundError: Если аудиофайл не найден
        Exception: При ошибках обработки аудио или транскрибации
    """
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
    Вырезает сегмент аудио и сохраняет его в отдельный файл.
    
    Извлекает часть аудио между указанными временными метками
    и сохраняет в WAV формате.
    
    Args:
        audiosegment: Объект AudioSegment из pydub с полным аудио
        start_sec: Начало сегмента в секундах
        end_sec: Конец сегмента в секундах
        output_path: Путь для сохранения вырезанного сегмента
        
    Note:
        pydub работает в миллисекундах, поэтому секунды умножаются на 1000.
        Файл сохраняется в формате WAV.
        
    Raises:
        Exception: При ошибках сохранения файла
    """
    t1 = start_sec * 1000
    t2 = end_sec * 1000

    # Срез аудио
    chunk = audiosegment[t1:t2]

    # Сохранение (формат определяется расширением файла или параметром format)
    chunk.export(output_path, format="wav")

