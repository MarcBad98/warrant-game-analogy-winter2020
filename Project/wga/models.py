"""
    WG-A Django Models

    This file contains all the models needed to operate the control and non-control cases. The Django model layer is
    essentially a representation of a database (which database you use is defined in settings.py). This layer allows
    our application to communicate with the database back-end. In our case, we are using a PostgreSQL database to better
    handle concurrent access (as opposed to SQLite, which was used during development).

    DOCUMENTATION
    https://docs.djangoproject.com/en/2.2/topics/db/models/
"""

import logging
import random
import datetime
import string
import csv

from django.db import models
from django.db.models import Q
from django.utils import timezone


WGA_ADMIN_LOGGER = logging.getLogger('django.moderator')


########################################################################################################################


"""
    Create Key HELPER FUNCTION
    
    Returns a 20 character long key value that can be used for Intermediary and User objects without raising a UNIQUE
    constraint IntegrityError exception. Keys are used to uniquely identify games slots and users.
"""


def create_key():
    random.seed(datetime.datetime.now().second)
    key = ''.join([random.choice(string.ascii_lowercase + string.digits) for _ in range(20)])
    while Intermediary.objects.filter(key=key).exists() or User.objects.filter(key=key).exists():
        key = ''.join([random.choice(string.ascii_lowercase + string.digits) for _ in range(20)])
    return key


########################################################################################################################


"""
    User MODEL
    
    Django model representing mTurk workers. Rather than using Django's User model in the auth middleware, we opt to
    use our own Django model so that we ensure anonymity (this model does not have any fields that could store
    potentially identifying data).

    FIELDS
        --- group               :: the mTurk worker's assigned game session
        --- name                :: the mTurk worker's username (code name) entered in the mTurk HIT
        --- key                 :: the mTurk worker's login key, a unique 20 character identifier

    METHODS
        --- get_status          :: returns a dictionary with the total number of active, moderated, and completed games
"""


class User(models.Model):

    group = models.ForeignKey('wga.Group', null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=64)
    key = models.CharField(max_length=20, unique=True, default=create_key)
    log_in = models.DateTimeField(blank=True, null=True)
    assigned = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return self.name


########################################################################################################################


"""
    FactPair MODEL
    
    Django model representing facts in a ScenarioPair and Game object. Each FactPair requires a fact for both source
    and target domains.
    
    FIELDS
        --- game                :: the associated Game object (leave blank / null when creating ScenarioPairs)
        --- source_fact         :: text for the source fact
        --- target_fact         :: text for the target fact
"""


class FactPair(models.Model):

    game = models.ForeignKey('wga.Game', blank=True, null=True, on_delete=models.SET_NULL)
    source_fact = models.CharField(max_length=1024)
    target_fact = models.CharField(max_length=1024)

    def __str__(self):
        return f"{self.source_fact} | {self.target_fact}"


########################################################################################################################


"""
    ScenarioPair MODEL

    Django model representing scenarios. These scenarios can be used for both the control as well as non-control cases.

    FIELDS
        --- name                :: text description of the scenario
        --- facts               :: the associated FactPair objects
        --- source_conclusion   :: text for the source conclusion
        --- target_conclusion   :: text for the target conclusion
"""


class ScenarioPair(models.Model):

    name = models.CharField(max_length=64, unique=True)
    facts = models.ManyToManyField('wga.FactPair')
    source_conclusion = models.CharField(max_length=1024)
    target_conclusion = models.CharField(max_length=1024)

    def __str__(self):
        return self.name


########################################################################################################################


"""
    Move MODEL

    Django model representing moves in the WG-A game (not to be used in the control case since all moves will be made
    via a Minnit chat room).

    FIELDS
        --- user                :: the mTurk worker who made the move
        --- game                :: the associated Game object
        --- date                :: date and time in which the move was made (in UTC timezone)
        --- code                :: label for the move (what kind of move was made?)
        --- text                :: text description of the move
"""


