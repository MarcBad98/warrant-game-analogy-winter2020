"""
    WG-A User Django Views

    This file contains WebSocket request handlers. When a web browser wants to connect via WebSocket (through
    JavaScript), the web browser sends an HTTP request for such a connection. If the server accepts the connection, data
    can then be sent between the web browser and server via WebSockets. The advantage of WebSocket connections over HTTP
    requests is that WebSocket connections are long-lived connections; we can send data back and forth, updating both
    the front-end and back-end without using methods such as HTTP polling. Each WebSocket Consumer in this file is
    associated with a URL path as defined in django_project/routing.py. WebSocket connections first go through the nginx
    web server, which is then passed to the Daphne server. Django Channels also requires a Redis server in order for
    Django's different layers to communicate with the Channels layer.

    DOCUMENTATION
    https://channels.readthedocs.io/en/latest/
"""

import logging
import json

from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.db.models import Q
from django.template.loader import render_to_string

from wga import models
from . import views
from . import forms


WGA_PLAYER_LOGGER = logging.getLogger('django.games')


########################################################################################################################


"""
    Navigation Bar CONSUMER
"""


class NavBarConsumer(WebsocketConsumer):

    def connect(self):
        try:
            user = models.User.objects.get(key=self.scope['session']['user_identifier'])
        except models.User.MultipleObjectsReturned:
            self.close()
            return
        async_to_sync(self.channel_layer.group_add)(user.key, self.channel_name)
        self.accept()

    def update_navigation(self, event):    
        if self.scope['url_route']['kwargs'].get('url_key'):
            if not models.Intermediary.objects.filter(user__key=self.scope['session']['user_identifier'], key=self.scope['url_route']['kwargs']['url_key']).exists():
                return
        elif self.scope['session'].get('user_identifier'):
            if not models.User.objects.filter(key=self.scope['session']['user_identifier']).exists():
                return
        else:
            return

        data = views.find_user_data(url_key=self.scope['session']['user_identifier'])
        self.send(text_data=json.dumps({
            'html-navigation': render_to_string('wga/user/container/links.html', data)
        }))

    def disconnect(self, message):
        try:
            user = models.User.objects.get(key=self.scope['session']['user_identifier'])
        except models.User.MultipleObjectsReturned:
            self.close()
            return
        async_to_sync(self.channel_layer.group_discard)(user.key, self.channel_name)
        self.close()


########################################################################################################################


"""
    Game CONSUMER
    
    Django Channels consumer responsible for handling data in (both control and non-control) games via WebSockets. The
    four important functionalities of this consumer: (1) Receiving and recording time data, (2) Receiving and processing
    non-control form data, (3) Updating the mTurk worker's interface, and (4) Updating the mTurk worker's navigation
    bar.
"""


class GameConsumer(WebsocketConsumer):

    def connect(self):
        try:
            intermediary = models.Intermediary.objects.get(key=self.scope['url_route']['kwargs']['url_key'])
        except models.Intermediary.MultipleObjectsReturned:
            self.close()
            return
        async_to_sync(self.channel_layer.group_add)(intermediary.key, self.channel_name)
        async_to_sync(self.channel_layer.group_add)(intermediary.user.group.name, self.channel_name)
        self.accept()

    def receive(self, text_data):
        text_data = json.loads(text_data)
        data = views.find_game_data(url_key=self.scope['url_route']['kwargs']['url_key'])
        if text_data.get('time'):
            data['intermediary'].time += float(text_data['time'])
            data['intermediary'].save()
        else:
            data['form'] = forms.build_form(text_data, user=data['user'], game=data['game'], is_critic=data['is_critic'])
            if data['form'].is_valid():
                data['form'].process()
                for intermediary in models.Intermediary.objects.filter(Q(user=data['game'].adv_info.user) | Q(user=data['game'].crt_info.user)):
                    self._update_page(intermediary=intermediary)
            else:
                self.send(text_data=json.dumps({
                    'html-interface': render_to_string('wga/user/game/interface.html', data)
                }))

    def _update_page(self, intermediary):
        async_to_sync(self.channel_layer.group_send)(
            intermediary.key,
            {
                'type': 'update.interface'
            }
        )
        async_to_sync(self.channel_layer.group_send)(
            intermediary.user.key,
            {
                'type': 'update.navigation'
            }
        )

    def update_interface(self, event):
        if not models.Intermediary.objects.filter(user__key=self.scope['session']['user_identifier'], key=self.scope['url_route']['kwargs']['url_key']).exists():
            self.send(text_data=json.dumps({
                'html-interface': "An administrator has made changes here. Please navigate back to the login page."
            }))
            return

        data = views.find_game_data(url_key=self.scope['url_route']['kwargs']['url_key'])
        if not views.is_turn(data):
            data['game'].context = 'Not Turn'  # DO NOT SAVE
        data['form'] = forms.build_form(user=data['user'], game=data['game'], is_critic=data['is_critic'])
        if data['user'].group.case == models.Group.Case.NON_CONTROL:
            self.send(text_data=json.dumps({
                'html-interface': render_to_string('wga/user/game/interface.html', data)
            }))
        elif data['user'].group.case == models.Group.Case.CONTROL:
            self.send(text_data=json.dumps({
                'html-interface': render_to_string('wga/user/chat/interface.html', data)
            }))

    def update_messages(self, event):
        self.send(text_data=json.dumps({
            'message': event['message']
        }))

    def disconnect(self, message):
        try:
            intermediary = models.Intermediary.objects.get(key=self.scope['url_route']['kwargs']['url_key'])
        except models.Intermediary.MultipleObjectsReturned:
            self.close()
            return
        async_to_sync(self.channel_layer.group_discard)(intermediary.key, self.channel_name)
        async_to_sync(self.channel_layer.group_discard)(intermediary.user.group.name, self.channel_name)
        self.close()


########################################################################################################################
