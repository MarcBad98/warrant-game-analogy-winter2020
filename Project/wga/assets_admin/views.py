"""
    WG-A Admin Django Views

    This file contains HTTP request handlers. Each view is invoked by navigating to its associated URL (as set in the
    URLconf files). HTTP requests first go through the nginx web server, which is then passed to the Gunicorn server.
    The Gunicorn server then matches the URL with those in the URLconf and invokes the associated URL.

    DOCUMENTATION
    https://docs.djangoproject.com/en/2.2/topics/http/views/
"""

import logging
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View, CreateView, UpdateView, ListView, DetailView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.template.loader import render_to_string
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from django_project.settings import TIME_ZONE
from wga import models
from . import forms


WGA_ADMIN_LOGGER = logging.getLogger('django.moderator')
CHANNEL_LAYER = get_channel_layer()


########################################################################################################################


"""
    Index VIEW
    
    Django view that handles HTTP requests for the administrator landing page after logging in via Django's default
    admin login. The web page shows all scenarios registered in the database as well as allows administrators to create
    new game sessions.
"""


class IndexView(LoginRequiredMixin, CreateView):

    login_url = '/admin/'
    success_url = reverse_lazy('moderator:list-of-groups')
    template_name = 'wga/admin/index.html'
    form_class = forms.CreateGroupForm

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['scenarios'] = models.ScenarioPair.objects.all()
        return context


########################################################################################################################


"""
    Group List & Detail VIEWS
    
    Django view that handles HTTP requests for web pages responsible for showing information about game sessions. The
    Group List VIEW responds with a web page listing out all the game sessions found in the database; the Group Detail
    VIEW responds with a web page listing out all the games encompassed by the game session.
"""


class GroupListView(LoginRequiredMixin, ListView):

    login_url = '/admin/'
    template_name = 'wga/admin/group_list.html'
    model = models.Group


class GroupDetailView(LoginRequiredMixin, DetailView):

    login_url = '/admin/'
    template_name = 'wga/admin/group_detail.html'
    model = models.Group

    def get_object(self):
        return get_object_or_404(models.Group, name=self.kwargs['group_name'])


########################################################################################################################


"""
    Add Game VIEW
    
    Django view that handles HTTP requests for the add game form. Before the administrator can submit the form,
    JavaScript invokes the Check Add Game view (only through POST requests) to send warnings: has the selected player(s)
    played the chosen scenario already?
"""


class AddGameView(LoginRequiredMixin, CreateView):

    login_url = '/admin/'
    success_url = reverse_lazy('moderator:list-of-groups')
    template_name = 'wga/admin/add_game.html'
    form_class = forms.AddGameForm

    def get_form_kwargs(self, *args, **kwargs):
        arguments = super().get_form_kwargs(*args, **kwargs)
        arguments['group'] = get_object_or_404(models.Group, name=self.kwargs['group_name'])
        return arguments

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['group'] = get_object_or_404(models.Group, name=self.kwargs['group_name'])
        return context


class CheckAddGameView(LoginRequiredMixin, View):

    login_url = '/admin'

    def post(self, request, **kwargs):
        group = get_object_or_404(models.Group, name=kwargs['group_name'])
        response = {'adv': False, 'crt': False}

        s, a, c = request.POST.get('scenario'), request.POST.get('advocate'), request.POST.get('critic')
        if s and (a or c):
            if a:
                query = Q(group=group) & Q(scenario__id=s) & (Q(adv_info__user__id=a) | Q(crt_info__user__id=a))
                response['adv'] = models.Game.objects.filter(query).exists()
            if c:
                query = Q(group=group) & Q(scenario__id=s) & (Q(adv_info__user__id=c) | Q(crt_info__user__id=c))
                response['crt'] = models.Game.objects.filter(query).exists()

        return JsonResponse(response)


########################################################################################################################


"""
    Shuffle Games VIEW
    
    Django view that handles HTTP requests for the shuffle game form.
"""


class ShuffleGamesView(LoginRequiredMixin, CreateView):

    login_url = '/admin/'
    success_url = reverse_lazy('moderator:list-of-groups')
    template_name = 'wga/admin/shuffle.html'
    form_class = forms.ShuffleGamesForm

    def get_form_kwargs(self, *args, **kwargs):
        arguments = super().get_form_kwargs(*args, **kwargs)
        arguments['group'] = get_object_or_404(models.Group, name=self.kwargs['group_name'])
        return arguments

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['group'] = get_object_or_404(models.Group, name=self.kwargs['group_name'])
        return context


########################################################################################################################


"""
    Download VIEW
    
    Django view that handles HTTP requests for downloading JSON data for each group. You can extract all relevant data
    here, but you should also make back-ups of the database by running these Django-level commands:
    
    python manage.py dumpdata --exclude auth.permission --exclude contenttypes --indent 4 > db.json
    
        AND / OR
        
    python manage.py dumpdata wga --indent 4 > wga.json
"""


