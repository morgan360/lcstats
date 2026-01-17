from django.urls import path
from . import views

app_name = 'flashcards'

urlpatterns = [
    # List all flashcard sets (all topics)
    path('', views.flashcard_sets_index, name='flashcard_sets_index'),

    # List sets for a specific topic
    path('<slug:topic_slug>/', views.flashcard_sets_list, name='flashcard_sets_list'),

    # Study a specific set (shows cards one by one)
    path('<slug:topic_slug>/<int:set_id>/study/', views.study_set, name='study_set'),

    # AJAX endpoint to record answer
    path('api/record-answer/', views.record_answer, name='record_answer'),

    # AJAX endpoint to demote a 'know' card back to 'learning'
    path('api/demote-card/', views.demote_card, name='demote_card'),

    # AJAX endpoint to reset a single card's progress
    path('api/reset-card/', views.reset_card_progress, name='reset_card'),

    # Reset all progress for a set
    path('<slug:topic_slug>/<int:set_id>/reset/', views.reset_set_progress, name='reset_set'),

    # Student progress view for a set
    path('<slug:topic_slug>/<int:set_id>/progress/', views.set_progress, name='set_progress'),
]
