from django.urls import path
from . import exam_builder, views

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

    # Teachers' own exams, built from past questions (teachers only). Above the
    # <slug:slug>/ paper route, which would otherwise swallow "exams/".
    path('exams/', exam_builder.my_exams, name='my_exams'),
    path('exams/new/', exam_builder.exam_create, name='exam_create'),
    path('exams/<int:pk>/', exam_builder.exam_builder, name='exam_builder'),
    path('exams/<int:pk>/details/', exam_builder.exam_save_details, name='exam_save_details'),
    path('exams/<int:pk>/add/', exam_builder.exam_add_question, name='exam_add_question'),
    path('exams/<int:pk>/items/<int:item_pk>/remove/', exam_builder.exam_remove_question,
         name='exam_remove_question'),
    path('exams/<int:pk>/items/<int:item_pk>/move/', exam_builder.exam_move_question,
         name='exam_move_question'),
    path('exams/<int:pk>/items/<int:item_pk>/omit/', exam_builder.exam_set_omitted,
         name='exam_set_omitted'),
    path('exams/<int:pk>/delete/', exam_builder.exam_delete, name='exam_delete'),
    path('exams/<int:pk>/exam.pdf', exam_builder.exam_pdf, name='exam_pdf'),
    path('exams/<int:pk>/marking-scheme.pdf', exam_builder.exam_scheme_pdf,
         name='exam_scheme_pdf'),

    # Retagging from the worksheet page (superusers only; the view re-checks)
    path('question/<int:pk>/topics/',
         views.set_question_topics, name='set_question_topics'),

    # Exam questions by topic
    path('questions/', views.exam_questions_index, name='exam_questions_index'),

    # Full paper attempt (timed or practice) - slug catch-all must come after specific routes
    path('<slug:slug>/', views.paper_detail, name='paper_detail'),
    path('<slug:slug>/start/', views.start_paper_attempt, name='start_paper_attempt'),

    # Open a single question part for practice, straight from a link
    path('question/<int:question_id>/practise/', views.practise_question,
         name='practise_question'),
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