class Move(models.Model):

    class Code:
        CREATE_RULE = "Create Rule"
        UPDATE_RULE = "Update Rule"

        SENT_ATTACK = "Sent Attack"
        ACCEPTED_ATTACK = "Accepted Attack"
        REJECTED_ATTACK = "Rejected Attack"

        PROPOSED_EDIT = "Proposed Edit"
        ACCEPTED_EDIT = "Accepted Edit"
        REJECTED_EDIT = "Rejected Edit"
        MODIFIED_EDIT = "Modified Edit"

        PROPOSED_ADD = "Proposed Add"
        ACCEPTED_ADD = "Accepted Add"
        REJECTED_ADD = "Rejected Add"
        MODIFIED_ADD = "Modified Add"

        REPORT = "Report"
        REPORT_REVIEWED = "Report Reviewed"

        PASS = "Pass"
        COMPLETED = "Completed"

    user = models.ForeignKey('wga.User', null=True, on_delete=models.SET_NULL)
    game = models.ForeignKey('wga.Game', null=True, on_delete=models.SET_NULL)
    date = models.DateTimeField(default=timezone.now)
    code = models.CharField(max_length=64)
    text = models.CharField(max_length=1024)

    def __str__(self):
        return f"Advocate {self.text}" if self.game.adv_info.user == self.user else f"Critic {self.text}"


########################################################################################################################


"""
    Message MODEL

    Django model representing messages from administrators to mTurk workers (one-way communication; not to be used in
    the control case since administrators can communicate with mTurk workers via the Minnit chat room). This model will
    be used to display individualized messages (to mTurk workers in a particular game) or to display session-wide
    announcements (to all mTurk workers in a game session).

    FIELDS
        --- text                :: text description of the message
        --- date                :: date and time in which the message / announcement was made
"""


class Message(models.Model):

    date = models.DateTimeField(default=timezone.now)
    text = models.CharField(max_length=1024)

    def __str__(self):
        return self.text


########################################################################################################################


"""
    Group MODEL
    
    Django model representing game sessions. We use the Group object to identify mTurk workers as either control or
    non-control study participants.
    
    FIELDS
        --- name                :: text description of the game session
        --- case                :: text identifier distinguishing between control and non-control cases
        --- date                :: date and time in which the game session was made (in UTC timezone)
        --- num_users           :: total number of users in the game session
        --- num_games           :: total number of games in the game session
        --- scenarios           :: the associated ScenarioPair objects
        
        DJANGO CHANNELS
        --- messages            :: (non-control) the associated Message objects

    METHODS
        --- generate_games      :: once all fields are filled, generate User, Intermediary, and Game objects
        --- add_game            :: when mTurk workers finish all their games, the administrators can create new games
        --- add_announcement    :: (non-control) adds a session-wide announcement
"""


