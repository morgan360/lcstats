# students/urls.py
from django.urls import path
from django.views.generic import RedirectView
from .views import LogoutViewAllowGet
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

    # These used to be a second, parallel auth flow with their own templates.
    # They had no "Continue with Google" button and never would have: allauth
    # only renders social logins on its own views. Redirected rather than
    # deleted so existing links and bookmarks keep working; the names are kept
    # for the same reason.
    path('signup/', RedirectView.as_view(pattern_name='account_signup', permanent=False), name='signup'),
    path('login/', RedirectView.as_view(pattern_name='account_login', permanent=False), name='login'),
    path('logout/', LogoutViewAllowGet.as_view(next_page='/'), name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('question-attempt/<int:attempt_id>/feedback/', views.question_attempt_feedback, name='question_attempt_feedback'),
]
