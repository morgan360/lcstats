# notes/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # 🧠 Put this FIRST
    path("save-info/", views.save_info, name="save_info"),

    # Your other routes (leave them after)
    path("<str:topic_name>/", views.notes_topic, name="notes_topic"),
]
