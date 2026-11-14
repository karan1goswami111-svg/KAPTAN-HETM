from django.apps import AppConfig
import os

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        try:
            # 1. Domain fix karne ke liye
            from django.contrib.sites.models import Site
            Site.objects.update_or_create(
                id=1,
                defaults={
                    'domain': 'kaptan-hetm.onrender.com',
                    'name': 'KAPTAN-HETM'
                }
            )
            
            # 2. Google Login ka error hatane ke liye (Automatic SocialApp creation)
            from allauth.socialaccount.models import SocialApp
            
            # Yahan apni real Google Client ID aur Secret daal de (ya Render env variables use kar)
            client_id = os.environ.get('GOOGLE_CLIENT_ID', 'YAHAN_APNI_GOOGLE_CLIENT_ID_DAAL_DENA')
            client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', 'YAHAN_APNI_GOOGLE_SECRET_DAAL_DENA')
            
            if client_id and 'YAHAN' not in client_id:
                google_app, created = SocialApp.objects.get_or_create(
                    provider='google',
                    defaults={
                        'name': 'Google',
                        'client_id': client_id,
                        'secret': client_secret,
                    }
                )
                google_app.sites.add(1)
        except Exception:
            pass