# main/services/mail_service.py
"""
Сервис для работы с электронной почтой через IMAP.

Обеспечивает получение писем из Gmail, извлечение вложений
и парсинг содержимого резюме из писем.
"""
import io
import logging
import smtplib
from email.message import EmailMessage
from imap_tools import MailBox

from . import doc_reader_service

logger = logging.getLogger(__name__)


class MailService:
    """
    Сервис для работы с почтой через IMAP протокол.
    
    Подключается к Gmail через IMAP, получает последние письма,
    извлекает вложения (резюме) и парсит их содержимое.
    """

    @staticmethod
    def get_last_messages(mail, pwd, num_of_messages: int = 50):
        """
        Получает последние письма из почтового ящика Gmail.
        
        Подключается к Gmail через IMAP, получает указанное количество
        последних писем, извлекает текст и вложения (резюме).
        
        Args:
            mail: Email адрес для подключения
            pwd: Пароль приложения Gmail (App Password)
            num_of_messages: Количество последних писем для получения (по умолчанию 50)
            
        Returns:
            list: Список словарей с данными писем, каждый содержит:
                - from: Отправитель
                - date: Дата письма
                - subject: Тема письма
                - text: Текст письма (HTML или plain text)
                - file_content: Извлеченный текст из первого найденного вложения
                - file_name: Имя файла вложения
                - file_payload: Байты файла вложения (для сохранения)
                
        Note:
            Обрабатывается только первое найденное вложение с текстом (PDF/DOCX).
            Если вложение не содержит текста или не поддерживается, file_content будет пустым.
            
        Raises:
            Exception: При ошибках подключения к почте или парсинга писем
        """
        processed_messages = []
        try:
            with MailBox("imap.gmail.com").login(mail, pwd) as mailbox:
                for message in mailbox.fetch(limit=num_of_messages, reverse=True):

                    file_content_text = ""
                    file_name = None
                    file_payload = None  # Байты файла

                    full_text = message.text or message.html or ""

                    for att in message.attachments:
                        extracted_text = doc_reader_service.DocumentReader.read_document(att.filename, att.payload)

                        if extracted_text:
                            # Если текст извлекся, считаем это основным файлом резюме
                            file_content_text += extracted_text

                            # Сохраняем метаданные для сохранения файла в БД
                            file_name = att.filename
                            file_payload = att.payload
                            break

                    msg_data = {
                        "from": message.from_,
                        "date": message.date,
                        "subject": message.subject,
                        "text": full_text,
                        "file_content": file_content_text,
                        "file_name": file_name,
                        "file_payload": file_payload
                    }
                    processed_messages.append(msg_data)
        except Exception as e:
            logger.error(f"Error parsing mail: {e}")

        return processed_messages

    @staticmethod
    def send_message(sender_email, subject, body, pwd, to_email):
        msg = EmailMessage()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.set_content(body)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, pwd)
            smtp.send_message(msg)
            logger.info(f"Сообщение {to_email} отправлено")

