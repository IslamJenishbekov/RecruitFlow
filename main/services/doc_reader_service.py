# main/services/doc_reader_service.py

import io
import logging

from docx import Document
from pypdf import PdfReader

logger = logging.getLogger(__name__)

class DocumentReader():
    def __init__(self):
        pass

    @staticmethod
    def read_document(filename: str, payload: bytes) -> str:
        """
        Определяет тип файла по расширению и вызывает соответствующий парсер.
        """
        filename = filename.lower()
        logger.info(f"Начали читать документ: {filename}")
        text = ""
        if filename.endswith('.pdf'):
            text = f"Название документа: {filename}\n" + DocumentReader._read_pdf_from_bytes(payload)
        elif filename.endswith('.docx'):
            text = f"Название документа: {filename}\n" + DocumentReader._read_docx_from_bytes(payload)

        logger.info(f"Успешно прочитали документ и его содержимое: {text[:100]}")
        return text

    @staticmethod
    def _read_pdf_from_bytes(payload: bytes) -> str:
        """
        Извлекает текст из PDF (используя pypdf).
        """
        text = ""
        try:
            # Оборачиваем байты в поток, чтобы pypdf думал, что это открытый файл
            file_stream = io.BytesIO(payload)
            reader = PdfReader(file_stream)

            for page in reader.pages:
                # extract_text() может вернуть None, если на странице только картинка
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        except Exception as e:
            logger.error(f"Ошибка при чтении PDF: {e}")

        return text

    @staticmethod
    def _read_docx_from_bytes(payload: bytes) -> str:
        """
        Извлекает текст из DOCX (используя python-docx).
        """
        text = ""
        try:
            # Оборачиваем байты в поток
            file_stream = io.BytesIO(payload)
            doc = Document(file_stream)

            # Собираем все параграфы в один текст
            # strip() удаляет лишние пробелы
            text = "\n".join([para.text.strip() for para in doc.paragraphs if para.text])

        except Exception as e:
            logger.error(f"Ошибка при чтении DOCX: {e}")

        return text