from django.urls import path
from . import views

urlpatterns = [
    # --- Topic selector ---
    path("", views.select_topic, name="select_topic"),

    # --- Info Bot endpoint ---
    path("info-bot/<slug:topic_slug>/", views.info_bot, name="info_bot"),

    # --- Main question view (new system, supports subquestions) ---
    path("<int:topic_id>/question/<int:number>/", views.question_view, name="question_view"),

    # --- Topic completion page ---
    path("<str:topic_name>/complete/", views.topic_complete, name="topic_complete"),

    # --- Contact teacher about a question ---
    path("question/<int:question_id>/contact/", views.question_contact, name="question_contact"),

    # --- Animation demo ---
    path("demo/animation/", views.animation_demo, name="animation_demo"),
]
