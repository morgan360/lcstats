from django.urls import path

from . import views

app_name = 'studyplans'

urlpatterns = [
    # Student views
    path('', views.my_plan, name='my_plan'),
    path('achievements/', views.achievements, name='achievements'),
    path('plan/<int:plan_id>/', views.plan_detail, name='plan_detail'),
    path('checkpoint/<int:checkpoint_id>/', views.checkpoint_detail,
         name='checkpoint_detail'),
    path('item/<int:item_id>/start/', views.start_item, name='start_item'),
    path('item/<int:item_id>/tick/', views.toggle_item_done, name='toggle_item'),
    path('plan/<int:plan_id>/refresh/', views.refresh_progress,
         name='refresh_progress'),

    # Teacher views
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/new/', views.plan_builder, name='plan_builder'),
    path('teacher/preview/', views.plan_preview, name='plan_preview'),
    path('teacher/create/', views.plan_create, name='plan_create'),
    path('teacher/plan/<int:plan_id>/', views.plan_manage, name='plan_manage'),
    path('teacher/plan/<int:plan_id>/checkpoint/<int:checkpoint_id>/',
         views.manage_checkpoint, name='manage_checkpoint'),
    path('teacher/plan/<int:plan_id>/item/<int:item_id>/remove/',
         views.remove_item, name='remove_item'),
    path('teacher/plan/<int:plan_id>/run/', views.run_now, name='run_now'),
    path('teacher/class/<int:class_id>/oversight/', views.class_oversight,
         name='class_oversight'),
    path('teacher/student/<int:student_id>/', views.student_oversight,
         name='student_oversight'),

    # Builder helper API
    path('api/topic-candidates/<int:topic_id>/', views.topic_candidates,
         name='topic_candidates'),
]
