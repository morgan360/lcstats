from django.urls import path
from . import views

urlpatterns = [
    # --- Topic selector ---
    path("", views.select_topic, name="select_topic"),

    # --- Info Bot endpoint ---
    path("info-bot/<slug:topic_slug>/", views.info_bot, name="info_bot"),

    # --- Section-based navigation ---
    path("<slug:topic_slug>/sections/", views.section_list, name="section_list"),
    path("<slug:topic_slug>/sections/<slug:section_slug>/", views.section_quiz, name="section_quiz"),
    path("<slug:topic_slug>/sections/<slug:section_slug>/question/<int:number>/",
         views.section_question_view, name="section_question_view"),

    # --- Topic quiz entry point (redirects to section list) ---
    path("quiz/<slug:topic_slug>/", views.topic_quiz, name="topic_quiz"),

    # --- Main question view (legacy, for backwards compatibility) ---
    path("<int:topic_id>/question/<int:number>/", views.question_view, name="question_view"),

    # --- Topic completion page ---
    path("<str:topic_name>/complete/", views.topic_complete, name="topic_complete"),

    # --- Contact teacher about a question ---
    path("question/<int:question_id>/contact/", views.question_contact, name="question_contact"),
]
