from django.conf.urls import include, url

from ..views import async


urls = [
    url(
        r'^resources/$',
        async.ResourceList.as_view(),
        name='list'),
    url(
        r'^parties/(?P<object_id>[-\w]+)/resources/$',
        async.ResourceList.as_view(content_object='party.Party'),
        name='party'),
    url(
        r'^locations/(?P<object_id>[-\w]+)/resources/$',
        async.ResourceList.as_view(
            content_object='spatial.SpatialUnit',
            template='resources/table_snippets/resource_sm.html'),
        name='location'),
    url(
        r'^relationships/(?P<object_id>[-\w]+)/resources/$',
        async.ResourceList.as_view(
            content_object='party.TenureRelationship',
            template='resources/table_snippets/resource_sm.html'),
        name='relationship'),
]


urlpatterns = [
    url(
        r'^organizations/(?P<organization>[-\w]+)/projects/'
        '(?P<project>[-\w]+)/',
        include(urls)),
]
