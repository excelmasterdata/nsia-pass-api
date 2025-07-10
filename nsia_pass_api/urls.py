from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.borne_auth.urls')),
]


# Servir les fichiers statiques en développement ET production
if settings.DEBUG or True:  # Force pour Render
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)