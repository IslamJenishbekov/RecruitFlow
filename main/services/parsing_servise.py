import re

import requests
from bs4 import BeautifulSoup


class ParsingService:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def parse(self, url):
        if 'devkg' in url:
            return self.parse_devkg(url)
        elif "headhunter" in url:
            return self.parse_headhunter(url)
        return "Парсим пока что только DEVKG, HeadHunter"

    def parse_devkg(self, url):
        response = requests.get(url, headers=self.headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        text = soup.get_text().split("Похожие вакансии")[0]
        text = re.sub(r'\n+', '\n', text)
        return text

    def parse_headhunter(self, url):
        vacancy_id = url.split('/')[-1].split("?")[0]
        url = f"https://api.hh.ru/vacancies/{vacancy_id}"
        response = requests.get(url).json()
        name, description = response['name'], response['description']
        soup = BeautifulSoup(description, 'html.parser')
        description = soup.get_text(separator='\n')
        return f"{name}\n{description}"
