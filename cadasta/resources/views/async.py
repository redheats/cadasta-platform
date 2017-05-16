from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.apps import apps
from tutelary.mixins import APIPermissionRequiredMixin
from rest_framework import generics
from rest_framework.response import Response
from organization.views.mixins import ProjectMixin
from core.views.mixins import SuperUserCheckMixin
from ..models import ContentObject


class ResourceList(APIPermissionRequiredMixin,
                   SuperUserCheckMixin,
                   ProjectMixin,
                   generics.ListAPIView):
    columns = ('name', 'mime_type', 'contributor__username', 'last_updated')
    content_object = 'organization.Project'
    template = 'resources/table_snippets/resource.html'

    use_resource_library_queryset = True

    def get_actions(self, request):
        if self.get_project().archived:
            return ['project.view_archived', 'resource.list']
        if self.get_project().public():
            return ['project.view', 'resource.list']
        else:
            return ['project.view_private', 'resource.list']

    permission_required = {
        'GET': get_actions
    }

    def get_queryset(self):
        if self.content_object == 'organization.Project':
            qs = self.get_project().resource_set.all().select_related(
                'contributor')
        else:
            qs = self.get_content_object().resources.all().select_related(
                'contributor')

        if not self.is_superuser or self.get_org_role() is not None:
            return qs.filter(archived=False)

        return qs

    def get_perms_objects(self):
        return [self.get_project()]

    def get_content_object(self):
        if self.content_object == 'organization.Project':
            return self.get_project()
        else:
            return get_object_or_404(
                apps.get_model(*self.content_object.split('.')),
                project__organization__slug=self.kwargs['organization'],
                project__slug=self.kwargs['project'],
                id=self.kwargs['object_id']
            )

    def get_results(self):
        query = self.request.GET
        qs = self.get_queryset()

        records_total = qs.count()
        # filter the queryset if a search term was provided
        search = query.get('search[value]')
        if search:
            qs = qs.filter(Q(name__contains=search) |
                           Q(original_file__contains=search) |
                           Q(mime_type__contains=search) |
                           Q(contributor__username__contains=search) |
                           Q(contributor__full_name__contains=search))
        records_filtered = qs.count()

        # set the ordering for the queryset
        order_col = int(query.get('order[0][column]', 0))
        order_dir = '' if query.get('order[0][dir]', 'asc') == 'asc' else '-'
        qs = qs.order_by(order_dir + self.columns[order_col])

        # Slice the queryset to results for the current page
        offset = int(query.get('start', 0))
        limit = int(query.get('length', 10)) + offset
        qs = qs[offset:limit]

        return qs, records_total, records_filtered

    def get(self, *args, **kwargs):
        qs, records_total, records_filtered = self.get_results()

        content_object = self.get_content_object()
        model_type = ContentType.objects.get_for_model(content_object)
        attachments = ContentObject.objects.filter(
            content_type__pk=model_type.id,
            object_id=content_object.id,
            resource_id__in=[resource.id for resource in qs]
        ).values_list('resource_id', 'id')
        attachment_id_dict = dict(attachments)

        for r in qs:
            r.attachment_id = attachment_id_dict.get(r.id)

        return Response({
            'draw': int(self.request.GET.get('draw')),
            'recordsTotal': records_total,
            'recordsFiltered': records_filtered,
            'data': [],
            'tbody': render_to_string(
                self.template,
                context={
                    'resources': qs,
                    'project': self.get_project(),
                    'detatch_redirect': self.request.META['HTTP_REFERER']
                },
                request=self.request)
        })
