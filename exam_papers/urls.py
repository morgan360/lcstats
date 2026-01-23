from django.urls import path
from . import views

app_name = 'exam_papers'

urlpatterns = [
    # List of all available exam papers
    path('', views.paper_list, name='paper_list'),

    # Full paper attempt (timed or practice)
    path('<slug:slug>/', views.paper_detail, name='paper_detail'),
    path('<slug:slug>/start/', views.start_paper_attempt, name='start_paper_attempt'),

    # Question interface
    path('attempt/<int:attempt_id>/question/<int:question_id>/',
         views.question_interface, name='question_interface'),

    # Submit answer for a question part
    path('attempt/<int:attempt_id>/submit/',
         views.submit_answer, name='submit_answer'),

    # Get solution (with attempt-based unlocking)
    path('attempt/<int:attempt_id>/solution/<int:part_id>/',
         views.get_solution, name='get_solution'),

    # Complete exam attempt
    path('attempt/<int:attempt_id>/complete/',
         views.complete_attempt, name='complete_attempt'),

    # View results
    path('attempt/<int:attempt_id>/results/',
         views.view_results, name='view_results'),

    # Topic-based practice
    path('topic/<int:topic_id>/', views.topic_practice, name='topic_practice'),

    # Feedback on question grading
    path('attempt/<int:attempt_id>/feedback/',
         views.exam_question_feedback, name='exam_question_feedback'),

    # Timer controls
    path('attempt/<int:attempt_id>/pause/',
         views.pause_exam, name='pause_exam'),
    path('attempt/<int:attempt_id>/resume/',
         views.resume_exam, name='resume_exam'),
    path('attempt/<int:attempt_id>/exit/',
         views.exit_exam, name='exit_exam'),
]