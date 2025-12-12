# Файл: main/models.py
"""
Модели данных для приложения RecruitFlow.

Содержит модели для:
- Пользователей с настройками интеграций
- Проектов и вакансий
- Кандидатов с резюме и транскрипциями
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    Расширенная модель пользователя с настройками интеграций.
    
    Наследуется от AbstractUser и добавляет поля для:
    - Gmail App Password (для мониторинга почты)
    - Google OAuth credentials (для Calendar API)
    - Zoom API credentials (для создания встреч)
    
    Attributes:
        gmail_password: Пароль приложения Gmail для IMAP доступа
        google_credentials: JSON с OAuth2 токенами для Google Calendar
        zoom_account_id: Zoom Account ID
        zoom_client_id: Zoom OAuth Client ID
        zoom_client_secret: Zoom OAuth Client Secret
        
    Note:
        Хранение паролей в открытом виде небезопасно для production.
        В будущих версиях рекомендуется использовать шифрование.
    """
    # Хранить пароль в открытом виде небезопасно, но для MVP и App Password допустимо.
    # В будущем лучше использовать шифрование.
    gmail_password = models.CharField(max_length=255, null=True, blank=True)
    google_credentials = models.JSONField(null=True, blank=True)
    zoom_account_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="Zoom Account ID")
    zoom_client_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="Zoom Client ID")
    zoom_client_secret = models.CharField(max_length=255, null=True, blank=True, verbose_name="Zoom Client Secret")
    telegram_bot_token = models.CharField(max_length=255, null=True, blank=True, verbose_name="Telegram Bot Token")
    telegram_bot_link = models.URLField(max_length=255, null=True, blank=True, verbose_name="Ссылка на Telegram бота")

    def __str__(self):
        return self.username


class Project(models.Model):
    """
    Модель проекта/команды.
    
    Проект объединяет вакансии и участников (пользователей).
    Один пользователь может быть в нескольких проектах.
    
    Attributes:
        name: Название проекта
        created_at: Дата создания
        updated_at: Дата последнего обновления
        users: Связь ManyToMany с пользователями через ProjectUser
        
    Relations:
        - positions: Вакансии в рамках проекта (ForeignKey)
        - users: Участники проекта (ManyToMany через ProjectUser)
    """
    name = models.CharField(max_length=200, verbose_name="Название проекта")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлен")

    # Связь с пользователями через промежуточную таблицу
    users = models.ManyToManyField(CustomUser, through='ProjectUser', related_name='projects')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"


