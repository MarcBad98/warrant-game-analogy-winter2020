"""
    WG-A Admin Django Forms

    This file contains all the forms for the WG-A Admin web pages. Django forms render the necessary HTML elements to
    render HTML forms; rather than having the front-end developer manually write the HTML for forms, Django offers form
    objects that makes HTML forms more maintainable.

    DOCUMENTATION
    https://docs.djangoproject.com/en/2.2/topics/forms/
"""

import logging
import os

from django import forms
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from wga import models


WGA_ADMIN_LOGGER = logging.getLogger('django.moderator')
WGA_GAME_LOGGER = logging.getLogger('django.games')
CHANNEL_LAYER = get_channel_layer()


########################################################################################################################


"""
    Create Group FORM
    
    Django form for creating new Group objects. Here, we do form validations to ensure that game generation works
    without raising exceptions.
    
    VALIDATIONS
        --- name                :: ensure all groups have unique names
        --- name                :: ensure CSV file of code names exists
        --- num_users           :: ensure enough users for 2-player games       >> (num_users * num_games) % 2 == 0
        --- num_games           :: ensure enough users for 2-player games       >> (num_users * num_games) % 2 == 0
        --- scenarios           :: ensure enough scenarios for 2-player games   >> num_scenarios >= (2 * num_games) - 1 
"""


