from django.urls import path
from . import views

urlpatterns = [
    path('', views.module_list, name='module_list'),
    path('<slug:topic_slug>/', views.module_detail, name='module_detail'),
]
