import json
from django.test import TestCase, RequestFactory
from django.template.loader import render_to_string
from django.contrib.contenttypes.models import ContentType
from skivvy import APITestCase, remove_csrf
from tutelary.models import Policy, assign_user_policies, Role

from accounts.tests.factories import UserFactory
from organization.tests.factories import ProjectFactory
from organization.models import OrganizationRole
from core.tests.utils.cases import UserTestCase
from party.tests.factories import PartyFactory, TenureRelationshipFactory
from spatial.tests.factories import SpatialUnitFactory
from ..views.async import ResourceList
from ..models import Resource, ContentObject
from .factories import ResourceFactory


def assign_policies(user):
    clauses = {
        'clause': [
            {
                "effect": "allow",
                "object": ["*"],
                "action": ["org.*"]
            }, {
                'effect': 'allow',
                'object': ['organization/*'],
                'action': ['org.*', "org.*.*"]
            }, {
                'effect': 'allow',
                'object': ['project/*/*'],
                'action': ['project.*', 'project.*.*', 'resource.*']
            }, {
                'effect': 'allow',
                'object': ['resource/*/*/*'],
                'action': ['resource.*']
            }
        ]
    }
    policy = Policy.objects.create(
        name='test-policy',
        body=json.dumps(clauses))
    assign_user_policies(user, policy)


