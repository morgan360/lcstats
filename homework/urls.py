from django.urls import path
from . import views

app_name = 'homework'

urlpatterns = [
    # Student views
    path('', views.student_homework_dashboard, name='student_dashboard'),
    path('assignment/<int:assignment_id>/', views.assignment_detail, name='assignment_detail'),
    path('toggle-task/<int:progress_id>/', views.toggle_task_completion, name='toggle_task'),
    path('submit/<int:assignment_id>/', views.submit_homework, name='submit_homework'),

    # Notification views
    path('snooze-notification/', views.snooze_homework_notification, name='snooze_notification'),

    # Teacher views
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/class/<int:class_id>/', views.class_detail, name='class_detail'),
    path('teacher/class/<int:class_id>/report/', views.class_homework_report, name='class_homework_report'),
    path('teacher/assignment/<int:assignment_id>/progress/', views.assignment_progress, name='assignment_progress'),
]
