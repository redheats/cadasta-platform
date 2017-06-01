from django.template.loader import render_to_string
from tutelary.mixins import APIPermissionRequiredMixin
from jsonattrs.mixins import template_xlang_labels
from rest_framework import generics
from rest_framework.response import Response

from questionnaires.models import Question, QuestionOption


from . import mixins


class PartyList(APIPermissionRequiredMixin,
                mixins.PartyQuerySetMixin,
                generics.ListAPIView):
    columns = ('name', 'type', )

    def get_actions(self, request):
        if self.get_project().archived:
            return ['project.view_archived', 'party.list']
        if self.get_project().public():
            return ['project.view', 'party.list']
        else:
            return ['project.view_private', 'party.list']

    permission_required = {
        'GET': get_actions
    }

    def get_perms_objects(self):
        return [self.get_project()]

    def get_results(self):
        query = self.request.GET
        qs = self.get_queryset()

        records_total = qs.count()

        # filter the queryset if a search term was provided
        search = query.get('search[value]')
        if search:
            qs = qs.filter(name__contains=search)
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

        party_opts = {}
        project = self.get_project()
        if project.current_questionnaire:
            try:
                party_type = Question.objects.get(
                    name='party_type',
                    questionnaire_id=project.current_questionnaire)
                party_opts = QuestionOption.objects.filter(question=party_type)
                party_opts = dict(party_opts.values_list('name', 'label_xlat'))
            except Question.DoesNotExist:
                pass

        for party in qs:
            party.type_labels = template_xlang_labels(
                party_opts.get(party.type))

        return Response({
            'draw': int(self.request.GET.get('draw')),
            'recordsTotal': records_total,
            'recordsFiltered': records_filtered,
            'data': [],
            'tbody': render_to_string(
                'party/table_snippets/party.html',
                context={
                    'parties': qs,
                    'project': project
                },
                request=self.request)
        })