class ProjectResourcesTest(APITestCase, UserTestCase, TestCase):
    view_class = ResourceList
    get_data = {'draw': '1', 'start': 0, 'length': 10, 'order[0][column]': 0}
    request_meta = {'HTTP_REFERER': 'http://example.com/'}

    def setup_models(self):
        self.user = UserFactory.create()
        self.project = ProjectFactory.create()
        ResourceFactory.create_batch(10,
                                     project=self.project,
                                     content_object=self.project)
        self.search_resource = ResourceFactory.create(
            name='TestForSearch',
            project=self.project,
            content_object=self.project)
        self.archived_resource = ResourceFactory.create(
            name='Archived Resource',
            project=self.project,
            content_object=self.project,
            archived=True)
        ResourceFactory.create_batch(5,
                                     project=self.project)

    def setup_url_kwargs(self):
        return {
            'organization': self.project.organization.slug,
            'project': self.project.slug
        }

    def render_html_snippet(self, resources):
        model_type = ContentType.objects.get_for_model(self.project)
        attachments = ContentObject.objects.filter(
            content_type__pk=model_type.id,
            object_id=self.project.id,
            resource_id__in=[resource.id for resource in resources]
        ).values_list('resource_id', 'id')
        attachment_id_dict = dict(attachments)

        for r in resources:
            r.attachment_id = attachment_id_dict.get(r.id)

        html = render_to_string(
            'resources/table_snippets/resource.html',
            context={'resources': resources,
                     'project': self.project,
                     'detatch_redirect': 'http://example.com/'},
            request=RequestFactory().get('/'))

        return remove_csrf(html)

    def test_get_default(self):
        assign_policies(self.user)
        response = self.request(user=self.user)
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 16
        assert response.content['recordsFiltered'] == 16

        resources = Resource.objects.filter(
            archived=False).order_by('name')[0:10]
        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet(resources))

    def test_get_default_superuser(self):
        su_role = Role.objects.get(name='superuser')
        self.user.assign_policies(su_role)
        response = self.request(user=self.user)
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 17
        assert response.content['recordsFiltered'] == 17

        resources = Resource.objects.all().order_by('name')[0:10]
        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet(resources))

    def test_get_default_superuser_plus_org_member(self):
        OrganizationRole.objects.create(user=self.user,
                                        organization=self.project.organization)
        su_role = Role.objects.get(name='superuser')
        self.user.assign_policies(su_role)
        response = self.request(user=self.user)
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 16
        assert response.content['recordsFiltered'] == 16

        resources = Resource.objects.filter(
            archived=False).order_by('name')[0:10]
        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet(resources))

    def test_get_default_org_member(self):
        OrganizationRole.objects.create(user=self.user,
                                        organization=self.project.organization)
        response = self.request(user=self.user)
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 16
        assert response.content['recordsFiltered'] == 16

        resources = Resource.objects.filter(
            archived=False).order_by('name')[0:10]
        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet(resources))

    def test_get_organization_does_not_exist(self):
        response = self.request(user=self.user,
                                url_kwargs={'organization': 'some-org'})
        assert response.status_code == 404
        assert response.content['detail'] == "Project not found."

    def test_get_project_does_not_exist(self):
        response = self.request(user=self.user,
                                url_kwargs={'project': 'some-prj'})
        assert response.status_code == 404
        assert response.content['detail'] == "Project not found."

    def test_get_with_unauthorized_user(self):
        response = self.request(user=self.user)
        assert response.status_code == 403

    def test_get_with_unauthenticated_user(self):
        response = self.request(user=None)
        assert response.status_code == 401

    def test_get_private_project(self):
        self.project.access = 'private'
        self.project.save()

        assign_policies(self.user)
        response = self.request(user=self.user)
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 16
        assert response.content['recordsFiltered'] == 16

        resources = Resource.objects.filter(
            archived=False).order_by('name')[0:10]
        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet(resources))

    def test_get_archived_project(self):
        self.project.archived = True
        self.project.save()

        assign_policies(self.user)
        response = self.request(user=self.user)
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 16
        assert response.content['recordsFiltered'] == 16

        resources = Resource.objects.filter(
            archived=False).order_by('name')[0:10]
        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet(resources))

    def test_get_search(self):
        assign_policies(self.user)
        response = self.request(user=self.user,
                                get_data={'search[value]': 'TestForSearch'})
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 16
        assert response.content['recordsFiltered'] == 1

        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet([self.search_resource]))

    def test_get_order_by_name(self):
        assign_policies(self.user)
        response = self.request(user=self.user,
                                get_data={'order[0][column]': 0,
                                          'order[0][dir]': 'asc'})
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 16
        assert response.content['recordsFiltered'] == 16

        resources = Resource.objects.filter(
            archived=False).order_by('name')[0:10]
        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet(resources))

    def test_get_inverse_order_by_name(self):
        assign_policies(self.user)
        response = self.request(user=self.user,
                                get_data={'order[0][column]': 0,
                                          'order[0][dir]': 'desc'})
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 16
        assert response.content['recordsFiltered'] == 16

        resources = Resource.objects.filter(
            archived=False).order_by('-name')[0:10]
        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet(resources))

    def test_get_with_length(self):
        assign_policies(self.user)
        response = self.request(user=self.user, get_data={'length': 25})
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 16
        assert response.content['recordsFiltered'] == 16

        resources = Resource.objects.filter(
            archived=False).order_by('name')
        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet(resources))

    def test_get_with_length_and_start(self):
        assign_policies(self.user)
        response = self.request(user=self.user,
                                get_data={'length': 15, 'start': 15})
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 16
        assert response.content['recordsFiltered'] == 16

        resources = Resource.objects.filter(
            archived=False).order_by('name')[15:16]
        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet(resources))


class PartyResourcesTest(APITestCase, UserTestCase, TestCase):
    view_class = ResourceList
    get_data = {'draw': '1', 'start': 0, 'length': 10, 'order[0][column]': 0}
    request_meta = {'HTTP_REFERER': 'http://example.com/'}

    def setup_models(self):
        self.user = UserFactory.create()
        self.project = ProjectFactory.create()
        self.party = PartyFactory.create(project=self.project)
        ResourceFactory.create_batch(10,
                                     project=self.project,
                                     content_object=self.party)
        ResourceFactory.create_batch(5,
                                     project=self.project)

    def setup_url_kwargs(self):
        return {
            'organization': self.project.organization.slug,
            'project': self.project.slug,
            'object_id': self.party.id
        }

    def render_html_snippet(self, resources):
        model_type = ContentType.objects.get_for_model(self.party)
        attachments = ContentObject.objects.filter(
            content_type__pk=model_type.id,
            object_id=self.party.id,
            resource_id__in=[resource.id for resource in resources]
        ).values_list('resource_id', 'id')
        attachment_id_dict = dict(attachments)

        for r in resources:
            r.attachment_id = attachment_id_dict.get(r.id)

        html = render_to_string(
            'resources/table_snippets/resource.html',
            context={'resources': resources,
                     'project': self.project,
                     'detatch_redirect': 'http://example.com/'},
            request=RequestFactory().get('/'))

        return remove_csrf(html)

    def test_get_default(self):
        assign_policies(self.user)
        response = self.request(user=self.user,
                                view_kwargs={'content_object': 'party.Party'})
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 10
        assert response.content['recordsFiltered'] == 10

        resources = self.party.resources.order_by('name')
        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet(resources))


