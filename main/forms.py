from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import *


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email') # Укажите поля, которые будут на форме регистрации

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email') # Поля, которые можно редактировать в админке

class ProjectForm(forms.ModelForm):
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
    class Meta:
        model = CustomUser
        fields = ['email', 'gmail_password'] # Добавили email
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'name@company.com'
            }),
            'gmail_password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите новый пароль (если хотите изменить)',
                'autocomplete': 'new-password'
            })
        }
        labels = {
            'email': 'Служебная почта',
            'gmail_password': 'Gmail App Password'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем поле email обязательным (в AbstractUser оно может быть blank=True)
        self.fields['email'].required = True
        # Делаем поле пароля необязательным, чтобы можно было сохранить email, не меняя пароль
        self.fields['gmail_password'].required = False


class CandidateUploadForm(forms.Form):
    cv_file = forms.FileField(
        label="Файл резюме",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.docx' # Ограничиваем выбор файлов
        })
    )

class CandidateAudioForm(forms.ModelForm):
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