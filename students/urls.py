# students/urls.py
from django.urls import path
from .views import LogoutViewAllowGet
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='students/login.html'), name='login'),
    path('logout/', LogoutViewAllowGet.as_view(next_page='/'), name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('question-attempt/<int:attempt_id>/feedback/', views.question_attempt_feedback, name='question_attempt_feedback'),
]
