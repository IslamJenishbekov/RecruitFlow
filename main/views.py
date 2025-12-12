# main/views.py
"""
Django views для приложения RecruitFlow.

Содержит представления для:
- Аутентификации и регистрации
- Управления проектами и вакансиями
- Работы с кандидатами
- Настройки профиля и интеграций
- OAuth авторизации для Google Calendar
"""
import datetime
import logging
import threading
import os
from functools import wraps
from google_auth_oauthlib.flow import Flow
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db import close_old_connections, connection
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.conf import settings
from .services.zoom_service import ZoomService
from .services.calendar_service import GoogleCalendarService
from django.http import HttpResponseBadRequest
from django.db import transaction
from .forms import *
from .models import *
from .services import llm_service, mail_service, parsing_servise, audio_processing
from .repository import candidate

REDIRECT_URI = 'http://127.0.0.1:8000/oauth2callback'

logger = logging.getLogger(__name__)
parser_service = parsing_servise.ParsingService()


def restrict_test_user(view_func):
    """
    Декоратор для ограничения действий тестовых пользователей.
    
    Блокирует выполнение действия, если логин пользователя начинается с "test_user".
    Показывает сообщение с просьбой войти со своего аккаунта.
    
    Args:
        view_func: Функция представления для обертки
        
    Returns:
        Обернутая функция с проверкой тестового пользователя
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.username.startswith('test_user'):
            messages.warning(
                request,
                'Чтобы создать свой проект, вам надо зайти со своего аккаунта.'
            )
            # Редиректим на предыдущую страницу или главную
            return redirect(request.META.get('HTTP_REFERER', 'home'))
        return view_func(request, *args, **kwargs)

    return wrapper


def signup(request):
    """
    Представление для регистрации нового пользователя.
    
    GET: Отображает форму регистрации
    POST: Обрабатывает форму и создает нового пользователя
    
    Returns:
        HttpResponse: Страница регистрации или редирект на страницу входа
    """
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
        # Проверка для тестовых пользователей
        if request.user.username.startswith('test_user'):
            messages.warning(
                request,
                'Чтобы создать свой проект, вам надо зайти со своего аккаунта.'
            )
            return redirect('home')

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
    """
    Представление для страницы профиля пользователя.
    
    Отображает статистику (количество проектов и вакансий) и форму
    для настройки интеграций (Gmail, Zoom, Google Calendar).
    
    GET: Отображает форму с текущими настройками
    POST: Сохраняет обновленные настройки профиля
    
    Returns:
        HttpResponse: Страница профиля с формой настроек
    """
    user = request.user

    # Сбор статистики для левой колонки
    # (Предполагаем, что related_name в модели ProjectUser настроен или фильтруем напрямую)
    projects_count = Project.objects.filter(projectuser__user=user).count()

    # Считаем количество вакансий во всех проектах пользователя
    positions_count = Position.objects.filter(project__projectuser__user=user).count()

    if request.method == 'POST':
        # Важно: request.FILES обязателен для загрузки файлов
        form = ProfileSettingsForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки профиля успешно обновлены!')
            return redirect('profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = ProfileSettingsForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'projects_count': projects_count,
        'positions_count': positions_count,
    }
    return render(request, 'main/profile.html', context)


@login_required
def project_detail(request, project_id):
    """
    Представление для детальной страницы проекта.
    
    Отображает список вакансий в проекте с количеством кандидатов
    и форму для создания новой вакансии.
    
    Args:
        project_id: ID проекта
        
    GET: Отображает список вакансий и форму создания
    POST: Создает новую вакансию в проекте
    
    Returns:
        HttpResponse: Страница проекта с вакансиями
        
    Raises:
        Http404: Если проект не найден или пользователь не имеет доступа
    """
    # 1. Получаем проект, проверяя доступ (user входит в project.users)
    project = get_object_or_404(Project, id=project_id, users=request.user)

    # 2. Обработка создания новой позиции
    if request.method == 'POST':
        # Проверка для тестовых пользователей
        if request.user.username.startswith('test_user'):
            messages.warning(
                request,
                'Чтобы создать свой проект, вам надо зайти со своего аккаунта.'
            )
            return redirect('project_detail', project_id=project.id)

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
@restrict_test_user
def delete_position(request, position_id):
    """
    Удаляет вакансию из проекта.
    
    Args:
        position_id: ID вакансии для удаления
        
    Returns:
        HttpResponse: Редирект на страницу проекта
        
    Raises:
        Http404: Если вакансия не найдена или пользователь не имеет доступа
    """
    # Ищем позицию, но также проверяем, что юзер имеет доступ к проекту этой позиции
    position = get_object_or_404(Position, id=position_id, project__users=request.user)
    project_id = position.project.id
    position_name = position.name

    position.delete()

    messages.success(request, f'Позиция "{position_name}" удалена.')
    return redirect('project_detail', project_id=project_id)


@login_required
def position_detail(request, position_id):
    """
    Представление для детальной страницы вакансии.
    
    Отображает список кандидатов на вакансию и форму для
    загрузки резюме нового кандидата.
    
    Args:
        position_id: ID вакансии
        
    GET: Отображает список кандидатов и форму загрузки
    POST: Создает нового кандидата из загруженного файла резюме
    
    Returns:
        HttpResponse: Страница вакансии с кандидатами
        
    Raises:
        Http404: Если вакансия не найдена или пользователь не имеет доступа
    """
    position = get_object_or_404(Position, id=position_id, project__users=request.user)

    if request.method == 'POST':
        # Проверка для тестовых пользователей
        if request.user.username.startswith('test_user'):
            messages.warning(
                request,
                'Чтобы создать свой проект, вам надо зайти со своего аккаунта.'
            )
            return redirect('position_detail', position_id=position.id)

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
    """
    Представление для детальной страницы кандидата.
    
    Отображает полную информацию о кандидате, резюме, транскрипции
    и форму для загрузки аудиозаписи интервью.
    
    Args:
        candidate_id: ID кандидата
        
    GET: Отображает информацию о кандидате и форму загрузки аудио
    POST: Обрабатывает загруженное аудио, выполняет транскрибацию
          и обновляет статус кандидата
    
    Process:
        При загрузке аудио:
        1. Сохраняет файл
        2. Выполняет транскрибацию через audio_processing
        3. Сохраняет транскрипцию в БД
        4. Обновляет статус на 'interview_passed'
    
    Returns:
        HttpResponse: Страница кандидата
        
    Raises:
        Http404: Если кандидат не найден или пользователь не имеет доступа
    """
    # 1. Получаем кандидата с проверкой прав (через позицию и проект)
    candidate = get_object_or_404(
        Candidate,
        id=candidate_id,
        position__project__users=request.user
    )

    # 2. Обработка загрузки аудио
    if request.method == 'POST':
        # Проверка для тестовых пользователей
        if request.user.username.startswith('test_user'):
            messages.warning(
                request,
                'Чтобы создать свой проект, вам надо зайти со своего аккаунта.'
            )
            return redirect('candidate_detail', candidate_id=candidate.id)

        form = CandidateAudioForm(request.POST, request.FILES, instance=candidate)
        if form.is_valid():
            # 1. Сохраняем файл физически и ставим статус "В обработке"
            candidate = form.save(commit=False)
            candidate.status = 'processing'  # Добавьте этот статус в модели, если его нет
            candidate.save()

            messages.success(request,
                             "Аудио загружено. Расшифровка началась в фоне (займет 3-10 минут). Обновите страницу позже.")

            # --- ФУНКЦИЯ ДЛЯ ФОНОВОГО ПОТОКА ---
            def background_transcription_task(cand_id, file_path):
                logger.info(f"THREAD: Запуск фоновой задачи для кандидата {cand_id}")

                # ВАЖНО: В начале потока закрываем "старые" соединения, 
                # чтобы поток гарантированно создал свое собственное.
                close_old_connections()

                try:
                    # 1. Тяжелая транскрибация (CPU bound)
                    logger.info(f"THREAD: Старт транскрибации для {cand_id}...")
                    #transcription_text = audio_processing.get_transcription(file_path)
                    transcription_text = """По причине того что pytorch модели (применяемые для транскрибации и диаризации)
                    # требует больше ресурсов на сервере,
                    # и бесплатные лимиты быстро исчерпываются,
                    # данная функция временно выключена ( 02.12.2025 19:12 )
                    # """

                    logger.info(
                        f"THREAD: Транскрибация завершена для {cand_id}. Длина текста: {len(str(transcription_text))}")

                    # 2. LLM (Network bound)
                    extracted_salary = None
                    if transcription_text:
                        try:
                            llm_service_instance = llm_service.GeminiService()
                            extracted_salary = llm_service_instance.extract_salary_from_transcription(
                                transcription_text)
                            logger.info(f"THREAD: Зарплата извлечена для {cand_id}: {extracted_salary}")
                        except Exception as e_llm:
                            logger.error(f"THREAD: Ошибка LLM для {cand_id}: {e_llm}")

                    # 3. Сохранение в БД
                    # ВАЖНО: Снова закрываем соединения перед работой с БД, если операция была долгой
                    close_old_connections()

                    # Получаем свежий объект из БД (внутри своего потока)
                    cand_fresh = Candidate.objects.get(id=cand_id)

                    cand_fresh.interview_transcription = transcription_text
                    if extracted_salary:
                        cand_fresh.waited_salary = extracted_salary

                    cand_fresh.status = 'interview_passed'
                    cand_fresh.save()

                    logger.info(f"THREAD: Успешно сохранено для кандидата {cand_id}")

                except Exception as e:
                    logger.error(f"THREAD: Критическая ошибка для {cand_id}: {e}")
                    logger.error(traceback.format_exc())

                    # Пытаемся записать ошибку в статус
                    try:
                        close_old_connections()
                        cand_fail = Candidate.objects.get(id=cand_id)
                        cand_fail.status = 'failed'  # Или любой статус ошибки
                        # Можно записать ошибку в поле транскрипции, чтобы видеть её в админке
                        # cand_fail.interview_transcription = f"Ошибка обработки: {str(e)}" 
                        cand_fail.save()
                    except:
                        pass  # Если даже тут упало, просто выходим

                finally:
                    # Всегда закрываем соединение при выходе из потока
                    close_old_connections()

            # --- ЗАПУСК ПОТОКА ---
            # Передаем ID и Путь (строки), а не сам объект Django, чтобы избежать проблем с потоками
            file_path_str = candidate.audio_file.path

            thread = threading.Thread(
                target=background_transcription_task,
                args=(candidate.id, file_path_str),
                daemon=True  # Daemon значит, что поток не заблокирует выключение сервера
            )
            thread.start()

            return redirect('candidate_detail', candidate_id=candidate.id)
    else:
        form = CandidateAudioForm(instance=candidate)
    interview_form = BotInterviewSetupForm()
    context = {
        'candidate': candidate,
        'form': form,
        'project': candidate.position.project,  # Для хлебных крошек
        'interview_form': interview_form,
    }
    return render(request, 'main/candidate_detail.html', context)


