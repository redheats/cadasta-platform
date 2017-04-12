from celery import states, Signature
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _

from core.models import RandomIDModel
from .celery import app
from .utils import fields as utils


class BackgroundTask(RandomIDModel):
    ALL_STATES = sorted(states.ALL_STATES)
    DONE_STATES = ('SUCCESS', 'FAILURE')
    TASK_STATE_CHOICES = sorted(zip(ALL_STATES, ALL_STATES))
    FOLLOWUP_FUNCTION_CHOICES = {}

    type = models.CharField(_('Task function'), max_length=128)
    status = models.CharField(
        _('State'), max_length=50, default=states.PENDING,
        choices=TASK_STATE_CHOICES)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True)

    input = JSONField(
        default=utils.input_field_default, blank=True,
        validators=[utils.is_type(dict), utils.validate_input_field])
    options = JSONField(
        _('Task scheduling options'), default=dict, blank=True,
        validators=[utils.is_type(dict)])
    output = JSONField(null=True, blank=True)
    log = ArrayField(models.TextField(), default=list, blank=True)

    related_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey(
        'related_content_type', 'related_object_id')

    parent = models.ForeignKey(
        'self', related_name='children', on_delete=models.CASCADE,
        blank=True, null=True)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return 'id={0.id} type={0.type} status={0.status}'.format(self)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._state.adding:
            self.options = self.get_default_options()

    def save(self, *args, **kwargs):
        created = self._state.adding
        with transaction.atomic():
            super().save(*args, **kwargs)
            # Ensure model fields run through validators after special
            # auto-filled data (eg auto_now_add) is added.
            self.full_clean(exclude=None)

        if created and self.schedule_task_on_create:
            app.send_task(
                self.type, args=self.input_args, kwargs=self.input_kwargs,
                task_id=self.id, **self.options)

    def get_default_options(self):
        """
        Return a copy of task's options with defaults added. Will not
        overwrite existing options' settings.
        """
        options = self.options.copy()
        options.setdefault('reply_to', settings.CELERY_RESULT_QUEUE)
        options.setdefault(
            'queue', app.amqp.router.route({}, self.type)['queue'].name)
        return options

    @classmethod
    @transaction.atomic
    def chain(cls, *tasks):
        """
        Chain tasks together in order they were recieved. Requires input
        of BackgroundTask instances. Will update instances to connect
        tasks to their parent BackgroundTasks instances. Will not save
        those instances. Saving must be done manually.
        """
        previous_id = None
        chain = None
        for task in tasks:
            task.schedule_task_on_create = False
            if previous_id:
                task.parent_id = previous_id
            if not task.id:
                task.save()
            previous_id = task.id
            sig = task.as_signature()
            chain = (chain | sig) if chain else sig
        setattr(chain, 'models', tasks)
        return chain

    def as_signature(self):
        return Signature(
            self.type, args=self.input_args, kwargs=self.input_kwargs,
            task_id=self.id, **self.options,
        )

    @property
    def input_args(self):
        return self.input.get('args')

    @input_args.setter
    def input_args(self, value):
        self.input['args'] = value

    @property
    def input_kwargs(self):
        return self.input.get('kwargs')

    @input_kwargs.setter
    def input_kwargs(self, value):
        self.input['kwargs'] = value

    @property
    def schedule_task_on_create(self):
        return getattr(self, '_schedule_task_on_create', True)

    @schedule_task_on_create.setter
    def schedule_task_on_create(self, value):
        return setattr(self, '_schedule_task_on_create', value)
