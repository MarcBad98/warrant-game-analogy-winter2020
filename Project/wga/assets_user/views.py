"""
    WG-A User Django Views

    This file contains HTTP request handlers. Each view is invoked by navigating to its associated URL (as set in the
    URLconf files). HTTP requests first go through the nginx web server, which is then passed to the Gunicorn server.
    The Gunicorn server then matches the URL with those in the URLconf and invokes the associated URL.

    DOCUMENTATION
    https://docs.djangoproject.com/en/2.2/topics/http/views/
"""

import logging

from django.views.generic import View, FormView
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from wga import models
from . import forms


WGA_PLAYER_LOGGER = logging.getLogger('django.games')


########################################################################################################################


"""
    Find User Data HELPER FUNCTION
    
    Takes in a User identifier key. Returns a dictionary of all relevant information about the User object
    (specifically, the User object itself, its associated Game objects, and its associated Intermediary objects).
"""


def find_user_data(url_key):
    user = get_object_or_404(models.User, key=url_key)
    return {
        'user': user,
        'games_a': models.Game.objects.filter(adv_info__user=user),
        'games_b': models.Game.objects.filter(Q(adv_info__user=user) | Q(crt_info__user=user)),
        'games_c': models.Game.objects.filter(crt_info__user=user),
        'intermediaries_a': models.Intermediary.objects.filter(user=user, role=models.Intermediary.Role.ADVOCATE),
        'intermediaries_b': models.Intermediary.objects.filter(user=user),
        'intermediaries_c': models.Intermediary.objects.filter(user=user, role=models.Intermediary.Role.CRITIC),
        'intermediaries_chat': models.Intermediary.objects.filter(user=user, role=models.Intermediary.Role.INTERLOCUTOR)
    }


"""
    Find Game Data HELPER FUNCTION
    
    Takes in an Intermediary identifier key. Returns a dictionary of all relevant information about the Intermediary
    object (specifically, the Intermediary object itself, its associated Game object, its associated User object, and a
    Boolean value indicating the User's role).
"""


def find_game_data(url_key):
    intermediary = get_object_or_404(models.Intermediary, key=url_key)
    game = intermediary.criticism if hasattr(intermediary, 'criticism') else intermediary.advocacy
    data = find_user_data(url_key=intermediary.user.key)
    data.update({
        'intermediary': intermediary,
        'game': game,
        'moves': list(game.move_set.all().order_by('date')),
        'messages': list((intermediary.user.group.messages.all() | intermediary.messages.all()).order_by('date')),
        'user': intermediary.user,
        'is_critic': intermediary.role == models.Intermediary.Role.CRITIC
    })
    return data


"""
    Is Turn HELPER FUNCTION
    
    Takes in a dictionary returned by the find_game_data() method. Returns a Boolean value indicating whether its the
    mTurk worker's turn or not.
"""


def is_turn(data):
    turn_as_crt = data['is_critic'] and data['game'].turn == models.Game.Turn.CRITIC
    turn_as_adv = not data['is_critic'] and data['game'].turn == models.Game.Turn.ADVOCATE
    return turn_as_crt or turn_as_adv


########################################################################################################################


"""
    Login VIEW
    
    Django view responsible for showing the mTurk worker the user login page. This web page is intended to identify
    the mTurk worker using their user name and key (to ensure that the visitor is actually an mTurk worker, and to
    figure out which set of instructions to display: control or non-control).
"""