class Group(models.Model):

    class Case:
        CONTROL = 'Control'
        NON_CONTROL = 'Non-control'

    CHAT_ROOMS = [
        'XFyk6', 'S2u68', 'u3N0F', '2dbTj', 'Xv2vN',
        '8K0Mm', 'rX87A', 'gzHCP', 'Z7b41', '4gTEM',
        'l9U37', 'eKM2e', '7Y0UQ', 'omZkr', 'kyfS2',
        'CgLc2', 'ciUek', 'Z20JB', 'QWPLe', 's0OPS',
        'm5Ur4', 'mRgnP', 'EYegn', 'GEvu5', 'ETUs1',
        'nWkA0', 'HxASu', 'XUmdq', 'pOrKP', 'a9IS4',
        'gpni7', 'WMJ3K', 'AFP1M', 'NqBgf', '0KQ28',
        'Kefgn', 'zxjZ4', 'uYx5q', '67XtR', 'vkfIx',
        'oKb8f', '4xpmv', 'Gc7pP', 'qMVhc', 'ppPKF',
        'Fp6eR', 's0aWN', '5GZ1h', 'eLQ5Z'
    ]

    CASE_CHOICES = [
        (Case.CONTROL, "Control"),
        (Case.NON_CONTROL, "Non-control")
    ]

    name = models.CharField(max_length=64, unique=True)
    case = models.CharField(max_length=64, choices=CASE_CHOICES)
    date = models.DateTimeField(default=timezone.now)
    start = models.DateTimeField()
    num_users = models.IntegerField()
    num_games = models.IntegerField()
    scenarios = models.ManyToManyField('wga.ScenarioPair')

    # Django Channels (WebSockets)
    messages = models.ManyToManyField('wga.Message')

    def generate_games(self):
        if self.case == self.Case.NON_CONTROL:
            self._non_control()
        elif self.case == self.Case.CONTROL:
            self._control()

    def _non_control(self):
        self.save()

        # Step 0: Load CSV file from mTurk (containing mTurk workers' code names)
        with open(f"wga/game_sessions/{self.name}.csv", 'r') as file:
            reader = csv.reader(file)
            code_names = list(reader)
        WGA_ADMIN_LOGGER.debug(f"Step 0 Completed: Loaded code names from {self.name}.csv")

        # Step 1: Generate *num_users* number of User objects
        players = [User.objects.create(name=code_names[i][0], group=self) for i in range(self.num_users)]
        WGA_ADMIN_LOGGER.debug("Step 1 Completed: Generated User objects")

        # Step 2: Generate a random set of game pairs
        adv, crt = [], []
        alternate = True
        for i in range(self.num_users):
            for _ in range(self.num_games):
                adv.append(i) if alternate else crt.append(i)
                alternate = not alternate
        while True:
            random.seed(datetime.datetime.now().second)
            random.shuffle(adv)
            random.shuffle(crt)
            for i in range(len(adv)):
                if adv[i] == crt[i]:
                    break
            else:
                break
        WGA_ADMIN_LOGGER.debug(f"Step 2 Completed: Generated game pairs - {list(zip(adv, crt))}")

        # Step 3: Generate games based on game pairs from Step 2
        for (i, j) in zip(adv, crt):
            # Step 3a: Find a scenario that Players i and j have not played before
            scenarios = list(self.scenarios.all())
            scenario = random.choice(scenarios)
            while Game.objects.filter(Q(group=self) & Q(scenario=scenario) & (
                Q(adv_info__user=players[i]) | Q(crt_info__user=players[i]) |
                Q(adv_info__user=players[j]) | Q(crt_info__user=players[j]))
            ).exists():
                scenarios.remove(scenario)
                scenario = random.choice(scenarios)
            # Step 3b: Create a game based on the scenario chosen for Players i and j in Step 1
            game = Game.objects.create(
                group=self,
                scenario=scenario,
                adv_info=Intermediary.objects.create(user=players[i], role=Intermediary.Role.ADVOCATE),
                crt_info=Intermediary.objects.create(user=players[j], role=Intermediary.Role.CRITIC)
            )
            game.set_initial_facts()
            WGA_ADMIN_LOGGER.debug(f"Generated: {game}")
        WGA_ADMIN_LOGGER.debug(f"Step 3 Completed: Generated games")

        # Step 4: Update the group's number of games
        self.num_games = int(self.num_users * self.num_games / 2)
        self.save()
        WGA_ADMIN_LOGGER.debug(f"Step 4 Completed: Finished generating {self.num_games} games")

        # Step 5: Return a CSV file
        with open(f"wga/game_sessions/{self.name}.csv", 'w+') as file:
            for user in self.user_set.all():
                file.write(f"{user.name},{user.key}\n")
        WGA_ADMIN_LOGGER.debug("Step 5 Completed: Generated CSV file")

    def add_game(self, scenario, advocate, critic):
        self.save()
        game = Game.objects.create(
            group=self,
            scenario=scenario,
            adv_info=Intermediary.objects.create(user=advocate, role=Intermediary.Role.ADVOCATE),
            crt_info=Intermediary.objects.create(user=critic, role=Intermediary.Role.CRITIC)
        )
        game.set_initial_facts()
        self.num_games += 1
        self.save()
        WGA_ADMIN_LOGGER.debug(f"Added {game} to {self.name}")
        return game

    def _control(self):
        self.save()

        # Step 0: Load CSV file from mTurk (containing mTurk workers' code names)
        with open(f"wga/game_sessions/{self.name}.csv", 'r') as file:
            reader = csv.reader(file)
            code_names = list(reader)
        WGA_ADMIN_LOGGER.debug(f"Step 0 Completed: Loaded code names from {self.name}.csv")

        # Step 1: Generate *num_users* number of User objects
        players = [User.objects.create(name=code_names[i][0], group=self) for i in range(self.num_users)]
        WGA_ADMIN_LOGGER.debug("Step 1 Completed: Generated User objects")

        # Step 2: Generate a random set of game pairs
        adv, crt = [], []
        alternate = True
        for i in range(self.num_users):
            for _ in range(self.num_games):
                adv.append(i) if alternate else crt.append(i)
                alternate = not alternate
        while True:
            random.seed(datetime.datetime.now().second)
            random.shuffle(adv)
            random.shuffle(crt)
            for i in range(len(adv)):
                if adv[i] == crt[i]:
                    break
            else:
                break
        WGA_ADMIN_LOGGER.debug(f"Step 2 Completed: Generated game pairs - {list(zip(adv, crt))}")

        # Step 3: Generate games based on game pairs from Step 2
        chats = self.CHAT_ROOMS.copy()
        # Step 3a: Set each game's scenario
        scenarios = list(self.scenarios.all())
        random.shuffle(scenarios)
        scenario = scenarios.pop(0)
        for (i, j) in zip(adv, crt):
            """
            # Step 3a: Find a scenario that Players i and j have not played before
            scenarios = list(self.scenarios.all())
            scenario = random.choice(scenarios)
            while Game.objects.filter(Q(group=self) & Q(scenario=scenario) & (
                Q(adv_info__user=players[i]) | Q(crt_info__user=players[i]) |
                Q(adv_info__user=players[j]) | Q(crt_info__user=players[j]))
            ).exists():
                scenarios.remove(scenario)
                scenario = random.choice(scenarios)
            """
            # Step 3b: Create a game based on the scenario chosen for Players i and j in Step 1
            game = Game.objects.create(
                group=self,
                scenario=scenario,
                chat=chats.pop(0),
                adv_info=Intermediary.objects.create(user=players[i], role=Intermediary.Role.INTERLOCUTOR),
                crt_info=Intermediary.objects.create(user=players[j], role=Intermediary.Role.INTERLOCUTOR),
                rule_antecedent='n/a',
                rule_consequent='n/a',
                context=Game.Context.CONVERSATION,
                context_data='n/a',
                turn=Game.Turn.CONVERSATION
            )
            game.set_initial_facts()
            WGA_ADMIN_LOGGER.debug(f"Generated: {game}")
        WGA_ADMIN_LOGGER.debug(f"Step 3 Completed: Generated games")

        # Step 4: Update the group's number of games
        self.num_games = int(self.num_users * self.num_games / 2)
        self.save()
        WGA_ADMIN_LOGGER.debug(f"Step 4 Completed: Finished generating {self.num_games} games")

        # Step 5: Return a CSV file
        with open(f"wga/game_sessions/{self.name}.csv", 'w+') as file:
            for user in self.user_set.all():
                file.write(f"{user.name},{user.key}\n")
        WGA_ADMIN_LOGGER.debug("Step 5 Completed: Generated CSV file")

    def shuffle(self):
        # Step 0: Mark all current games as finished
        for game in self.game_set.all():
            game.context = Game.Context.COMPLETED
            game.turn = Game.Turn.COMPLETED
            game.adv_info = None
            game.crt_info = None
            # game.scenario = None
            game.save()
        WGA_ADMIN_LOGGER.debug("Step 0 Completed: Marked all current games as finished")

        # Step 1: Collect all Intermediary objects into a single list
        intermediaries = list(Intermediary.objects.filter(user__group=self, user__assigned=False))
        intermediaries.extend(list(Intermediary.objects.filter(user__group=self, user__assigned=True).order_by('?')))
        WGA_ADMIN_LOGGER.debug(f"Step 1 Completed: Collected all Intermediary objects for { self.name }")

        # Step 2: Generate new game pairs
        adv, crt = [], []
        alternate = True
        for i in range(self.num_users):
            for _ in range(int(self.num_games * 2 / self.num_users)):
                adv.append(i) if alternate else crt.append(i)
                alternate = not alternate
        """
        # unnecessary since we are assuming the control group will only ever have one game each participant
        while True:
            random.seed(datetime.datetime.now().second)
            random.shuffle(adv)
            random.shuffle(crt)
            for i in range(len(adv)):
                if adv[i] == crt[i]:
                    break
            else:
                break
        """
        WGA_ADMIN_LOGGER.debug(f"Step 2 Completed: Generated game pairs - {list(zip(adv, crt))}")

        # Step 3: Generate new games
        chats = self.CHAT_ROOMS.copy()
        scenario = random.choice([s for s in self.scenarios.all() if not self.game_set.filter(scenario=s).exists()])
        for (i, j, game) in zip(adv, crt, list(Game.objects.filter(group=self))):
            game = Game.objects.create(
                group=self,
                scenario=scenario,
                chat=chats.pop(0),
                adv_info=intermediaries[i],
                crt_info=intermediaries[j],
                rule_antecedent='n/a',
                rule_consequent='n/a',
                context=Game.Context.CONVERSATION,
                context_data='n/a',
                turn=Game.Turn.CONVERSATION
            )
            game.set_initial_facts()
            WGA_ADMIN_LOGGER.debug(f"Generated: {game}")
        WGA_ADMIN_LOGGER.debug(f"Step 3 Completed: Generated games")

    def __str__(self):
        return self.name


