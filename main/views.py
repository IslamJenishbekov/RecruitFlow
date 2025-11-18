# main/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from .forms import *
from django.contrib import messages  # Для всплывающих сообщений
from .models import *
# --- АУТЕНТИФИКАЦИЯ ---

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

# --- ОСНОВНАЯ ЛОГИКА ---

@login_required
def projects(request):
    """
    Главная страница:
    1. Список проектов пользователя.
    2. Обработка формы создания нового проекта.
    """
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            # Создаем проект, но пока не сохраняем в БД окончательно,
            # хотя здесь save() сразу вернет инстанс
            new_project = form.save()

            # ВАЖНО: Привязываем текущего пользователя к проекту
            # Так как у нас ManyToMany через ProjectUser, метод .add()
            # сработает, потому что в ProjectUser нет обязательных дополнительных полей,
            # кроме автоматических дат.
            new_project.users.add(request.user)

            return redirect('home')
    else:
        form = ProjectForm()

    # Получаем проекты, связанные с текущим пользователем
    # Используем related_name='projects', указанный в модели CustomUser (через M2M)
    # Или, так как в Project models.py related_name='projects' стоит у поля users:
    user_projects = request.user.projects.all().order_by('-created_at')

    context = {
        'projects': user_projects,
        'form': form
    }
    return render(request, 'main/projects.html', context)
@login_required
def profile(request):
    """Страница профиля"""
    return render(request, 'main/profile.html')

@login_required
def project_detail(request, project_id):
    """Страница проекта: показывает список позиций"""
    # Логика в будущем:
    # project = get_object_or_404(Project, id=project_id)
    # positions = project.positions_set.all()
    return render(request, 'main/positions.html', {'project_id': project_id})

@login_required
def position_detail(request, position_id):
    """Страница позиции: показывает таблицу кандидатов"""
    # Логика в будущем:
    # position = get_object_or_404(Position, id=position_id)
    # candidates = position.candidates_set.all()
    return render(request, 'main/candidates.html', {'position_id': position_id})

@login_required
def candidate_detail(request, candidate_id):
    """Страница анкеты кандидата"""
    # Логика в будущем:
    # candidate = get_object_or_404(Candidate, id=candidate_id)
    return render(request, 'main/candidate_detail.html', {'candidate_id': candidate_id})


@login_required
@require_POST  # Разрешаем только POST запросы (безопасность)
def delete_project(request, project_id):
    # Ищем проект, который принадлежит текущему пользователю
    project = get_object_or_404(Project, id=project_id, users=request.user)

    # Удаляем
    project_name = project.name
    project.delete()

    # Добавляем сообщение об успехе (покажется в base.html)
    messages.success(request, f'Проект "{project_name}" успешно удален.')

    return redirect('home')


@login_required
@require_POST
def add_user_to_project(request, project_id):
    project = get_object_or_404(Project, id=project_id, users=request.user)
    username = request.POST.get('username')
    User = get_user_model()

    try:
        user_to_add = User.objects.get(username=username)

        if user_to_add in project.users.all():
            messages.warning(request, f'Пользователь {username} уже есть в проекте.')
        else:
            project.users.add(user_to_add)
            messages.success(request, f'Пользователь {username} добавлен в проект.')

    except User.DoesNotExist:
        messages.error(request, f'Пользователь с ником "{username}" не найден.')

    return redirect('home')