from django.apps import AppConfig


class TasksConfig(AppConfig):
    name = 'tasks'

    def ready(self):
        from .celery import app
        from .consumers import ResultConsumer
        app.steps['consumer'].add(ResultConsumer)