@login_required
@require_POST
@restrict_test_user
def delete_project(request, project_id):
    """
    Удаляет проект.
    
    Args:
        project_id: ID проекта для удаления
        
    Returns:
        HttpResponse: Редирект на главную страницу
        
    Raises:
        Http404: Если проект не найден или пользователь не имеет доступа
        
    Note:
        При удалении проекта каскадно удаляются все связанные вакансии и кандидаты.
    """
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
@restrict_test_user
def add_user_to_project(request, project_id):
    """
    Добавляет пользователя в проект.
    
    Args:
        project_id: ID проекта
        username: Имя пользователя из POST данных
        
    Returns:
        HttpResponse: Редирект на главную страницу
        
    Raises:
        Http404: Если проект не найден или пользователь не имеет доступа
        
    Note:
        Показывает предупреждение, если пользователь уже в проекте.
        Показывает ошибку, если пользователь не найден.
    """
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
@restrict_test_user
def import_requirements_from_url(request, position_id):
    """
    Импортирует требования к вакансии с внешнего сайта.
    
    Парсит описание вакансии с указанного URL и сохраняет
    в поле requirements позиции.
    
    Args:
        position_id: ID вакансии
        target_url: URL страницы вакансии из POST данных
        
    Supported sites:
        - devkg.com
        - hh.ru (HeadHunter)
        
    Returns:
        HttpResponse: Редирект на страницу проекта
        
    Raises:
        Http404: Если вакансия не найдена или пользователь не имеет доступа
    """
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