class ProjectUser(models.Model):
    """
    Промежуточная модель для связи пользователей и проектов.
    
    Позволяет хранить дополнительную информацию о связи
    пользователя с проектом (даты присоединения и т.д.).
    
    Attributes:
        project: Связь с проектом (ForeignKey)
        user: Связь с пользователем (ForeignKey)
        created_at: Дата присоединения к проекту
        updated_at: Дата последнего обновления связи
        
    Constraints:
        unique_together: Один пользователь не может быть дважды в одном проекте
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'user')  # Один юзер не может быть дважды в одном проекте
        verbose_name = "Участник проекта"
        verbose_name_plural = "Участники проектов"


class Position(models.Model):
    """
    Модель вакансии/позиции.
    
    Представляет открытую вакансию в рамках проекта.
    Содержит требования к кандидату и связана с кандидатами.
    
    Attributes:
        project: Проект, к которому относится вакансия (ForeignKey)
        name: Название вакансии
        requirements: Текст требований к кандидату
        created_at: Дата создания
        updated_at: Дата последнего обновления
        
    Relations:
        - candidates: Кандидаты на эту позицию (ForeignKey)
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='positions', verbose_name="Проект")
    name = models.CharField(max_length=200, verbose_name="Название вакансии")
    requirements = models.TextField(verbose_name="Требования", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    class Meta:
        verbose_name = "Позиция"
        verbose_name_plural = "Позиции"


class Candidate(models.Model):
    """
    Модель кандидата.
    
    Хранит полную информацию о кандидате: данные из резюме,
    контакты, статус в процессе найма, файлы и транскрипции.
    
    Attributes:
        position: Вакансия, на которую претендует кандидат (ForeignKey)
        full_name: ФИО кандидата
        
        # Данные из резюме
        programming_language: Языки программирования
        experience: Опыт работы (текстовое описание)
        used_technologies: Стек технологий
        education: Образование
        soft_skills: Soft skills
        languages: Владение языками
        
        # Контакты
        phone_number: Номер телефона
        gmail: Email адрес
        telegram: Telegram username
        
        # HR информация
        waited_salary: Ожидаемая зарплата
        status: Текущий статус в процессе найма
        scheduled_at: Время запланированного интервью
        
        # Файлы
        cv_file: Файл резюме (PDF/DOCX)
        audio_file: Аудиозапись интервью
        
        # Результаты
        interview_transcription: Текст транскрипции интервью
        questions_answers: JSON с вопросами и ответами
        
        created_at: Дата создания записи
        updated_at: Дата последнего обновления
        
    Status Choices:
        - 'new': Новый кандидат
        - 'screening': Скрининг пройден
        - 'interview_scheduled': Интервью назначено
        - 'interview_passed': Интервью пройдено
        - 'offer': Оффер
        - 'rejected': Отказ
    """
    # Статусы кандидата
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('screening', 'Скрининг пройден'),
        ('interview_scheduled', 'Интервью назначено'),
        ('interview_passed', 'Интервью пройдено'),
        ('offer', 'Оффер'),
        ('rejected', 'Отказ'),
    ]

    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='candidates', verbose_name="Позиция")
    full_name = models.CharField(max_length=255, verbose_name="ФИО")

    # Данные из резюме
    programming_language = models.CharField(max_length=100, verbose_name="Язык программирования", blank=True)
    experience = models.CharField(max_length=500, verbose_name="Опыт (лет)", blank=True)  # "3 года", "5 лет"
    used_technologies = models.TextField(verbose_name="Стек технологий", blank=True)
    education = models.TextField(verbose_name="Образование", blank=True)
    soft_skills = models.TextField(verbose_name="Soft Skills", blank=True)
    languages = models.CharField(max_length=255, verbose_name="Владение языками", blank=True)

    # Контакты
    phone_number = models.CharField(verbose_name="Phone Number", null=True)
    gmail = models.EmailField(verbose_name="Email", blank=True, null=True)
    telegram = models.CharField(max_length=100, verbose_name="Telegram", blank=True)

    # HR инфо
    waited_salary = models.CharField(max_length=100, verbose_name="Ожидаемая ЗП", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name="Время созвона")

    # Файлы
    cv_file = models.FileField(upload_to='resumes/', null=True, blank=True, verbose_name="Файл резюме")
    audio_file = models.FileField(upload_to='interviews/', null=True, blank=True, verbose_name="Запись интервью")

    # Результаты
    interview_transcription = models.TextField(verbose_name="Транскрибация", blank=True)
    # Используем JSONField для вопросов-ответов, так как у вас Postgres
    questions_answers = models.JSONField(verbose_name="Вопросы и ответы", null=True, blank=True)
    telegram_short_interview = models.TextField(verbose_name="Текст телеграм интервью", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Кандидат"
        verbose_name_plural = "Кандидаты"


class BotInterviewSession(models.Model):
    """
    Модель сессии интервью в Telegram.
    Настройки определяют, как именно бот (AI) будет вести диалог.
    """

    # --- Варианты выбора ---
    MODE_CHOICES = [
        ('screening', 'HR Скрининг (базовый)'),
        ('hard_skills', 'Техническое интервью (Hard Skills)'),
        ('soft_skills', 'Поведенческое интервью (Soft Skills)'),
        ('mixed', 'Смешанное'),
    ]

    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]

    # --- Основные поля ---
    telegram_username = models.CharField(max_length=255, verbose_name="Telegram Username")
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='bot_sessions',
        verbose_name="Связанный кандидат"
    )

    # --- Параметры интервью ---
    interview_mode = models.CharField(
        max_length=50,
        choices=MODE_CHOICES,
        default='mixed',
        verbose_name="Тип интервью"
    )

    questions_count = models.PositiveIntegerField(
        default=5,
        verbose_name="Количество вопросов"
    )
    interview_parameters = models.TextField(verbose_name="Параметры интервью (Промпт)", blank=True)

    # Технические поля
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    chat_history = models.JSONField(default=list, verbose_name="История переписки", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"@{self.telegram_username} | {self.get_interview_mode_display()}"

    class Meta:
        verbose_name = "Сессия Telegram интервью"
        verbose_name_plural = "Сессии Telegram интервью"
        indexes = [
            models.Index(fields=['telegram_username', 'status']),
        ]

    def get_system_prompt(self):
        """
        Генерирует детальный System Prompt для AI, включая:
        1. Требования вакансии (Position).
        2. Данные кандидата (Candidate).
        3. Настройки стиля и сложности (Session settings).
        """
        # Безопасное получение данных (на случай, если поля пустые)
        position = self.candidate.position
        cand = self.candidate

        # Формируем блок требований вакансии
        requirements_text = position.requirements if position.requirements else "Требования не указаны, проверяй общие знания по названию позиции."

        # Формируем блок информации о кандидате
        candidate_info = (
            f"ФИО: {cand.full_name}\n"
            f"Опыт работы: {cand.experience or 'Не указан'}\n"
            f"Технический стек: {cand.used_technologies or 'Не указан'}\n"
            f"Языки программирования: {cand.programming_language or 'Не указан'}\n"
            f"Образование: {cand.education or 'Не указано'}\n"
            f"Soft Skills: {cand.soft_skills or 'Не указаны'}\n"
            f"Владение языками: {cand.languages or 'Не указано'}"
        )

        # Формируем сам промпт
        system_prompt = f"""
Ты — профессиональный технический рекрутер и эксперт в найме.
Твоя задача — провести {self.get_interview_mode_display()} собеседование с кандидатом.

==============================
ВАКАНСИЯ (КОГО МЫ ИЩЕМ):
Название: {position.name}
Требования к кандидату:
{requirements_text}
==============================

==============================
КАНДИДАТ (КТО ПРИШЕЛ):
{candidate_info}
==============================

==============================
ПАРАМЕТРЫ ИНТЕРВЬЮ:
Количество вопросов, которые нужно задать (ориентировочно, можно чуть больше, чуть меньше, по необходимости): {self.questions_count}
==============================

ИНСТРУКЦИЯ ПО ВЕДЕНИЮ ДИАЛОГА:
1. Поздоровайся с кандидатом по имени, представься (как AI-рекрутер компании) и кратко обозначь формат.
2. Твоя цель — проверить, соответствует ли опыт кандидата требованиям вакансии. Ищи пробелы в знаниях.
3. ЗАДАВАЙ ВОПРОСЫ СТРОГО ПО ОДНОМУ. Не отправляй список вопросов сразу.
4. Жди ответа кандидата. После получения ответа — дай краткую обратную связь (принято/хорошо/уточни) и переходи к следующему вопросу.
5. Если кандидат отвечает слишком коротко или уклончиво — задавай уточняющие вопросы (drill down).
6. Если кандидат не знает ответа — поддерживай дружелюбный тон (если выбран такой стиль) и иди дальше.
7. После того как задашь примерно {self.questions_count} основных вопросов — вежливо заверши интервью и попрощайся.

Начинай диалог с приветствия.
"""
        return system_prompt.strip()
