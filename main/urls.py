# main/urls.py

from django.urls import include, path

from . import views  # Импортируем представления из текущего приложения

urlpatterns = [
    path('', views.projects, name='home'),
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('positions/<int:position_id>/', views.position_detail, name='position_detail'),
    path('candidates/<int:candidate_id>/', views.candidate_detail, name='candidate_detail'),
    path('projects/<int:project_id>/delete/', views.delete_project, name='delete_project'),
    path('projects/<int:project_id>/add_user/', views.add_user_to_project, name='add_user_to_project'),
    path('positions/<int:position_id>/delete/', views.delete_position, name='delete_position'),
    path('positions/<int:position_id>/import_url/', views.import_requirements_from_url,
         name='import_requirements_from_url'),
    path('schedule-mass/', views.schedule_interviews, name='schedule_interviews'),
    path('google-auth/start/', views.start_google_auth, name='start_google_auth'),
    path('oauth2callback/', views.google_auth_callback, name='google_auth_callback'),
]