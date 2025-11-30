"""
Сервис для парсинга вакансий с различных сайтов.

Поддерживает парсинг требований к вакансиям с:
- DEVKG (devkg.com)
- HeadHunter (hh.ru)
"""
import re

import requests
from bs4 import BeautifulSoup


class ParsingService:
    """
    Сервис для парсинга описаний вакансий с внешних сайтов.
    
    Извлекает текст требований и описания вакансий для последующего
    использования при оценке релевантности кандидатов.
    """
    def __init__(self):
        """
        Инициализирует сервис парсинга.
        
        Устанавливает User-Agent для HTTP запросов, чтобы избежать блокировок.
        """
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def parse(self, url):
        """
        Парсит вакансию по URL, определяя сайт автоматически.
        
        Определяет тип сайта по URL и вызывает соответствующий парсер.
        
        Args:
            url: URL страницы вакансии
            
        Returns:
            str: Извлеченный текст описания и требований вакансии.
                 Сообщение об ошибке, если сайт не поддерживается.
                 
        Supported sites:
            - devkg.com: Парсинг через BeautifulSoup
            - hh.ru: Парсинг через HeadHunter API
            
        Note:
            Если сайт не поддерживается, возвращается сообщение об этом.
        """
        if 'devkg' in url:
            return self.parse_devkg(url)
        elif "headhunter" in url:
            return self.parse_headhunter(url)
        return "Парсим пока что только DEVKG, HeadHunter"

    def parse_devkg(self, url):
        """
        Парсит вакансию с сайта DEVKG (devkg.com).
        
        Извлекает текст описания вакансии до блока "Похожие вакансии".
        
        Args:
            url: URL страницы вакансии на DEVKG
            
        Returns:
            str: Очищенный текст описания вакансии (без лишних переносов строк)
            
        Raises:
            requests.RequestException: При ошибках HTTP запроса
            Exception: При ошибках парсинга HTML
        """
        response = requests.get(url, headers=self.headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        text = soup.get_text().split("Похожие вакансии")[0]
        text = re.sub(r'\n+', '\n', text)
        return text

    def parse_headhunter(self, url):
        """
        Парсит вакансию с сайта HeadHunter (hh.ru).
        
        Использует HeadHunter API для получения данных вакансии,
        извлекает название и описание, очищает HTML теги.
        
        Args:
            url: URL страницы вакансии на HeadHunter
            
        Returns:
            str: Название вакансии и очищенное описание, разделенные переносом строки
            
        Raises:
            requests.RequestException: При ошибках HTTP запроса к API
            KeyError: Если API вернул неожиданную структуру данных
            Exception: При ошибках парсинга HTML описания
        """
        vacancy_id = url.split('/')[-1].split("?")[0]
        url = f"https://api.hh.ru/vacancies/{vacancy_id}"
        response = requests.get(url).json()
        name, description = response['name'], response['description']
        soup = BeautifulSoup(description, 'html.parser')
        description = soup.get_text(separator='\n')
        return f"{name}\n{description}"
