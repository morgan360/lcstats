from django.urls import path
from . import views

app_name = 'quickkicks'

urlpatterns = [
    path('', views.quickkicks_index, name='quickkicks_index'),
    path('<slug:topic_slug>/', views.quickkicks_list, name='quickkicks_list'),
    path('<slug:topic_slug>/<int:quickkick_id>/', views.quickkick_view, name='quickkick_view'),
]