from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from tasks.consumers import ResultConsumer
from tasks.tests.factories import BackgroundTaskFactory


@override_settings(CELERY_RESULT_QUEUE='results-queue')
class TestConsumers(TestCase):

    @patch('celery.app.app_or_default')
    @patch('tasks.consumers.bootsteps.ConsumerStep.__init__')
    def test_validate_queues(self, consumer_init, get_mock_app):
        """
        Ensure that consumer throws exception if worker processing Results
        queue.
        """
        mock_app = MagicMock()
        get_mock_app.return_value = mock_app
        mock_app.amqp.queues = ['foo', 'results-queue']

        with self.assertRaises(ValueError):
            ResultConsumer()
        assert not consumer_init.called

        # Correct setup
        mock_app.amqp.queues = ['foo', 'bar']
        ResultConsumer()
        consumer_init.assert_called_once_with()

    @patch('tasks.consumers.bootsteps.ConsumerStep.__init__', MagicMock())
    def test_get_queues(self):
        consumers = ResultConsumer().get_consumers(MagicMock())
        assert len(consumers) == 1
        consumer = consumers[0]
        assert len(consumer.queues) == 1
        queue = consumer.queues[0]
        queue.name == 'results-queue'

    @patch('tasks.consumers.bootsteps.ConsumerStep.__init__', MagicMock())
    @patch('tasks.consumers.BackgroundTask.objects.get')
    def test_message_handler_completed(self, mock_get):
        """
        Ensure completed tasks set output to the output property.
        """
        task = BackgroundTaskFactory.build(status='PENDING', log=[])
        mock_get.return_value = task
        task.save = MagicMock()

        fake_body = {
            'task_id': '123',
            'status': 'SUCCESS',
            'result': 'All succeeded',
        }
        mock_msg = MagicMock()
        ResultConsumer().handle_message(fake_body, mock_msg)
        task.save.assert_called_once_with()
        mock_msg.ack.assert_called_once_with()
        assert task.status == 'SUCCESS'
        assert task.output == "All succeeded"
        assert task.log == []

    @patch('tasks.consumers.bootsteps.ConsumerStep.__init__', MagicMock())
    @patch('tasks.consumers.BackgroundTask.objects.get')
    def test_message_handler_in_progress_str_log(self, mock_get):
        """
        Ensure in-progess tasks append output str to the log.
        """
        task = BackgroundTaskFactory.build(status='PENDING', log=[])
        mock_get.return_value = task
        task.save = MagicMock()

        fake_body = {
            'task_id': '123',
            'status': 'PROGRESS',
            'result': 'Things are coming along',
        }
        mock_msg = MagicMock()
        ResultConsumer().handle_message(fake_body, mock_msg)
        task.save.assert_called_once_with()
        mock_msg.ack.assert_called_once_with()
        assert task.status == 'PROGRESS'
        assert task.output is None
        assert task.log == ['Things are coming along']

    @patch('tasks.consumers.bootsteps.ConsumerStep.__init__', MagicMock())
    @patch('tasks.consumers.BackgroundTask.objects.get')
    def test_message_handler_in_progress_dict_log(self, mock_get):
        """
        Ensure in-progess tasks append output dict with log key to the log.
        """
        task = BackgroundTaskFactory.build(status='PENDING', log=[])
        mock_get.return_value = task
        task.save = MagicMock()

        fake_body = {
            'task_id': '123',
            'status': 'PROGRESS',
            'result': {'log': 'Things are coming along'},
        }
        mock_msg = MagicMock()
        ResultConsumer().handle_message(fake_body, mock_msg)
        task.save.assert_called_once_with()
        mock_msg.ack.assert_called_once_with()
        assert task.status == 'PROGRESS'
        assert task.output is None
        assert task.log == ['Things are coming along']

    @patch('tasks.consumers.bootsteps.ConsumerStep.__init__', MagicMock())
    @patch('tasks.consumers.logger')
    def test_message_handler_handles_exceptions(self, mock_logger):
        """
        Ensure that exceptions in task parsing are handled gracefully
        """
        mock_msg = MagicMock()
        empty_body = {}
        ResultConsumer().handle_message(empty_body, mock_msg)
        mock_msg.ack.assert_called_once_with()
        assert mock_logger.exception.call_count == 1

    @patch('tasks.consumers.bootsteps.ConsumerStep.__init__', MagicMock())
    @patch('tasks.consumers.BackgroundTask.objects.get')
    @patch('tasks.consumers.logger')
    def test_message_handler_handles_failed_ack(self, mock_logger, mock_get):
        """
        Ensure that exceptions in task parsing are handled gracefully
        """
        task = BackgroundTaskFactory.build(status='PENDING')
        mock_get.return_value = task
        task.save = MagicMock()
        fake_body = {
            'task_id': '123',
            'status': 'PROGRESS',
            'result': {'log': 'Things are coming along'},
        }
        ack_func = MagicMock(side_effect=Exception("Failed ack"))
        mock_msg = MagicMock(ack=ack_func)
        ResultConsumer().handle_message(fake_body, mock_msg)
        ack_func.assert_called_once_with()
        assert mock_logger.exception.call_count == 1
