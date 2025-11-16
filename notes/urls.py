# notes/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Index page - must be before save-info
    path("", views.notes_index, name="notes_index"),

    # Save info endpoint
    path("save-info/", views.save_info, name="save_info"),

    # Topic-specific notes
    path("<str:topic_name>/", views.notes_topic, name="notes_topic"),
]
