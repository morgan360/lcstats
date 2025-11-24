from django.urls import path
from . import views

urlpatterns = [
    path('<slug:topic_slug>/', views.cheatsheets_by_topic, name='cheatsheets_topic'),
]