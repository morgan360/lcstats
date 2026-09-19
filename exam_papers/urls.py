from django.urls import path
from . import views

app_name = 'exam_papers'

urlpatterns = [
    # List of all available exam papers
    path('', views.paper_list, name='paper_list'),

    # Papers & marking schemes browser
    path('browse/', views.papers_and_solutions, name='papers_and_solutions'),

    # Worksheet generator (public, for all logged-in users)
    path('worksheet/', views.worksheet_generator, name='worksheet_generator'),
    path('worksheet/print/', views.worksheet_print, name='worksheet_print'),
    path('worksheet/pdf/', views.worksheet_pdf, name='worksheet_pdf'),

    # The same, one card per question part
    path('worksheet/parts/', views.parts_generator, name='parts_generator'),
    path('worksheet/parts/print/', views.parts_print, name='parts_print'),
    path('worksheet/parts/pdf/', views.parts_pdf, name='parts_pdf'),

    # Retagging from those two pages (superusers only; the views re-check)
    path('question/<int:pk>/topic/',
         views.set_question_topic, name='set_question_topic'),
    path('part/<int:pk>/topic/', views.set_part_topic, name='set_part_topic'),

    # Full paper attempt (timed or practice) - slug catch-all must come after specific routes
    path('<slug:slug>/', views.paper_detail, name='paper_detail'),
    path('<slug:slug>/start/', views.start_paper_attempt, name='start_paper_attempt'),

    # Open a single question part for practice, straight from a link
    path('part/<int:part_id>/practise/', views.practise_part, name='practise_part'),

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