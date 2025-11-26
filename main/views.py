# main/views.py

import logging

from django.contrib import messages  # Для всплывающих сообщений
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import *
from .models import *
from .services import llm_service, mail_service, parsing_servise, audio_processing
from .repository import candidate

logger = logging.getLogger(__name__)
parser_service = parsing_servise.ParsingService()

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
    user = request.user

    # Статистика
    projects_count = user.projects.count()
    positions_count = Position.objects.filter(project__users=user).count()

    # Обработка формы
    if request.method == 'POST':
        form = ProfileSettingsForm(request.POST, instance=user)
        if form.is_valid():
            # Логика сохранения:
            # Если поле пароля пустое, Django ModelForm по умолчанию не трогает его,
            # если оно не было изменено. Но так как мы используем виджет PasswordInput
            # и render_value=False (по умолчанию), поле приходит пустым.

            # Нюанс: если юзер оставил поле пароля пустым, мы не хотим затирать старый пароль пустым значением.
            # ModelForm обычно справляется, но для надежности проверим:

            if not form.cleaned_data.get('gmail_password'):
                # Если пароль не введен, исключаем его из обновления
                user.email = form.cleaned_data['email']
                user.save()
            else:
                # Если введен, сохраняем всё
                form.save()

            messages.success(request, 'Настройки профиля обновлены.')
            return redirect('profile')
    else:
        form = ProfileSettingsForm(instance=user)

    context = {
        'user': user,
        'projects_count': projects_count,
        'positions_count': positions_count,
        'form': form
    }
    return render(request, 'main/profile.html', context)


@login_required
def project_detail(request, project_id):
    # 1. Получаем проект, проверяя доступ (user входит в project.users)
    project = get_object_or_404(Project, id=project_id, users=request.user)

    # 2. Обработка создания новой позиции
    if request.method == 'POST':
        form = PositionForm(request.POST)
        if form.is_valid():
            position = form.save(commit=False)
            position.project = project  # Привязываем позицию к текущему проекту
            position.save()
            messages.success(request, f'Позиция "{position.name}" успешно создана.')
            return redirect('project_detail', project_id=project.id)
    else:
        form = PositionForm()

    # 3. Получаем список позиций с подсчетом кандидатов
    # annotate(candidates_count=Count('candidates')) создает виртуальное поле с числом
    positions = project.positions.all().annotate(candidates_count=Count('candidates')).order_by('-created_at')

    context = {
        'project': project,
        'positions': positions,
        'form': form
    }
    return render(request, 'main/positions.html', context)  # Обратите внимание на имя шаблона


@login_required
@require_POST
def delete_position(request, position_id):
    # Ищем позицию, но также проверяем, что юзер имеет доступ к проекту этой позиции
    position = get_object_or_404(Position, id=position_id, project__users=request.user)
    project_id = position.project.id
    position_name = position.name

    position.delete()

    messages.success(request, f'Позиция "{position_name}" удалена.')
    return redirect('project_detail', project_id=project_id)


@login_required
def position_detail(request, position_id):
    position = get_object_or_404(Position, id=position_id, project__users=request.user)

    if request.method == 'POST':
        form = CandidateUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['cv_file']
            candidate.CandidateOperations.create_candidate_from_single_document(uploaded_file, position)
            messages.success(request, "Кандидат успешно добавлен!")
            return redirect('position_detail', position_id=position.id)
    else:
        form = CandidateUploadForm()

    candidates = position.candidates.all().order_by('-created_at')

    context = {
        'position': position,
        'candidates': candidates,
        'form': form,
        'project': position.project
    }
    return render(request, 'main/candidates.html', context)


@login_required
def candidate_detail(request, candidate_id):
    # 1. Получаем кандидата с проверкой прав (через позицию и проект)
    candidate = get_object_or_404(
        Candidate,
        id=candidate_id,
        position__project__users=request.user
    )

    # 2. Обработка загрузки аудио
    if request.method == 'POST':
        form = CandidateAudioForm(request.POST, request.FILES, instance=candidate)
        if form.is_valid():
            # Сначала сохраняем файл физически
            candidate = form.save()

            try:
                # Запускаем логику транскрибации
                # Важно: audio_file.path дает полный путь к файлу на диске
                if candidate.audio_file:
                    file_path = candidate.audio_file.path

                    # Вызываем ваш сервис
                    transcription_text = audio_processing.get_transcription(file_path)

                    # Сохраняем результат
                    candidate.interview_transcription = transcription_text
                    candidate.status = 'interview_passed'  # Можно авто-менять статус
                    candidate.save()

                    messages.success(request, "Аудио загружено и успешно расшифровано!")
            except Exception as e:
                messages.error(request, f"Ошибка при транскрибации: {e}")

            # PRG Pattern
            return redirect('candidate_detail', candidate_id=candidate.id)
    else:
        form = CandidateAudioForm(instance=candidate)

    context = {
        'candidate': candidate,
        'form': form,
        'project': candidate.position.project  # Для хлебных крошек
    }
    return render(request, 'main/candidate_detail.html', context)

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


@login_required
@require_POST
def import_requirements_from_url(request, position_id):
    position = get_object_or_404(Position, id=position_id, project__users=request.user)

    url = request.POST.get('target_url')

    if not url:
        messages.error(request, "URL не был передан.")
        return redirect('project_detail', project_id=position.project.id)


    text = parser_service.parse(url)
    logger.info(text)
    position.requirements = text
    position.save()

    messages.success(request, f"Требования успешно импортированы с сайта.")

    return redirect('project_detail', project_id=position.project.id)
