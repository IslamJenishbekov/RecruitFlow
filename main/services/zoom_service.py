# main/services/zoom_service.py
"""
Сервис для работы с Zoom API.

Предоставляет функциональность для создания видеоконференций
через Zoom API с использованием OAuth2 авторизации.
"""
import requests
import base64


class ZoomService:
    """
    Сервис для создания Zoom встреч через API.
    
    Использует OAuth2 авторизацию через Account Credentials Grant
    для получения access token и создания запланированных встреч.
    
    Attributes:
        account_id: Zoom Account ID
        client_id: Zoom OAuth Client ID
        client_secret: Zoom OAuth Client Secret
        base_url: Базовый URL Zoom API
    """
    def __init__(self, account_id, client_id, client_secret):
        """
        Инициализирует сервис Zoom с учетными данными.
        
        Args:
            account_id: Zoom Account ID
            client_id: Zoom OAuth Client ID
            client_secret: Zoom OAuth Client Secret
        """
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.zoom.us/v2"

    def _get_access_token(self):
        """
        Получает OAuth2 access token для Zoom API.
        
        Использует Account Credentials Grant для получения токена.
        
        Returns:
            str: Access token для использования в API запросах
            
        Raises:
            Exception: При ошибках получения токена (неверные credentials,
                     проблемы с сетью и т.д.)
        """
        url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={self.account_id}"
        auth_str = f"{self.client_id}:{self.client_secret}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()

        headers = {
            "Authorization": f"Basic {b64_auth}"
        }

        response = requests.post(url, headers=headers)
        return response.json().get("access_token")

    def create_meeting(self, topic, start_time_iso, duration_minutes):
        """
        Создает запланированную Zoom встречу.
        
        Создает новую видеоконференцию с указанными параметрами
        и возвращает ссылку для присоединения.
        
        Args:
            topic: Тема встречи (например, "Interview: Иван Иванов")
            start_time_iso: Время начала в формате ISO (YYYY-MM-DDTHH:mm:ss)
            duration_minutes: Длительность встречи в минутах
            
        Returns:
            str: Ссылка для присоединения к встрече (join_url)
            
        Settings:
            - host_video: True (видео хоста включено)
            - participant_video: True (видео участников включено)
            - join_before_host: False (участники не могут присоединиться до хоста)
            - mute_upon_entry: True (участники заходят с выключенным микрофоном)
            - timezone: "Europe/Moscow"
            
        Raises:
            Exception: При ошибках создания встречи (неверные параметры,
                     проблемы с API, превышение лимитов и т.д.)
        """
        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "topic": topic,
            "type": 2,  # Scheduled meeting
            "start_time": start_time_iso,  # Format: yyyy-MM-ddTHH:mm:ss
            "duration": duration_minutes,
            "timezone": "Europe/Moscow",
            "settings": {
                "host_video": True,
                "participant_video": True,
                "join_before_host": False,
                "mute_upon_entry": True
            }
        }

        response = requests.post(
            f"{self.base_url}/users/me/meetings",
            headers=headers,
            json=payload
        )

        if response.status_code == 201:
            return response.json().get("join_url")
        else:
            raise Exception(f"Zoom creation failed: {response.text}")