from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.tests.factories import UserFactory
from core.tests.factories import PolicyFactory
from tasks.celery import app
from .factories import BackgroundTaskFactory


class TestBackgroundTaskModel(TestCase):

    def setUp(self):
        PolicyFactory.load_policies()
        self.user = UserFactory.create()

        # Ensure new routes are applied
        app.amqp.flush_routes()
        app.amqp.router = app.amqp.Router()

    def test_str(self):
        task = BackgroundTaskFactory.build(id='a1b2c3', type='some.task')
        assert str(task) == 'id=a1b2c3 type=some.task status=PENDING'

    def test_save_valid_input_args(self):
        """ Ensure that invalid input args will raise validation error """
        with self.assertRaises(ValidationError) as context:
            BackgroundTaskFactory.build(
                id=None, type='foo.bar', input={'args': None},
                creator=self.user
            ).save()
        assert context.exception.error_dict.get('input')

        with self.assertRaises(ValidationError) as context:
            BackgroundTaskFactory.build(
                id=None, type='foo.bar', input={'args': {}},
                creator=self.user
            ).save()
        assert context.exception.error_dict.get('input')

    def test_save_valid_input_kwargs(self):
        """ Ensure that invalid input kwargs will raise validation error """
        with self.assertRaises(ValidationError) as context:
            BackgroundTaskFactory.build(
                id=None, type='foo.bar', input={'kwargs': None},
                creator=self.user
            ).save()
        assert context.exception.error_dict.get('input')

        with self.assertRaises(ValidationError) as context:
            BackgroundTaskFactory.build(
                id=None, type='foo.bar', input={'kwargs': []},
                creator=self.user
            ).save()
        assert context.exception.error_dict.get('input')

    def test_save_valid_input(self):
        """ Ensure that input requires both 'args' and 'kwargs' values. """
        # Missing kwargs
        with self.assertRaises(ValidationError) as context:
            BackgroundTaskFactory.build(
                id=None, type='foo.bar', input={'args': []},
                creator=self.user
            ).save()
        assert context.exception.error_dict.get('input')

        # Missing args
        with self.assertRaises(ValidationError) as context:
            BackgroundTaskFactory.build(
                id=None, type='foo.bar', input={'kwargs': {}},
                creator=self.user
            ).save()
        assert context.exception.error_dict.get('input')

        # All good
        BackgroundTaskFactory.build(
            id=None, type='foo.bar', input={'args': [], 'kwargs': {}},
            creator=self.user
        ).save()
