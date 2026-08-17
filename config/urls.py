# config\urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
   path('admin/', admin.site.urls),
   path('', include('apps.dashboard.urls')),
   path('accounts/', include('apps.accounts.urls')),
   path('letters/', include('apps.letters.urls')),
   path('documents/', include('apps.documents.urls')),
]
if settings.DEBUG:
   # Local dev (plain `runserver`): serve media at plain /media/, no app prefix
   urlpatterns += [
       re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
   ]
   urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
   # Production (IIS): serve at the prefixed path matching MEDIA_URL/STATIC_URL
   urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
   urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)