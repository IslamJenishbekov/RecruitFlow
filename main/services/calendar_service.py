# main/services/calendar_service.py
"""
Сервис для работы с Google Calendar API.

Предоставляет функциональность для:
- Поиска свободных слотов в календаре
- Создания событий (встреч) с приглашениями
"""
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class GoogleCalendarService:
    """
    Сервис для работы с Google Calendar через API.
    
    Использует OAuth2 credentials для авторизации и выполнения операций
    с календарем пользователя.
    
    Attributes:
        creds: OAuth2 credentials пользователя
        service: Объект Google Calendar API service
    """
    def __init__(self, user_credentials_data):
        """
        Инициализирует сервис Google Calendar с credentials пользователя.
        
        Args:
            user_credentials_data: JSON словарь с OAuth2 токенами пользователя,
                                  сохраненный после авторизации через OAuth flow.
                                  Должен содержать: token, refresh_token, client_id,
                                  client_secret, token_uri, scopes.
        """
        self.creds = Credentials.from_authorized_user_info(user_credentials_data)
        self.service = build('calendar', 'v3', credentials=self.creds)

    def get_free_slots(self, date_check: datetime.date, duration_minutes=45):
        """
        Ищет свободные временные слоты в календаре на указанную дату.
        
        Анализирует календарь пользователя и находит периоды времени,
        когда нет запланированных событий и есть достаточно времени
        для встречи указанной длительности.
        
        Args:
            date_check: Дата для поиска свободных слотов
            duration_minutes: Минимальная длительность свободного слота в минутах
                             (по умолчанию 45)
                             
        Returns:
            list: Список datetime объектов с началом каждого свободного слота.
                  Рабочее время: 10:00 - 19:00.
                  Пустой список, если свободных слотов не найдено.
                  
        Note:
            Рабочее время жестко задано как 10:00-19:00.
            В будущих версиях рекомендуется брать из настроек пользователя.
            
        Raises:
            Exception: При ошибках доступа к Google Calendar API
        """
        work_start = datetime.datetime.combine(date_check, datetime.time(10, 0))
        work_end = datetime.datetime.combine(date_check, datetime.time(19, 0))

        # Получаем занятые периоды (события) из календаря
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=work_start.isoformat() + 'Z',
            timeMax=work_end.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        free_slots = []
        current_time = work_start

        # Упрощенный алгоритм поиска "дырок"
        for event in events:
            # Парсим время начала события (учитываем timezone в реальном проекте!)
            start = event['start'].get('dateTime', event['start'].get('date'))
            start_dt = datetime.datetime.fromisoformat(start)

            # Если есть место до начала следующего события
            gap = (start_dt.replace(tzinfo=None) - current_time)
            if gap.total_seconds() / 60 >= duration_minutes:
                free_slots.append(current_time)

            # Сдвигаем текущее время на конец этого события
            end = event['end'].get('dateTime', event['end'].get('date'))
            current_time = datetime.datetime.fromisoformat(end).replace(tzinfo=None)

        # Проверка последнего слота (после последнего события до конца рабочего дня)
        if (work_end - current_time).total_seconds() / 60 >= duration_minutes:
            free_slots.append(current_time)

        return free_slots

    def create_event(self, summary, description, start_dt, duration_minutes, candidate_email, zoom_link):
        """
        Создает событие в календаре с приглашением кандидата.
        
        Создает встречу в Google Calendar с указанными параметрами,
        добавляет кандидата как участника и включает ссылку на Zoom.
        Google автоматически отправляет приглашение на email кандидата.
        
        Args:
            summary: Название события (например, "Interview: Иван Иванов")
            description: Описание события
            start_dt: Дата и время начала встречи (datetime объект)
            duration_minutes: Длительность встречи в минутах
            candidate_email: Email кандидата для приглашения
            zoom_link: Ссылка на Zoom конференцию
            
        Returns:
            str: URL события в Google Calendar (htmlLink)
            
        Note:
            Временная зона жестко задана как 'Europe/Moscow'.
            В будущих версиях рекомендуется брать из настроек пользователя.
            Напоминания: email за 24 часа, popup за 10 минут.
            
        Raises:
            Exception: При ошибках создания события в Google Calendar API
        """
        end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

        event_body = {
            'summary': summary,
            'location': zoom_link,
            'description': f"{description}\n\nСсылка на встречу: {zoom_link}",
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'Europe/Moscow',  # Лучше брать из настроек юзера
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'Europe/Moscow',
            },
            'attendees': [
                {'email': candidate_email},
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

        event = self.service.events().insert(calendarId='primary', body=event_body).execute()
        return event.get('htmlLink')