class LoginView(FormView):

    success_url = reverse_lazy('user:instructions')
    template_name = 'wga/user/login.html'
    form_class = forms.LoginForm

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        if self.request.session.get('user_identifier'):
            data = find_user_data(url_key=self.request.session['user_identifier'])
            context.update(data)
        return context

    def form_valid(self, form):
        WGA_PLAYER_LOGGER.debug(f"[{form.cleaned_data['key']}] Login succeeded: {form.cleaned_data}")
        user = models.User.objects.get(name=form.cleaned_data['name'])
        user.assigned = True
        user.log_in = timezone.now()
        user.save()
        self.request.session['user_identifier'] = user.key
        self.request.session.set_expiry(int(timezone.timedelta(hours=2).total_seconds()))
        with open(f"wga/game_sessions/{user.group.name}.csv", 'w+') as file:
            for user in user.group.user_set.all():
                file.write(f"{user.name},{user.key},{user.log_in}\n")
        return super().form_valid(form)


########################################################################################################################


"""
    Instructions VIEW
    
    Django view responsible for showing the mTurk worker the user instructions page. This web page is intended to give
    them instructions on how to play the game: the control group receives written instructions about the chat room
    whereas the non-control group receives a video about the Warrant Game: Analogy interface. If the mTurk worker
    is in the non-control group, then they must enter a password after watching the instructional video to continue
    with the study (to ensure the mTurk worker watched the video).
"""


class InstructionsView(FormView):

    success_url = reverse_lazy('user:instructions')
    template_name = 'wga/user/instructions.html'
    form_class = forms.InstructionsForm

    def get_form_kwargs(self, *args, **kwargs):
        arguments = super().get_form_kwargs(*args, **kwargs)
        if self.request.session.get('user_identifier'):
            data = find_user_data(url_key=self.request.session['user_identifier'])
            arguments['user'] = data['user']
        else:
            WGA_PLAYER_LOGGER.warning(f"Request lacks session data.")
            raise Http404("Login Credentials Missing")
        return arguments

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        if self.request.session.get('user_identifier'):
            data = find_user_data(url_key=self.request.session['user_identifier'])
            context.update(data)
        else:
            WGA_PLAYER_LOGGER.warning(f"Request lacks session data.")
            raise Http404("Login Credentials Missing")
        return context

    def form_valid(self, form):
        WGA_PLAYER_LOGGER.debug(f"[{self.request.session['user_identifier']}] Login succeeded: {form.cleaned_data}")
        user = models.User.objects.get(key=self.request.session['user_identifier'])
        user.approved = True
        user.save()
        self.request.session['ready'] = True
        return super().form_valid(form)


########################################################################################################################


"""
    Frequently Asked Questions VIEW
    
    Django view responsible for displaying the FAQ web page. This web page contains a list of frequently asked
    questions. For the pilot study, the FAQ web page was left blank (since this was the first time the study went
    online). A chat room is embedded on this web page so that mTurk workers can contact the administrators during their
    games; however, they cannot contact the administrators this way if they are having trouble logging in.
"""


class FAQView(View):

    def get(self, request):
        data = {}
        if request.session.get('user_identifier'):
            data = find_user_data(url_key=request.session['user_identifier'])
        return render(request, 'wga/user/faq.html', data)


########################################################################################################################


"""
    Game VIEW
    
    Django view responsible for displaying the proper user game depending on if the game is a control or non-control
    group. The control group will see their scenario as text with an embedded chat room to interact with the other
    mTurk worker. The non-control group will see the argument structure and the appropriate move forms to make
    structured attacks and defenses.
"""


@method_decorator(csrf_exempt, name='dispatch')
class GameView(View):

    def get(self, request, **kwargs):
        if request.session.get('user_identifier') and models.Intermediary.objects.filter(user__key=request.session.get('user_identifier'), key=kwargs['url_key']).exists():
            data = find_game_data(url_key=kwargs['url_key'])
            if not is_turn(data):
                data['game'].context = 'Not Turn'  # DO NOT SAVE
            data['form'] = forms.build_form(user=data['user'], game=data['game'], is_critic=data['is_critic'])
            return render(request, 'wga/user/game.html', data)
        else:
            WGA_PLAYER_LOGGER.warning(f"Request lacks session data.")
            raise Http404("Login Credentials Missing")


########################################################################################################################
