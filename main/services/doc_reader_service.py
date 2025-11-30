# main/services/doc_reader_service.py
"""
Сервис для чтения документов (PDF и DOCX).

Извлекает текст из файлов резюме для последующего анализа
с помощью LLM.
"""
import io
import logging

from docx import Document
from pypdf import PdfReader

logger = logging.getLogger(__name__)

class DocumentReader:
    """
    Класс для извлечения текста из документов (PDF и DOCX).
    
    Поддерживает форматы:
    - PDF (через pypdf)
    - DOCX (через python-docx)
    """
    def __init__(self):
        """Инициализирует DocumentReader (статический класс)."""
        pass

    @staticmethod
    def read_document(filename: str, payload: bytes) -> str:
        """
        Извлекает текст из документа по его типу.
        
        Определяет тип файла по расширению и вызывает соответствующий
        метод для извлечения текста.
        
        Args:
            filename: Имя файла (используется для определения типа)
            payload: Байты файла для обработки
            
        Returns:
            str: Извлеченный текст из документа с префиксом имени файла.
                 Пустая строка, если файл не поддерживается или произошла ошибка.
                 
        Supported formats:
            - .pdf: PDF документы
            - .docx: Microsoft Word документы
            
        Note:
            Если файл не поддерживается, возвращается пустая строка.
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
        Извлекает текст из PDF файла.
        
        Обрабатывает все страницы PDF и извлекает текстовое содержимое.
        
        Args:
            payload: Байты PDF файла
            
        Returns:
            str: Извлеченный текст со всех страниц, разделенный переносами строк.
                 Пустая строка, если текст не найден или произошла ошибка.
                 
        Note:
            Страницы с только изображениями (без текста) пропускаются.
            
        Raises:
            Exception: При ошибках чтения PDF (логируется, возвращается пустая строка)
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
        Извлекает текст из DOCX файла.
        
        Обрабатывает все параграфы документа и извлекает текстовое содержимое.
        
        Args:
            payload: Байты DOCX файла
            
        Returns:
            str: Извлеченный текст из всех параграфов, разделенный переносами строк.
                 Пустая строка, если текст не найден или произошла ошибка.
                 
        Note:
            Пустые параграфы и лишние пробелы автоматически удаляются.
            
        Raises:
            Exception: При ошибках чтения DOCX (логируется, возвращается пустая строка)
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