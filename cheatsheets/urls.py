from django.urls import path
from . import views

app_name = 'cheatsheets'

urlpatterns = [
    path('', views.cheatsheets_index, name='cheatsheets_index'),
    path('log-tables/', views.log_tables_view, name='log_tables'),
    path('<slug:topic_slug>/', views.cheatsheets_by_topic, name='cheatsheets_topic'),
]