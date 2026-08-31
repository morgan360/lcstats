from django.urls import path

from . import views

app_name = 'hw_solutions'

urlpatterns = [
    path('', views.hw_solutions_index, name='hw_solutions_index'),
]
