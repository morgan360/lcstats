from django.urls import path
from . import views

app_name = 'cheatsheets'

urlpatterns = [
    path('', views.cheatsheets_index, name='cheatsheets_index'),
    path('<slug:topic_slug>/', views.cheatsheets_by_topic, name='cheatsheets_topic'),
]