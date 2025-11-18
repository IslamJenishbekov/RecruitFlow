from imap_tools import MailBox, AND
import logging
logger = logging.getLogger(__name__)


class MailService:
    def __init__(self):
        pass

    def get_last_messages(self, mail, pwd, num_of_messages: int = 50):
        with MailBox("imap.gmail.com").login(mail, pwd) as mailbox:
            messages = mailbox.fetch()
        return messages[:num_of_messages]



        