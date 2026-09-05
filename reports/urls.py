from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('openai-costs/', views.openai_costs, name='openai_costs'),
    path('class/<int:class_id>/entry/', views.daily_entry, name='daily_entry'),
    path('record/<int:record_id>/set/', views.set_record, name='set_record'),
    path('session/<int:session_id>/homework-due/', views.set_homework_due, name='set_homework_due'),
    path('class/<int:class_id>/student/<int:student_id>/note/', views.set_student_note, name='set_student_note'),
    path('class/<int:class_id>/overview/', views.class_overview, name='class_overview'),
    path('class/<int:class_id>/overview.csv', views.class_overview_csv, name='class_overview_csv'),
    path('class/<int:class_id>/tests/', views.test_list, name='test_list'),
    path('test/<int:test_id>/', views.test_detail, name='test_detail'),
    path('test/<int:test_id>/delete/', views.test_delete, name='test_delete'),
    path('student/<int:student_id>/', views.student_report, name='student_report'),
    path('student/<int:student_id>/report.csv', views.student_report_csv, name='student_report_csv'),
    path('student/<int:student_id>/report.pdf', views.student_report_pdf, name='student_report_pdf'),
    path('manifest.webmanifest', views.manifest, name='manifest'),
]
