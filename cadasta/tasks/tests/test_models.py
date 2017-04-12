from unittest.mock import patch

from celery.canvas import _chain, Signature
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from accounts.tests.factories import UserFactory
from core.tests.factories import PolicyFactory
from tasks.models import BackgroundTask
from tasks.celery import app
from .factories import BackgroundTaskFactory


@override_settings(CELERY_TASK_ROUTES={
    'foo.*': {'queue': 'foo_q'},
    'bar.*': {'queue': 'bar_q'}
})
@override_settings(CELERY_RESULT_QUEUE='result-queue')
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

    @patch('tasks.models.app.send_task')
    def test_save_send_task(self, send_task):
        """ Ensure that task is scheduled on BackgroundTask creation. """
        task = BackgroundTaskFactory.build(
            id='123', type='foo.bar', schedule_task_on_create=True,
            creator=self.user,
        )
        task.save()
        send_task.assert_called_once_with(
            'foo.bar', args=[], kwargs={}, task_id='123',
            **task.get_default_options())

    @patch('tasks.models.app.send_task')
    def test_save_send_task_disabled(self, send_task):
        """ Ensure that task is scheduled on BackgroundTask creation. """
        task = BackgroundTaskFactory.build(
            id='123', type='foo.bar', schedule_task_on_create=False,
            creator=self.user,
        )
        task.save()
        assert not send_task.called

    def test_default_options(self):
        task = BackgroundTaskFactory.build(
            id=None, type='foo.bar', options={'queue': 'bar_q'},
        )
        assert task.options == {
            'queue': 'bar_q',
            'reply_to': 'result-queue'
        }

    def test_default_options_no_overwrite(self):
        task = BackgroundTaskFactory.build(
            id=None, type='foo.bar', options={'queue': 'bar_q'})
        assert task.options == {
            'queue': 'bar_q',
            'reply_to': 'result-queue'
        }

    def test_chain(self):
        tasks = [
            BackgroundTaskFactory.build(
                id=i+1, input_args=(i*2,), input_kwargs={'num': i**2},
                type=name)
            for i, name in enumerate(['foo.first', 'bar.second', 'foo.third'])
        ]
        ch = BackgroundTask.chain(*tasks)
        assert isinstance(ch, _chain)
        assert all([isinstance(sig, Signature) for sig in ch.tasks])
        t1 = ch.tasks[0]
        assert t1.task == 'foo.first'
        assert t1.args == (0,)
        assert t1.kwargs == {'num': 0}
        assert tasks[0].id == t1.id == t1.options['task_id'] == 1
        assert t1.options['queue'] == 'foo_q'

        t2 = ch.tasks[1]
        assert t2.task == 'bar.second'
        assert t2.args == (2,)
        assert t2.kwargs == {'num': 1}
        assert tasks[1].id == t2.id == t2.options['task_id'] == 2
        assert t2.options['queue'] == 'bar_q'
        assert tasks[1].parent_id == tasks[0].id

        t3 = ch.tasks[2]
        assert t3.task == 'foo.third'
        assert t3.args == (4,)
        assert t3.kwargs == {'num': 4}
        assert tasks[2].id == t3.id == t3.options['task_id'] == 3
        assert t3.options['queue'] == 'foo_q'
        assert tasks[2].parent_id == tasks[1].id

    @patch('tasks.models.app.send_task')
    def test_chain_no_schedule(self, send_task):
        """
        Ensure that chain won't schedule a task, even if it needs to
        save the task (e.g to get an ID).
        """
        tasks = [
            BackgroundTaskFactory.build(
                id=None, type=name, creator=self.user,
                input_args=(i*2,), input_kwargs={'num': i**2},
                schedule_task_on_create=True
            )
            for i, name in enumerate(['foo.first', 'bar.second'])
        ]
        ch = BackgroundTask.chain(*tasks)
        t1 = ch.tasks[0]
        assert t1.task == 'foo.first'
        assert tasks[0].id
        assert t1.id == tasks[0].id
        assert tasks[0].schedule_task_on_create is False

        t2 = ch.tasks[1]
        assert t2.task == 'bar.second'
        assert tasks[1].id
        assert t2.id == tasks[1].id
        assert tasks[1].schedule_task_on_create is False

        assert not send_task.called
