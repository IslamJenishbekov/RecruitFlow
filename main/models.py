from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # Добавьте свои поля здесь, например:
    # age = models.PositiveIntegerField(null=True, blank=True)
    pass

    def __str__(self):
        return self.username