from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, Project
from django import forms

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