########################################################################################################################


"""
    Intermediary MODEL

    Django model representing a game slot. This model records data that is pertinent to both the mTurk worker as well as
    their particular game.

    FIELDS
        --- user                :: the mTurk worker playing in this game slot
        --- key                 :: 20 character string uniquely identifying the Intermediary object
        --- role                :: (non-control) the mTurk worker's role
        --- time                :: (non-control) amount of time (in seconds) the mTurk worker spends in the game
        
        DJANGO CHANNELS
        --- messages            :: (non-control) the associated Message objects

    METHODS
        --- add_message         :: (non-control) adds an individualized message
"""


class Intermediary(models.Model):

    class Role:
        ADVOCATE = "Advocate"
        CRITIC = "Critic"
        INTERLOCUTOR = "Interlocutor"

    ROLE_CHOICES = [
        (Role.ADVOCATE, "Advocate"),
        (Role.CRITIC, "Critic"),
        (Role.INTERLOCUTOR, "Interlocutor")
    ]

    user = models.ForeignKey('wga.User', null=True, on_delete=models.SET_NULL)
    key = models.CharField(unique=True, max_length=20, default=create_key)
    role = models.CharField(max_length=64, choices=ROLE_CHOICES)
    time = models.FloatField(default=0.0)

    # Django Channels (WebSockets)
    messages = models.ManyToManyField('wga.Message')

    def __str__(self):
        return self.user.name


