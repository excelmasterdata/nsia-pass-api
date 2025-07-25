# nsia_pass_api/celery.py
import os
from celery import Celery
from django.conf import settings


# Configurer Django pour Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nsia_pass_api.settings')

app = Celery('nsia_pass_api')

# Configuration depuis settings.py avec le préfixe CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-découverte des tâches dans toutes les apps Django
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')