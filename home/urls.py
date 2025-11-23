from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("news/dismiss/<int:news_id>/", views.dismiss_news_item, name="dismiss_news"),
]
