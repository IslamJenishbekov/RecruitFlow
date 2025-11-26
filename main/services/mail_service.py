# main/services/mail_service.py

import io
import logging

from imap_tools import MailBox

from . import doc_reader_service

logger = logging.getLogger(__name__)


class MailService:
    @staticmethod
    def get_last_messages(mail, pwd, num_of_messages: int = 50):
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