# Файл: main/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models


# 1. Пользователь
class CustomUser(AbstractUser):
    # Хранить пароль в открытом виде небезопасно, но для MVP и App Password допустимо.
    # В будущем лучше использовать шифрование.
    gmail_password = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.username


# 2. Проекты
class Project(models.Model):
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


# 3. Связь Юзер-Проект (ProjectsUsers)
class ProjectUser(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'user')  # Один юзер не может быть дважды в одном проекте
        verbose_name = "Участник проекта"
        verbose_name_plural = "Участники проектов"


# 4. Позиции (Вакансии)
class Position(models.Model):
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


# 5. Кандидаты
class Candidate(models.Model):
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
    experience = models.CharField(max_length=50, verbose_name="Опыт (лет)", blank=True)  # "3 года", "5 лет"
    experience_raw = models.TextField(verbose_name="Опыт (сырой текст)", blank=True)  # Место работы и описание
    used_technologies = models.TextField(verbose_name="Стек технологий", blank=True)
    education = models.TextField(verbose_name="Образование", blank=True)
    soft_skills = models.TextField(verbose_name="Soft Skills", blank=True)
    languages = models.CharField(max_length=255, verbose_name="Владение языками", blank=True)

    # Контакты
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Кандидат"
        verbose_name_plural = "Кандидаты"