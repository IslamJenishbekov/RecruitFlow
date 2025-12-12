"""
Django формы для приложения RecruitFlow.

Содержит формы для:
- Регистрации и редактирования пользователей
- Создания проектов и вакансий
- Настройки профиля с интеграциями
- Загрузки резюме и аудио
"""
from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
import json
from django.contrib.auth import get_user_model
from .models import *

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """
    Форма для регистрации нового пользователя.
    
    Расширяет стандартную форму UserCreationForm для работы
    с моделью CustomUser.
    
    Fields:
        username: Имя пользователя
        email: Email адрес
    """

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email')  # Укажите поля, которые будут на форме регистрации


class CustomUserChangeForm(UserChangeForm):
    """
    Форма для редактирования пользователя в админке.
    
    Fields:
        username: Имя пользователя
        email: Email адрес
    """

    class Meta:
        model = CustomUser
        fields = ('username', 'email')


class ProjectForm(forms.ModelForm):
    """
    Форма для создания нового проекта.
    
    Fields:
        name: Название проекта
        
    Widgets:
        name: TextInput с классом 'form-control' и placeholder
    """

    class Meta:
        model = Project
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Поиск Python разработчика'
            })
        }


class PositionForm(forms.ModelForm):
    """
    Форма для создания новой вакансии/позиции.
    
    Fields:
        name: Название вакансии
        requirements: Требования к кандидату
        
    Widgets:
        name: TextInput с классом 'form-control' и placeholder
        requirements: Textarea с 5 строками и placeholder
    """

    class Meta:
        model = Position
        fields = ['name', 'requirements']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Senior Python Developer'
            }),
            'requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Опишите требования, стек технологий и условия...'
            }),
        }


class ProfileSettingsForm(forms.ModelForm):
    """
    Форма для настройки профиля пользователя с интеграциями.
    
    Позволяет настроить:
    - Email и Gmail App Password
    - Zoom API credentials
    - Google OAuth credentials (через загрузку JSON файла)
    
    Fields:
        email: Служебная почта
        gmail_password: Gmail App Password для IMAP
        zoom_account_id: Zoom Account ID
        zoom_client_id: Zoom Client ID
        zoom_client_secret: Zoom Client Secret
        credentials_file: JSON файл с Google OAuth credentials
        
    Note:
        credentials_file - виртуальное поле, не сохраняется в БД,
        а парсится и сохраняется в google_credentials как JSON.
    """
    # Поле для файла Google Credentials (виртуальное)
    credentials_file = forms.FileField(
        required=False,
        label="Файл credentials.json",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.json'
        })
    )

    class Meta:
        model = CustomUser
        fields = [
            'email', 'gmail_password',
            'zoom_account_id', 'zoom_client_id', 'zoom_client_secret',
            'telegram_bot_token', 'telegram_bot_link'
        ]

        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'gmail_password': forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),

            # Zoom Widgets
            'zoom_account_id': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Например: abc123XYZ...'}),
            'zoom_client_id': forms.TextInput(attrs={'class': 'form-control'}),
            'zoom_client_secret': forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),

            'telegram_bot_token': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '123456789:ABCdef-_Gw...'
            }),
            'telegram_bot_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://t.me/MyBot'
            }),
        }
        labels = {
            'email': 'Служебная почта',
            'gmail_password': 'Gmail App Password',
            'zoom_account_id': 'Zoom Account ID',
            'zoom_client_id': 'Zoom Client ID',
            'zoom_client_secret': 'Zoom Client Secret',
            'telegram_bot_token': 'Token бота (от BotFather)',
            'telegram_bot_link': 'Ссылка на бота',
        }

    def clean_credentials_file(self):
        """
        Валидирует загруженный JSON файл с Google credentials.
        
        Returns:
            dict: Распарсенный JSON из файла
            
        Raises:
            ValidationError: Если файл не является валидным JSON
        """
        file = self.cleaned_data.get('credentials_file')
        if file:
            try:
                data = json.load(file)
                return data
            except json.JSONDecodeError:
                raise forms.ValidationError("Ошибка чтения файла. Убедитесь, что это корректный JSON.")
        return None

    def save(self, commit=True):
        """
        Сохраняет форму и обновляет google_credentials из файла.
        
        Args:
            commit: Если True, сохраняет объект в БД
            
        Returns:
            CustomUser: Сохраненный объект пользователя
        """
        user = super().save(commit=False)
        json_data = self.cleaned_data.get('credentials_file')
        if json_data:
            user.google_credentials = json_data

        if commit:
            user.save()
        return user


class CandidateUploadForm(forms.Form):
    """
    Форма для загрузки файла резюме кандидата.
    
    Fields:
        cv_file: Файл резюме (PDF или DOCX)
        
    Validation:
        Принимает только файлы с расширениями .pdf и .docx
    """
    cv_file = forms.FileField(
        label="Файл резюме",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.docx'  # Ограничиваем выбор файлов
        })
    )


class CandidateAudioForm(forms.ModelForm):
    """
    Форма для загрузки аудиозаписи интервью кандидата.
    
    Fields:
        audio_file: Аудиофайл с записью интервью
        
    Validation:
        Принимает только аудиофайлы (audio/*)
    """

    class Meta:
        model = Candidate
        fields = ['audio_file']
        widgets = {
            'audio_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'audio/*',  # Разрешаем только аудиофайлы
                'id': 'audioInput'
            })
        }


class BotInterviewSetupForm(forms.ModelForm):
    """
    Форма для настройки параметров AI-интервью.
    """

    class Meta:
        model = BotInterviewSession
        fields = ['interview_mode', 'questions_count']

        widgets = {
            'interview_mode': forms.Select(attrs={'class': 'form-select'}),
            'questions_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20})
        }
        labels = {
            'interview_mode': 'Тип интервью',
            'questions_count': 'Количество вопросов'
        }
