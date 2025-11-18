from django.urls import path
from . import views  # Импортируем представления из текущего приложения

urlpatterns = [
    path('', views.index, name='myapp-index'),
]