########################################################################################################################


"""
    Game MODEL
    
    Django model representing a game for both control and WG-A cases (though the control case will not be using all
    the model fields described here). This is one of the most important models for the WG-A case as it determines which
    forms and templates to use.
    
    FIELDS
        --- group               :: the associated Group object
        --- scenario            :: the associated ScenarioPair object
        --- chat                :: (control) necessary string value for the embedded Minnit chat room
        --- adv_info            :: the associated Intermediary object for the advocate player
        --- crt_info            :: the associated Intermediary object for the critic player
        --- rule_antecedent     :: (non-control) the WG-A game's rule antecedent
        --- rule_consequent     :: (non-control) the WG-A game's rule consequent
        --- context             :: (non-control) the WG-A game's current state
        --- context_data        :: (non-control) relevant data from the WG-A game's previous state
        --- turn                :: (non-control) determines the current player
        
    METHODS
        --- set_initial_facts   :: copies the facts from the ScenarioPair object and adds them to the Game object
        --- set_context_data    :: set relevant data to be used in the next game state
        --- get_context_data    :: set relevant data from the previous game state
        --- add_move            :: basic adder function
        --- can_pass            :: if 8 total moves have been made, the Critic is allowed to pass their turn
"""


class Game(models.Model):

    class Context:
        NOT_TURN = "Not Turn"
        CREATE_RULE = "Create Rule"
        IDLE = "Idle"
        ATTACK_RESPONSE = "Attack Response"
        PROPOSED_EDIT = "Proposed Edit"
        PROPOSED_ADD = "Proposed Add"
        SUSPENDED = "Suspended"
        COMPLETED = "Completed"
        CONVERSATION = "Conversation"

    class Turn:
        CRITIC = 0
        ADVOCATE = 1
        MODERATED = 2
        COMPLETED = 3
        CONVERSATION = 4

    TURN_CHOICES = [
        (Turn.CRITIC, "Critic"),
        (Turn.ADVOCATE, "Advocate"),
        (Turn.MODERATED, "Moderated"),
        (Turn.COMPLETED, "Completed"),
        (Turn.CONVERSATION, "Conversation")
    ]

    group = models.ForeignKey('wga.Group', null=True, on_delete=models.SET_NULL)
    scenario = models.ForeignKey('wga.ScenarioPair', null=True, on_delete=models.SET_NULL)
    chat = models.CharField(blank=True, null=True, max_length=20)
    adv_info = models.OneToOneField('wga.Intermediary', null=True, on_delete=models.SET_NULL, related_name='advocacy')
    crt_info = models.OneToOneField('wga.Intermediary', null=True, on_delete=models.SET_NULL, related_name='criticism')
    rule_antecedent = models.CharField(default="__________", max_length=1024)
    rule_consequent = models.CharField(default="__________", max_length=1024)
    context = models.CharField(default=Context.CREATE_RULE, max_length=64)
    context_data = models.CharField(blank=True, max_length=1024)  # DO NOT ACCESS DIRECTLY
    turn = models.IntegerField(default=Turn.ADVOCATE, choices=TURN_CHOICES)

    def set_initial_facts(self):
        self.save()
        for fact in self.scenario.facts.all():
            FactPair.objects.create(game=self, source_fact=fact.source_fact, target_fact=fact.target_fact)
        self.save()

    def set_context_data(self, data):
        self.save()
        self.context_data = '%_#_%'.join([str(s) for s in data])
        self.save()

    def get_context_data(self):
        return str(self.context_data).split('%_#_%')

    def add_move(self, user, code, text):
        self.save()
        Move.objects.create(user=user, game=self, code=code, text=text)
        self.save()

    def can_pass(self):
        return self.move_set.all().count() > 8

    def __str__(self):
        return f"Game between {self.adv_info.user.name} and {self.crt_info.user.name} on \"{self.scenario.name}\""


