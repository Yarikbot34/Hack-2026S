import os
from celery import Celery

# позволяет отправить задачу в очередь и сразу ответить пользователю "ОК", пока в фоне работает воркер

# Указываем Django на настройки
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

# Создаем экземпляр приложения Celery
app = Celery('app')

# Загружаем конфигурацию из Django settings (префикс CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим задачи во всех установленных приложениях
# Это значит, что он сам найдет tasks.py в database, nlp, main
app.autodiscover_tasks()