class DownloadView(LoginRequiredMixin, View):

    login_url = '/admin/'

    def get(self, request, **kwargs):
        group = get_object_or_404(models.Group, name=kwargs['group_name'])

        # HTML Data
        for game in models.Game.objects.filter(group=group):
            with open(f"wga/game_sessions/games/{game.context}/{game.id}.html", 'w+') as file:
                file.write(render_to_string('wga/user/post-game/post_game.html', {'game': game}))
        with open(f"wga/game_sessions/games/{group.name}.csv", 'w+') as file:
            for user in models.User.objects.filter(group=group):
                file.write(f"{user.name},{user.key},{user.log_in},{user.approved}\n")

        # JSON Data
        data = {
            'session': group.name,
            'created': group.date.__str__(),
            'timezone': TIME_ZONE,
            'announcements': [
                {
                    'text': message.text,
                    'date': message.date.__str__(),
                    'time': message.date.strftime("%H:%M:%S"),
                }
                for message in group.messages.all()
            ],
            'games': [
                {
                    'name': game.__str__(),
                    'scenario': {
                        'name': game.scenario.name,
                        'source conclusion': game.scenario.source_conclusion,
                        'target conclusion': game.scenario.target_conclusion,
                    },
                    'advocate': {
                        'name': game.adv_info.user.name,
                        'user key': game.adv_info.user.key,
                        'assigned': game.adv_info.user.assigned,
                        'approved': game.adv_info.user.approved,
                        'game key': game.adv_info.key,
                        'time': game.adv_info.time,
                        'messages': [message.text for message in (game.adv_info.messages.all() | group.messages.all()).order_by('date')]
                    },
                    'critic': {
                        'name': game.crt_info.user.name,
                        'user key': game.crt_info.user.key,
                        'assigned': game.crt_info.user.assigned,
                        'approved': game.crt_info.user.approved,
                        'game key': game.crt_info.key,
                        'time': game.crt_info.time,
                        'messages': [message.text for message in (game.crt_info.messages.all() | group.messages.all()).order_by('date')]
                    },
                    'rule': {
                        'name': "IF " + game.rule_antecedent + ", THEN " + game.rule_consequent,
                        'antecedent': game.rule_antecedent,
                        'consequent': game.rule_consequent
                    },
                    'turn': game.turn,
                    'facts': [
                        {
                            'source fact': fact.source_fact,
                            'target fact': fact.target_fact
                        }
                        for fact in game.factpair_set.all()
                    ],
                    'moves': [
                        {
                            'user': move.user.name,
                            'date': move.date.__str__(),
                            'time': move.date.strftime("%H:%M:%S"),
                            'code': move.code,
                            'text': move.text
                        }
                        for move in game.move_set.all()],
                    'reports': [
                        {
                            'user': report.user.name if report.user else None,
                            'date': report.date.__str__(),
                            'time': report.date.strftime("%H:%M:%S"),
                            'game': report.game.__str__(),
                            'report description': report.text,
                            'administrator comment': report.note,
                            'returned': report.returned
                        }
                        for report in game.report_set.all()]
                }
                for game in group.game_set.all()
            ]
        }
        response = HttpResponse(json.dumps(data, indent=4), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename=' + group.name + '.json'
        WGA_ADMIN_LOGGER.info(f"Downloaded JSON data for \"{group.name}\"")
        return response


########################################################################################################################


"""
    Message VIEW
    
    Django view that handles HTTP requests for sending one-way messages from the administrators to the mTurk workers.
    The returned web pages include the messages and announcements sent to players as well as a form to send such
    messages.
"""


class MessageCreateView(LoginRequiredMixin, CreateView):

    login_url = '/admin/'
    success_url = reverse_lazy('moderator:list-of-groups')
    template_name = 'wga/admin/message.html'
    form_class = forms.SendMessageForm

    def get_form_kwargs(self, *args, **kwargs):
        arguments = super().get_form_kwargs(*args, **kwargs)
        if self.kwargs['url_key'] == 'announcement':
            arguments['object'] = get_object_or_404(models.Group, name=self.kwargs['group_name'])
        else:
            arguments['object'] = get_object_or_404(models.Intermediary, key=self.kwargs['url_key'])
        return arguments

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['announcement'] = self.kwargs['url_key'] == 'announcement'
        if context['announcement']:
            context['object'] = get_object_or_404(models.Group, name=self.kwargs['group_name'])
        else:
            context['object'] = get_object_or_404(models.Intermediary, key=self.kwargs['url_key'])
        return context


########################################################################################################################


"""
    Intermediary Update VIEW
"""


class IntermediaryUpdateView(LoginRequiredMixin, UpdateView):

    login_url = '/admin/'
    model = models.Intermediary
    fields = ('user', )
    template_name = 'wga/admin/intermediary_update.html'

    def get_object(self):
        intermediary = get_object_or_404(models.Intermediary, key=self.kwargs['url_key'])
        self.previous_user = intermediary.user
        return intermediary

    def form_valid(self, form):
        intermediary = form.save()
        for intermediary in self.previous_user.intermediary_set.all() | self.object.user.intermediary_set.all():
            async_to_sync(CHANNEL_LAYER.group_send)(
                intermediary.key,
                {
                    'type': 'update.interface'
                }
            )
            async_to_sync(CHANNEL_LAYER.group_send)(
                intermediary.user.key,
                {
                    'type': 'update.navigation'
                }
            )
        return redirect(reverse_lazy('moderator:group', kwargs={'group_name': intermediary.user.group.name}))


########################################################################################################################


"""
    Report List & Resolve VIEWS
    
    Django views that handle HTTP requests for web pages responsible for showing information about reports. The Report
    List VIEW responds with a web page containing all the reports found in the database; the Resolve VIEW responds with
    a web page containing a form for the administrator to comment on the report.
"""


class ReportListView(LoginRequiredMixin, ListView):

    login_url = '/admin/'
    template_name = 'wga/admin/report_list.html'
    model = models.Report


class ReportResolveView(LoginRequiredMixin, UpdateView):

    login_url = '/admin/'
    success_url = reverse_lazy('moderator:list-of-reports')
    template_name = 'wga/admin/report_resolve.html'
    form_class = forms.ReportResolveForm

    def get_object(self):
        return get_object_or_404(models.Report, id=self.kwargs['report_id'])

    def get_form_kwargs(self, *args, **kwargs):
        arguments = super().get_form_kwargs(*args, **kwargs)
        arguments['report'] = self.object
        return arguments
        
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['moves'] = list(self.object.game.move_set.all().order_by('date'))
        return context


########################################################################################################################
