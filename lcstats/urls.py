from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # Django-allauth URLs
    path('hijack/', include('hijack.urls')),  # Django-hijack URLs
    path("", include("home.urls")),
    path("chat/", include("chat.urls")),
    path("interactive/", include("interactive_lessons.urls")),
    path("markdownx/", include("markdownx.urls")),
    path("notes/", include("notes.urls")),
    path('students/', include('students.urls')),
    path('revision/', include('revision.urls')),
    path('cheatsheets/', include('cheatsheets.urls')),
    path('exam-papers/', include('exam_papers.urls')),
    path('quickkicks/', include('quickkicks.urls')),
    path('homework/', include('homework.urls')),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)