########################################################################################################################


"""
    Report MODEL

    Django model representing a moderator report. mTurk workers are allowed to submit a report to the administrators
    only if (1) their opponent is acting contrary to the spirit of the game, (2) the mTurk worker needs to prematurely
    dropout of the study, and (3) the mTurk worker is experiencing technical issues with the website (not to be
    used in the control case since mTurk workers can communicate with administrators via the Minnit chat room).

    FIELDS
        --- user                :: the mTurk worker who made the report
        --- game                :: the associated Game object
        --- date                :: date and time in which the report was made (in UTC timezone)
        --- text                :: the mTurk worker's text description of the report
        --- note                :: the administrator's text description of their comments
        --- returned            :: the player who resumes the game
        --- resolved            :: is the report resolved (T/F)?

    METHODS
        --- report_error        :: method to send reports when the program runs into errors
        --- report_user         :: method to send reports when mTurk workers submit reports
"""


class Report(models.Model):

    RETURN_CHOICES = [
        (Game.Turn.CRITIC, "Critic"),
        (Game.Turn.ADVOCATE, "Advocate"),
        (Game.Turn.COMPLETED, "End Game")
    ]

    user = models.ForeignKey('wga.User', null=True, on_delete=models.SET_NULL)
    game = models.ForeignKey('wga.Game', null=True, on_delete=models.SET_NULL)
    date = models.DateTimeField(default=timezone.now)
    text = models.CharField(max_length=1024)
    note = models.CharField(null=True, max_length=1024)
    returned = models.IntegerField(null=True, choices=RETURN_CHOICES)
    resolved = models.BooleanField(default=False)

    @staticmethod
    def report_error(game, text):
        game.save()
        game.turn = Game.Turn.MODERATED
        game.save()
        Report.objects.create(game=game, text="Error Reported: " + text)

    @staticmethod
    def report_user(game, text):
        game.save()
        game.turn = Game.Turn.MODERATED
        game.save()
        Report.objects.create(game=game, text="User Reported: " + text)

    def __str__(self):
        return f"{self.user} {self.text}"


########################################################################################################################
