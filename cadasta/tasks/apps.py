from django.apps import AppConfig


class TasksConfig(AppConfig):
    name = 'tasks'

    def ready(self):
        from . import signals  # NOQA
        from .celery import app
        from .consumers import ResultConsumer
        app.steps['consumer'].add(ResultConsumer)
        app.autodiscover_tasks(force=True)

        from .models import BackgroundTask
        BackgroundTask.TASK_TYPES = [(t, t) for t in app.tasks]
