from datetime import datetime
from core.tests.utils.cases import UserTestCase
from accounts.models import PublicRole
from django.test import TestCase

from .factories import UserFactory


class UserTest(TestCase):
    def test_repr(self):
        date = datetime.now()
        user = UserFactory.build(username='John',
                                 full_name='John Lennon',
                                 email='john@beatles.uk',
                                 email_verified=True,
                                 verify_email_by=date)
        assert repr(user) == ('<User username=John'
                              ' full_name=John Lennon'
                              ' email=john@beatles.uk'
                              ' email_verified=True'
                              ' verify_email_by={}>').format(date)


class PublicRoleTest(UserTestCase, TestCase):

    def test_role_creation(self):
        user = UserFactory.create()
        role = PublicRole.objects.get(user=user)
        assert role.name == 'public_user'
        assert role.group.name == 'PublicUser'
        assert len(role.permissions) == 8
        assert role.is_public_user