class CreateGroupForm(forms.ModelForm):

    class Meta:
        model = models.Group
        fields = ('name', 'case', 'start', 'num_users', 'num_games', 'scenarios')
        labels = {
            'name': "Game Session Name",
            'case': "Control or Non-control Case",
            'start': "Start Date (mm/dd/yyyy hh:mm >> UTC-05:00)",
            'num_users': "Number of mTurk Workers",
            'num_games': "Number of Games for Each mTurk Worker",
            'scenarios': "Choose Which Scenarios to Include"
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['num_games'].widget.attrs.update({'min': 1, 'max': 5})
        self.fields['start'].input_formats = ['%m/%d/%Y %H:%M']  # '10/25/2006 14:30' === 10/25/2006 09:30am EST

    def clean_name(self):
        return self.cleaned_data['name'].replace(' ', '')

    def clean(self):
        super().clean()
        data = self.cleaned_data

        if data.get('name'):
            if models.Group.objects.filter(name=data['name']):
                self.add_error('name', forms.ValidationError("Name already taken"))
                WGA_ADMIN_LOGGER.debug(f"Invalid form: Name already taken. {data}")

        if data.get('name'):
            if not os.path.isfile(f"wga/game_sessions/{data['name']}.csv"):
                self.add_error('name', forms.ValidationError("CSV file does not exist"))
                WGA_ADMIN_LOGGER.debug("Invalid form: CSV file does not exist")
            else:
                with open(f"wga/game_sessions/{data['name']}.csv", 'r') as file:
                    rows = sum(1 for _ in file)
                if rows < data['num_users']:
                    self.add_error('name', forms.ValidationError("CSV file contains too few code names"))
                    WGA_ADMIN_LOGGER.debug("Invalid form: CSV file contains too few code names")
                elif rows > data['num_users']:
                    self.add_error('name', forms.ValidationError("CSV file contains too many code names"))
                    WGA_ADMIN_LOGGER.debug("Invalid form: CSV file contains too many code names")

        if data.get('num_users') and data.get('num_games'):
            if data['num_users'] * data['num_games'] % 2 != 0:
                self.add_error('num_users', forms.ValidationError("Required: (num_users * num_games) % 2 == 0"))
                self.add_error('num_games', forms.ValidationError("Required: (num_users * num_games) % 2 == 0"))
                WGA_ADMIN_LOGGER.debug(f"Invalid form: Required: (num_users * num_games) % 2 == 0. {data}")

        if data.get('scenarios') and data.get('num_games'):
            if data['scenarios'].count() < 2 * data['num_games'] - 1:
                self.add_error('scenarios', forms.ValidationError("Required: num_scenarios >= (2 * num_games) - 1"))
                WGA_ADMIN_LOGGER.debug(f"Invalid form: Required: num_scenarios >= (2 * num_games) - 1. {data}")

        return self.cleaned_data

    def save(self, *args, **kwargs):
        data = self.cleaned_data
        WGA_ADMIN_LOGGER.debug(f"Valid form passed: {data}")
        group = super().save(*args, **kwargs)
        group.generate_games()
        return group


########################################################################################################################


"""
    Add Game FORM
    
    Django form for adding new games to already existing groups.

    VALIDATIONS
        --- advocate            :: ensure advocate & critic are not the same mTurk worker
        --- critic              :: ensure advocate & critic are not the same mTurk worker
"""


class AddGameForm(forms.ModelForm):

    class Meta:
        model = models.Game
        fields = ('scenario', )

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group')
        super().__init__(*args, **kwargs)
        users = models.User.objects.filter(group=self.group)
        self.fields['advocate'] = forms.ModelChoiceField(users)
        self.fields['critic'] = forms.ModelChoiceField(users)

    def clean(self):
        super().clean()
        data = self.cleaned_data

        if data['advocate'] == data['critic']:
            self.add_error('advocate', forms.ValidationError("Player cannot play both roles!"))
            self.add_error('critic', forms.ValidationError("Player cannot play both roles!"))
            WGA_ADMIN_LOGGER.debug(f"Invalid form: Advocate and Critic cannot be the same player. {data}")

        return self.cleaned_data

    def save(self):
        data = self.cleaned_data
        WGA_ADMIN_LOGGER.debug(f"Valid form passed: {data}")

        game = self.group.add_game(scenario=data['scenario'], advocate=data['advocate'], critic=data['critic'])

        # TODO: Test to make sure the update goes through
        for intermediary in data['advocate'].intermediary_set.all() | data['critic'].intermediary_set.all():
            async_to_sync(CHANNEL_LAYER.group_send)(
                intermediary.user.key,
                {
                    'type': 'update.navigation'
                }
            )
        return game


########################################################################################################################


"""
    Shuffle Games FORM
    
    Django form for shuffling mTurk workers within a control group. The administrators will use this feature after every
    15 minutes to ensure that mTurk workers are continually collaborating on scenarios (prevent situations where two
    mTurk workers have resolved the scenario faster than anyone else could).
"""


class ShuffleGamesForm(forms.ModelForm):

    class Meta:
        model = models.Group
        fields = ('name', )

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group')
        super().__init__(*args, **kwargs)
        self.fields['name'].required = False
        self.fields['name'].widget.attrs.update({'readonly': True, 'placeholder': self.group.name})

    def save(self):
        data = self.cleaned_data
        WGA_ADMIN_LOGGER.debug(f"Valid form passed: {data}")

        self.group.shuffle()

        # TODO: Test to make sure the update goes through
        for intermediary in models.Intermediary.objects.filter(user__group=self.group):
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
        return self.group


########################################################################################################################


"""
    Send Message FORM

    Django form for sending messages / announcements from the administrators to the mTurk workers.
"""


class SendMessageForm(forms.ModelForm):

    class Meta:
        model = models.Message
        fields = ('text', )
        labels = {
            'text': "What message will you send?"
        }

    def __init__(self, *args, **kwargs):
        self.object = kwargs.pop('object')  # Object is either a Group or Intermediary object
        super().__init__(*args, **kwargs)

    def save(self):
        data = self.cleaned_data
        WGA_ADMIN_LOGGER.debug(f"Valid form passed: {data}")

        label = "[ANNOUNCEMENT] " if isinstance(self.object, models.Group) else "[MESSAGE] "
        message = models.Message.objects.create(text=label+data['text'])
        self.object.messages.add(message)

        # TODO: Test to make sure the update goes through
        async_to_sync(CHANNEL_LAYER.group_send)(
            self.object.name if isinstance(self.object, models.Group) else self.object.key,
            {
                'type': 'update.messages',
                'message': message.text
            }
        )
        return message


########################################################################################################################


"""
    Report Resolve FORM

    Django form for resolving reports sent to the administrators.
"""


class ReportResolveForm(forms.ModelForm):

    class Meta:
        model = models.Report
        fields = ('note', 'returned')
        labels = {
            'note': "What are your comments about this report?",
            'returned': "After resolving, which player will continue the game?"
        }

    def __init__(self, *args, **kwargs):
        self.report = kwargs.pop('report')
        super().__init__(*args, **kwargs)

    def save(self):
        data = self.cleaned_data
        WGA_ADMIN_LOGGER.debug(f"Valid form passed; {data}")

        self.report.note = data['note']
        self.report.returned = data['returned']
        self.report.resolved = True
        self.report.save()

        self.report.game.turn = self.report.returned
        self.report.game.context = models.Game.Context.COMPLETED if self.report.game.turn == models.Game.Turn.COMPLETED else models.Game.Context.IDLE
        self.report.game.set_context_data([])

        text = f"The moderator has reviewed the complaint: \"{self.report.note}\""
        self.report.game.add_move(user=self.report.user, code=models.Move.Code.REPORT_REVIEWED, text=text)
        WGA_GAME_LOGGER.info(f"[{self.report.user.key}] Processed {models.Move.Code.REPORT_REVIEWED}: \"{text}\"")

        # TODO: Test to make sure the update goes through
        for intermediary in [self.report.game.adv_info, self.report.game.crt_info]:
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
        return self.report


########################################################################################################################
