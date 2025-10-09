from django.urls import path
from . import views

urlpatterns = [
    path("", views.select_topic, name="select_topic"),

    # Info bot (always keep before <str:topic_name>)
    path("info-bot/<slug:topic_slug>/", views.info_bot, name="info_bot"),

    # Question navigation system (new)
    path("<int:topic_id>/question/<int:number>/", views.question_view, name="question_view"),

    # Interactive quiz (old topic-based system)
    path("<str:topic_name>/", views.interactive_quiz, name="interactive_quiz"),
    path("<str:topic_name>/<int:q_index>/", views.interactive_quiz, name="interactive_quiz"),
    path("<str:topic_name>/complete/", views.topic_complete, name="topic_complete"),
]
