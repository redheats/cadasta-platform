from django.test import TestCase
from django.core.urlresolvers import reverse, resolve
from resources.views.async import ResourceList


class RessourceUrlTest(TestCase):
    def test_project_list(self):
        actual = reverse(
            'async:resources:list',
            kwargs={'organization': 'habitat', 'project': '123abc'}
        )
        expected = '/async/organizations/habitat/projects/123abc/resources/'
        assert actual == expected

        resolved = resolve(
            '/async/organizations/habitat/projects/123abc/resources/')
        assert resolved.func.__name__ == ResourceList.__name__
        assert resolved.kwargs['organization'] == 'habitat'
        assert resolved.kwargs['project'] == '123abc'

    def test_party_list(self):
        actual = reverse(
            'async:resources:party',
            kwargs={'organization': 'habitat', 'project': '123abc',
                    'object_id': '456def'}
        )
        expected = ('/async/organizations/habitat/projects/123abc/'
                    'parties/456def/resources/')
        assert actual == expected

        resolved = resolve('/async/organizations/habitat/projects/123abc/'
                           'parties/456def/resources/')
        assert resolved.func.__name__ == ResourceList.__name__
        assert resolved.kwargs['organization'] == 'habitat'
        assert resolved.kwargs['project'] == '123abc'
        assert resolved.kwargs['object_id'] == '456def'
        assert (resolved.func.view_initkwargs['content_object'] ==
                'party.Party')

    def test_location_list(self):
        actual = reverse(
            'async:resources:location',
            kwargs={'organization': 'habitat', 'project': '123abc',
                    'object_id': '456def'}
        )
        expected = ('/async/organizations/habitat/projects/123abc/'
                    'locations/456def/resources/')
        assert actual == expected

        resolved = resolve('/async/organizations/habitat/projects/123abc/'
                           'locations/456def/resources/')
        assert resolved.func.__name__ == ResourceList.__name__
        assert resolved.kwargs['organization'] == 'habitat'
        assert resolved.kwargs['project'] == '123abc'
        assert resolved.kwargs['object_id'] == '456def'
        assert (resolved.func.view_initkwargs['template'] ==
                'resources/table_snippets/resource_sm.html')
        assert (resolved.func.view_initkwargs['content_object'] ==
                'spatial.SpatialUnit')

    def test_relationship_list(self):
        actual = reverse(
            'async:resources:relationship',
            kwargs={'organization': 'habitat', 'project': '123abc',
                    'object_id': '456def'}
        )
        expected = ('/async/organizations/habitat/projects/123abc/'
                    'relationships/456def/resources/')
        assert actual == expected

        resolved = resolve('/async/organizations/habitat/projects/123abc/'
                           'relationships/456def/resources/')
        assert resolved.func.__name__ == ResourceList.__name__
        assert resolved.kwargs['organization'] == 'habitat'
        assert resolved.kwargs['project'] == '123abc'
        assert resolved.kwargs['object_id'] == '456def'
        assert (resolved.func.view_initkwargs['template'] ==
                'resources/table_snippets/resource_sm.html')
        assert (resolved.func.view_initkwargs['content_object'] ==
                'party.TenureRelationship')
