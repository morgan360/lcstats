# notes/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # The old Study Resources pages; they now redirect to Summary Notes.
    path("", views.old_study_resources),

    # Save info endpoint
    path("save-info/", views.save_info, name="save_info"),

    path("<str:topic_name>/", views.old_study_resources),
]