@login_required
@require_POST
@restrict_test_user
def schedule_interviews(request):
    """
    Массовое планирование интервью для выбранных кандидатов.
    
    Для каждого выбранного кандидата:
    1. Ищет свободный слот в Google Calendar
    2. Создает Zoom встречу
    3. Создает событие в Google Calendar с приглашением кандидата
    4. Обновляет статус кандидата на 'interview_scheduled'
    
    Args:
        candidate_ids: Список ID кандидатов из POST данных
        
    Requirements:
        - Настроен Google Calendar (google_credentials)
        - Настроен Zoom (zoom_account_id, zoom_client_id, zoom_client_secret)
        
    Returns:
        HttpResponse: Редирект на предыдущую страницу
        
    Note:
        Ищет свободные слоты в течение 2 недель вперед.
        Показывает количество успешно запланированных интервью и ошибки.
    """
    candidate_ids = request.POST.getlist('candidate_ids')
    user = request.user

    if not candidate_ids:
        messages.warning(request, "Не выбрано ни одного кандидата.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # 1. Проверка Google
    if not user.google_credentials:
        messages.error(request, "Ошибка: Не подключен Google Calendar. Загрузите credentials в профиле.")
        return redirect('profile')

        # 2. Проверка Zoom (Теперь проверяем поля модели)
    if not all([user.zoom_account_id, user.zoom_client_id, user.zoom_client_secret]):
        messages.error(request, "Ошибка: Не настроен Zoom. Введите ключи API в профиле.")
        return redirect('profile')

    # 3. Инициализация сервисов
    try:
        # Берем настройки Zoom из пользователя!
        zoom_service = ZoomService(
            account_id=user.zoom_account_id,
            client_id=user.zoom_client_id,
            client_secret=user.zoom_client_secret
        )

        google_service = GoogleCalendarService(user.google_credentials)

    except Exception as e:
        logger.error(f"Service Init Error: {e}")
        messages.error(request, f"Ошибка авторизации в сервисах: {e}")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # ... Дальше логика поиска слотов и создания встреч остается прежней ...
    success_count = 0
    errors = []

    current_search_date = datetime.date.today() + datetime.timedelta(days=1)
    available_slots_cache = []

    for c_id in candidate_ids:
        try:
            candidate = Candidate.objects.get(id=c_id, position__project__users=user)

            if not candidate.gmail:
                errors.append(f"{candidate.full_name}: нет Email")
                continue

            if candidate.status == 'interview_scheduled':
                errors.append(f"{candidate.full_name}: уже назначено")
                continue

            # Поиск слотов (Google)
            attempts = 0
            while not available_slots_cache and attempts < 14:
                available_slots_cache = google_service.get_free_slots(current_search_date)
                if not available_slots_cache:
                    current_search_date += datetime.timedelta(days=1)
                    attempts += 1

            if not available_slots_cache:
                errors.append(f"{candidate.full_name}: Нет слотов (2 недели)")
                continue

            best_slot = available_slots_cache.pop(0)

            # Создание Zoom (Zoom)
            zoom_link = zoom_service.create_meeting(
                topic=f"Interview: {candidate.full_name}",
                start_time_iso=best_slot.strftime('%Y-%m-%dT%H:%M:%S'),
                duration_minutes=45
            )

            # Создание Календаря (Google)
            google_service.create_event(
                summary=f"Interview: {candidate.full_name}",
                description=f"Candidate: {candidate.full_name}\nPosition: {candidate.position.name}",
                start_dt=best_slot,
                duration_minutes=45,
                candidate_email=candidate.gmail,
                zoom_link=zoom_link
            )

            candidate.status = 'interview_scheduled'
            candidate.scheduled_at = best_slot
            if not candidate.questions_answers: candidate.questions_answers = {}
            candidate.questions_answers['zoom_link'] = zoom_link
            candidate.save()

            success_count += 1

        except Candidate.DoesNotExist:
            continue
        except Exception as e:
            logger.error(f"Error processing {c_id}: {e}")
            errors.append(f"{candidate.full_name}: {str(e)}")

    if success_count > 0:
        messages.success(request, f"Запланировано: {success_count}")
    if errors:
        messages.warning(request, f"Ошибки: {'; '.join(errors[:3])}")

    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def start_google_auth(request):
    """
    Начинает процесс OAuth2 авторизации для Google Calendar.
    
    Шаг 1: Создает OAuth Flow с загруженными credentials пользователя
    и перенаправляет на страницу авторизации Google.
    
    Requirements:
        - Пользователь должен загрузить credentials.json в профиле
        
    Returns:
        HttpResponse: Редирект на страницу авторизации Google
        
    Raises:
        Redirect: На страницу профиля с ошибкой, если credentials не загружены
    """
    user = request.user

    # Проверяем, загрузил ли пользователь файл с настройками (тот самый credentials.json)
    if not user.google_credentials:
        messages.error(request, "Сначала загрузите файл credentials.json и нажмите Сохранить.")
        return redirect('profile')

    try:
        # Мы временно сохраняем конфиг в словарь, чтобы Flow мог его прочитать
        # Важно: Google JSON обычно имеет структуру {"web": {...}} или {"installed": {...}}
        client_config = user.google_credentials

        # Создаем OAuth Flow
        flow = Flow.from_client_config(
            client_config,
            scopes=['https://www.googleapis.com/auth/calendar.events'],
            redirect_uri=REDIRECT_URI
        )

        # Генерируем ссылку авторизации
        auth_url, _ = flow.authorization_url(prompt='consent')

        # Сохраняем состояние во временной сессии (не обязательно для MVP, но полезно)
        request.session['google_auth_state'] = 'in_progress'

        return redirect(auth_url)

    except Exception as e:
        logger.error(f"Google Auth Error: {e}")
        messages.error(request,
                       f"Ошибка конфигурации Google: {e}. Убедитесь, что загрузили правильный JSON (OAuth Client ID).")
        return redirect('profile')


@login_required
def google_auth_callback(request):
    """
    Обрабатывает callback от Google OAuth2 авторизации.
    
    Шаг 2: Получает authorization code из URL, обменивает его на токены
    и сохраняет обновленные credentials в профиле пользователя.
    
    Args:
        code: Authorization code из GET параметров
        
    Returns:
        HttpResponse: Редирект на страницу профиля с сообщением об успехе
        
    Raises:
        HttpResponseBadRequest: Если код авторизации отсутствует
        Redirect: На страницу профиля с ошибкой при проблемах авторизации
        
    Note:
        Сохраняет refresh_token для автоматического обновления access token.
    """
    if 'code' not in request.GET:
        return HttpResponseBadRequest("Отсутствует код авторизации.")

    user = request.user

    try:
        # Снова инициализируем Flow с тем же конфигом
        client_config = user.google_credentials

        flow = Flow.from_client_config(
            client_config,
            scopes=['https://www.googleapis.com/auth/calendar.events'],
            redirect_uri=REDIRECT_URI
        )

        # Меняем код из URL на реальные токены
        flow.fetch_token(code=request.GET.get('code'))

        # Получаем итоговые credentials (с refresh_token!)
        credentials = flow.credentials

        # Формируем JSON, который уже пригоден для Authorized User
        creds_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

        # Сохраняем ЭТОТ JSON в базу. Теперь он "Authorized"
        user.google_credentials = creds_data
        user.save()

        messages.success(request, "Google Календарь успешно подключен!")
        return redirect('profile')

    except Exception as e:
        logger.error(f"Auth Callback Error: {e}")
        messages.error(request, f"Ошибка при подключении: {e}")
        return redirect('profile')


@login_required
@require_POST
def delete_candidates_mass(request):
    """
    Массовое удаление выбранных кандидатов.
    """
    candidate_ids = request.POST.getlist('candidate_ids')

    if candidate_ids:
        # Фильтруем удаление: удаляем только если пользователь имеет доступ к этому проекту
        # (Проверяем цепочку: Candidate -> Position -> Project -> ProjectUser -> User)
        deleted_count, _ = Candidate.objects.filter(
            id__in=candidate_ids,
            position__project__projectuser__user=request.user
        ).delete()

        if deleted_count > 0:
            messages.success(request, f'Успешно удалено кандидатов: {deleted_count}')
        else:
            messages.warning(request, 'Не удалось удалить выбранных кандидатов (возможно, нет прав).')

    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
@require_POST
def send_rejection_emails(request):
    """
    Массовая отправка писем с отказом и смена статуса на 'rejected'.
    """
    # 1. Проверяем, настроена ли почта у HR
    user = request.user
    if not user.email or not user.gmail_password:
        messages.error(request, 'Для отправки писем укажите Email и Gmail App Password в профиле.')
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    candidate_ids = request.POST.getlist('candidate_ids')

    if candidate_ids:
        # Получаем кандидатов (проверка прав доступа через проект)
        candidates = Candidate.objects.filter(
            id__in=candidate_ids,
            position__project__projectuser__user=user
        )

        sent_count = 0
        error_count = 0

        for candidate in candidates:
            if not candidate.gmail:
                continue

            # Текст письма (можно вынести в шаблон или настройки)
            subject = f"Ответ по вакансии {candidate.position.name}"
            body = (
                f"Здравствуйте, {candidate.full_name}.\n\n"
                f"Спасибо за проявленный интерес к вакансии \"{candidate.position.name}\".\n"
                "Мы внимательно ознакомились с вашим резюме. К сожалению, в настоящий момент "
                "мы не готовы пригласить вас на дальнейшее интервью, так как выбрали кандидатов, "
                "чей опыт больше соответствует текущим задачам.\n\n"
                "Мы сохраним ваше резюме в базе и свяжемся, если появятся подходящие позиции.\n\n"
                "С уважением,\n"
                f"{request.user.first_name or 'Команда HR'}"
            )

            try:
                # Отправка через ваш сервис
                mail_service.MailService.send_message(
                    sender_email=user.email,
                    subject=subject,
                    body=body,
                    pwd=user.gmail_password,
                    to_email=candidate.gmail
                )

                # Обновляем статус
                candidate.status = 'rejected'
                candidate.save()
                sent_count += 1

            except Exception as e:
                logger.error(f"Ошибка отправки для {candidate.gmail}: {e}")
                error_count += 1

        if sent_count > 0:
            messages.success(request, f'Отправлено писем с отказом: {sent_count}.')
        if error_count > 0:
            messages.warning(request, f'Не удалось отправить: {error_count}. Проверьте логи.')

    else:
        messages.info(request, 'Не выбрано ни одного кандидата.')

    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
@require_POST
def schedule_bot_interview(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)

    if not candidate.telegram:
        messages.error(request, "У кандидата не указан Telegram username!")
        return redirect('candidate_detail', candidate_id=candidate.id)

    form = BotInterviewSetupForm(request.POST)
    if form.is_valid():

        # Очищаем юзернейм
        clean_username = candidate.telegram.replace('@', '').strip()
        if "https" in clean_username:
            clean_username = clean_username.replace("https://t.me/", "")

        # --- НАЧАЛО ИЗМЕНЕНИЙ: Логика уникальности ---
        with transaction.atomic():
            # 1. Ищем старые АКТИВНЫЕ сессии для этого юзернейма
            old_sessions = BotInterviewSession.objects.filter(
                telegram_username=clean_username,
                status='active'
            )

            # 2. Если нашли — "архивируем" их (меняем статус на cancelled)
            if old_sessions.exists():
                count = old_sessions.update(status='cancelled')
                # Можно добавить сообщение в лог, если нужно
                print(f"Отменено {count} старых сессий для {clean_username}")

            # 3. Создаем новую сессию
            session = form.save(commit=False)
            session.candidate = candidate
            session.telegram_username = clean_username

            # Генерируем промпт
            session.interview_parameters = session.get_system_prompt()

            # Сохраняем новую (она по умолчанию status='active')
            session.save()

            # Меняем статус кандидата
            candidate.status = 'interview_scheduled'
            candidate.save()
        # --- КОНЕЦ ИЗМЕНЕНИЙ ---

        messages.success(request, f"Новое интервью назначено! Старые сессии для @{clean_username} отменены.")
    else:
        messages.error(request, "Ошибка при создании интервью. Проверьте введенные данные.")

    return redirect('candidate_detail', candidate_id=candidate.id)
