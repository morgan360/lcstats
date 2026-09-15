from django.urls import path

from . import views

app_name = 'homework_check'

urlpatterns = [
    path('', views.index, name='index'),
    path('new/', views.check_new, name='check_new'),
    path('<int:pk>/', views.check_detail, name='check_detail'),
    path('<int:pk>/upload/', views.check_upload, name='check_upload'),
    path('<int:pk>/analyse-next/', views.analyse_next, name='analyse_next'),
    path('<int:pk>/edit/', views.check_edit, name='check_edit'),
    path('<int:pk>/report/', views.report_print, name='report_print'),
    path('<int:pk>/delete/', views.check_delete, name='check_delete'),
    path('photo/<int:pk>/', views.check_photo, name='check_photo'),
    path('photo/<int:pk>/delete/', views.photo_delete, name='photo_delete'),
    path('scans/', views.scans, name='scans'),
    path('scans/assign/', views.scans_assign, name='scans_assign'),
    path('scans/<int:pk>/thumb/', views.scan_thumb, name='scan_thumb'),
    path('scans/<int:pk>/delete/', views.scan_delete, name='scan_delete'),
    path('run/', views.run, name='run'),
    path('inbound-email/', views.inbound_email, name='inbound_email'),
]
