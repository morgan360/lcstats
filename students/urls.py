# students/urls.py
from django.urls import path
from .views import LogoutViewAllowGet
from django.contrib.auth import views as auth_views
from . import views
from . import views_work

urlpatterns = [
    # Photograph-your-working. work_mobile is reached by scanning a QR on the
    # laptop, so it authenticates by signed token rather than by session.
    path('work/slot/', views_work.work_slot, name='work_slot'),
    path('work/<int:pk>/status/', views_work.work_status, name='work_status'),
    path('work/<int:pk>/photo/', views_work.work_photo, name='work_photo'),
    path('work/<int:pk>/delete/', views_work.work_delete, name='work_delete'),
    path('work/m/<str:token>/', views_work.work_mobile, name='work_mobile'),
    path('work/m/<str:token>/upload/', views_work.work_mobile_upload, name='work_mobile_upload'),

    path('signup/', views.signup_view, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='students/login.html'), name='login'),
    path('logout/', LogoutViewAllowGet.as_view(next_page='/'), name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('question-attempt/<int:attempt_id>/feedback/', views.question_attempt_feedback, name='question_attempt_feedback'),
]
