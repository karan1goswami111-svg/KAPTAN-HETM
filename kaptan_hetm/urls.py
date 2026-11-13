from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # Google OAuth aur allauth ke routes ke liye zaroori hai
    path('', include('core.urls')),
]