class RelationshipResourcesTest(APITestCase, UserTestCase, TestCase):
    view_class = ResourceList
    get_data = {'draw': '1', 'start': 0, 'length': 10, 'order[0][column]': 0}
    request_meta = {'HTTP_REFERER': 'http://example.com/'}

    def setup_models(self):
        self.user = UserFactory.create()
        self.project = ProjectFactory.create()
        self.relationship = TenureRelationshipFactory.create(
            project=self.project)
        ResourceFactory.create_batch(10,
                                     project=self.project,
                                     content_object=self.relationship)
        ResourceFactory.create_batch(5,
                                     project=self.project)

    def setup_url_kwargs(self):
        return {
            'organization': self.project.organization.slug,
            'project': self.project.slug,
            'object_id': self.relationship.id
        }

    def render_html_snippet(self, resources):
        model_type = ContentType.objects.get_for_model(self.relationship)
        attachments = ContentObject.objects.filter(
            content_type__pk=model_type.id,
            object_id=self.relationship.id,
            resource_id__in=[resource.id for resource in resources]
        ).values_list('resource_id', 'id')
        attachment_id_dict = dict(attachments)

        for r in resources:
            r.attachment_id = attachment_id_dict.get(r.id)

        html = render_to_string(
            'resources/table_snippets/resource.html',
            context={'resources': resources,
                     'project': self.project,
                     'detatch_redirect': 'http://example.com/'},
            request=RequestFactory().get('/'))

        return remove_csrf(html)

    def test_get_default(self):
        assign_policies(self.user)
        response = self.request(
            user=self.user,
            view_kwargs={'content_object': 'party.TenureRelationship'})
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 10
        assert response.content['recordsFiltered'] == 10

        resources = self.relationship.resources.order_by('name')
        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet(resources))


class LocationResourcesTest(APITestCase, UserTestCase, TestCase):
    view_class = ResourceList
    get_data = {'draw': '1', 'start': 0, 'length': 10, 'order[0][column]': 0}
    request_meta = {'HTTP_REFERER': 'http://example.com/'}

    def setup_models(self):
        self.user = UserFactory.create()
        self.project = ProjectFactory.create()
        self.location = SpatialUnitFactory.create(
            project=self.project)
        ResourceFactory.create_batch(10,
                                     project=self.project,
                                     content_object=self.location)
        ResourceFactory.create_batch(5,
                                     project=self.project)

    def setup_url_kwargs(self):
        return {
            'organization': self.project.organization.slug,
            'project': self.project.slug,
            'object_id': self.location.id
        }

    def render_html_snippet(self, resources):
        model_type = ContentType.objects.get_for_model(self.location)
        attachments = ContentObject.objects.filter(
            content_type__pk=model_type.id,
            object_id=self.location.id,
            resource_id__in=[resource.id for resource in resources]
        ).values_list('resource_id', 'id')
        attachment_id_dict = dict(attachments)

        for r in resources:
            r.attachment_id = attachment_id_dict.get(r.id)

        html = render_to_string(
            'resources/table_snippets/resource.html',
            context={'resources': resources,
                     'project': self.project,
                     'detatch_redirect': 'http://example.com/'},
            request=RequestFactory().get('/'))

        return remove_csrf(html)

    def test_get_default(self):
        assign_policies(self.user)
        response = self.request(
            user=self.user,
            view_kwargs={'content_object': 'spatial.SpatialUnit'})
        assert response.status_code == 200
        assert response.content['draw'] == 1
        assert response.content['recordsTotal'] == 10
        assert response.content['recordsFiltered'] == 10

        resources = self.location.resources.order_by('name')
        assert (remove_csrf(response.content['tbody']) ==
                self.render_html_snippet(resources))