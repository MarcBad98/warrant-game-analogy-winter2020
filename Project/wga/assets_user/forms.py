"""
    WG-A User Django Forms

    This file contains all the forms for the WG-A User web pages. Django forms render the necessary HTML elements to
    render HTML forms; rather than having the front-end developer manually write the HTML for forms, Django offers form
    objects that makes HTML forms more maintainable.

    DOCUMENTATION
    https://docs.djangoproject.com/en/2.2/topics/forms/
"""

import logging
import datetime

from django import forms
from django.shortcuts import get_object_or_404
from django.utils import timezone

from wga import models


WGA_GAME_LOGGER = logging.getLogger('django.games')


########################################################################################################################


"""
    Login FORM
    
    Django form for mTurk workers to login using their own user names and the key they were sent via mTurk bonus
    payment messages. This is the first form the mTurk worker will see, which validates their identity (as in: they are
    mTurk workers scheduled for the game session; identity is IMPORTANT as it helps us keep track of their progress,
    which determines their pay).

    VALIDATIONS
        --- name                :: ensure the given name is associated with an existing User object
        --- key                 :: ensure the given name is associated with the same User object
"""


class LoginForm(forms.Form):

    name = forms.CharField(label="User Name")
    key = forms.CharField(label="Key")

    def clean(self):
        super().clean()
        data = self.cleaned_data

        if not models.User.objects.filter(name=data['name'], key=data['key']).exists():
            WGA_GAME_LOGGER.debug(f"Invalid form: Missing or mismatched credentials. {data}")
            self.add_error('name', forms.ValidationError("Login failed. Credentials do not match."))

        elif models.User.objects.get(name=data['name']).assigned:
            WGA_GAME_LOGGER.debug(f"Invalid form: Re-entered credentials. {data}")
            self.add_error('name', forms.ValidationError("Login failed. Credentials already used."))

        elif timezone.now() < models.User.objects.get(name=data['name']).group.start:
            WGA_GAME_LOGGER.debug(f"Invalid form: Logged in before start time. {data}")
            self.add_error('name', forms.ValidationError("Login failed. Please wait until your assigned time."))

        elif timezone.now() > models.User.objects.get(name=data['name']).group.start + datetime.timedelta(hours=2):
            WGA_GAME_LOGGER.debug(f"Invalid form: Logged in after session expiration. {data}")
            self.add_error('name', forms.ValidationError("Login failed. Session was already completed."))

        return self.cleaned_data


"""
    Instructions FORM
    
    Django form for displaying initial instructions for mTurk workers. This is used in the Instructions VIEW in order to
    ensure that the mTurk worker has watched the 15-minute instructional video for the non-control case or read their
    text instructions for the control case. The instructional video will have a password embedded sometime in the video;
    this password will need to be entered into this form in order for the mTurk worker to continue with the study. For
    the text instructions, mTurk workers need only click a button to proceed.

    VALIDATIONS
        --- pwd                 :: ensure the given password is the same as the one in the video
"""


class InstructionsForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        if self.user.group.case == models.Group.Case.NON_CONTROL:
            self.fields['pwd'] = forms.CharField(label="Password")

    def clean(self):
        super().clean()
        data = self.cleaned_data

        if self.user.group.case == models.Group.Case.NON_CONTROL and data['pwd'] != "chicken-hawk":
            self.add_error('pwd', forms.ValidationError("Login failed. Password incorrect."))
            WGA_GAME_LOGGER.debug(f"Invalid form: Password is incorrect. {data}")

        return self.cleaned_data


########################################################################################################################


"""
    build_form HELPER FUNCTION
    
    Returns the form depending on the game's context. Rather than working with the below form classes individually, use
    build_form to get the required form.
"""


def build_form(post_data=None, user=None, game=None, is_critic=None):

    func_kwargs = {
        'user': user,
        'game': game,
        'is_critic': is_critic
    }

    if game.context == models.Game.Context.NOT_TURN:
        form = None

    elif game.context == models.Game.Context.CREATE_RULE:
        form = CreateRuleForm(**func_kwargs) if not post_data else CreateRuleForm(post_data, **func_kwargs)

    elif game.context == models.Game.Context.IDLE and is_critic:
        form = CriticIdleForm(**func_kwargs) if not post_data else CriticIdleForm(post_data, **func_kwargs)

    elif game.context == models.Game.Context.IDLE and not is_critic:
        form = AdvocateIdleForm(**func_kwargs) if not post_data else AdvocateIdleForm(post_data, **func_kwargs)

    elif game.context == models.Game.Context.ATTACK_RESPONSE:
        form = AttackResponseForm(**func_kwargs) if not post_data else AttackResponseForm(post_data, **func_kwargs)

    elif game.context == models.Game.Context.PROPOSED_EDIT:
        form = ProposedEditForm(**func_kwargs) if not post_data else ProposedEditForm(post_data, **func_kwargs)

    elif game.context == models.Game.Context.PROPOSED_ADD:
        form = ProposedAddForm(**func_kwargs) if not post_data else ProposedAddForm(post_data, **func_kwargs)

    else:
        WGA_GAME_LOGGER.error(f"An unrecognized context was passed to build_form: {game.context} with data {post_data}")
        models.Report.report_error(game=game, text=f"build_form(): invalid context - {game.context}")
        form = None

    return form


########################################################################################################################


"""
    (ABSTRACT) Move FORM
    
    This is an abstract class that every move form for WG-A must inherit. This class processes the passed keyword
    arguments that are useful in rendering and processing move forms:
    
    DATA MEMBERS
        --- user                :: the mTurk worker who will view and make the move
        --- game                :: the game in which the move will be made
        --- is_critic           :: is the mTurk worker playing as the critic (T/F)?
"""


class MoveForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.game = kwargs.pop('game')
        self.is_critic = kwargs.pop('is_critic')
        super().__init__(*args, **kwargs)

    # (OVERRIDE) Each MoveForm subclass must provide functionality for processing the form (changing game state).
    def process(self):
        pass


# -------------------------------------------------------------------------------------------------------------------- #


"""
    (A) Create Rule FORM
    
    The first stage of the game is the Advocate creating a rule for the given argument structure. Their rule must be
    in "IF x, THEN y" form with x being the antecedent and y being the consequent. The Advocate is given this form
    only once; any future edits to the rule must be done via the Update Rule FORM. After submitting this form, the
    process() method must be invoked to update the game state as well as switch game control accordingly ---> Critic
    (Idle).
     
    VALIDATIONS
        --- antecedent          :: after removing whitespace and "if" (if included), make sure the result is non-empty
        --- consequent          :: after removing whitespace and "then" (if included), make sure the result is non-empty
"""


class CreateRuleForm(MoveForm):

    antecedent = forms.CharField(max_length=1024)
    consequent = forms.CharField(max_length=1024)

    def clean_antecedent(self):
        a = self.cleaned_data['antecedent'].strip()
        if a[:2].lower() == "if":
            a = a[2:].strip()
            if not a:
                WGA_GAME_LOGGER.debug(f"Invalid form: No antecedent after excluding \"if\". {self.cleaned_data}")
                raise forms.ValidationError("Exclude \"if\" in your responses.")
        return a

    def clean_consequent(self):
        c = self.cleaned_data['consequent'].strip()
        if c[:4].lower() == "then":
            c = c[4:].strip()
            if not c:
                WGA_GAME_LOGGER.debug(f"Invalid form: No consequent after excluding \"then\". {self.cleaned_data}")
                raise forms.ValidationError("Exclude \"then\" in your responses.")
        return c

    def process(self):
        if self.is_valid():
            form = self.cleaned_data

            self.game.rule_antecedent = form['antecedent']
            self.game.rule_consequent = form['consequent']
            self.game.context = models.Game.Context.IDLE
            self.game.turn = models.Game.Turn.CRITIC

            text = f"Created the rule: IF {form['antecedent']}, THEN {form['consequent']}"
            self.game.add_move(user=self.user, code=models.Move.Code.CREATE_RULE, text=text)
            WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.CREATE_RULE}: \"{text}\"")


# -------------------------------------------------------------------------------------------------------------------- #


"""
    (A) Update Rule FORM
    
    The first stage of the game was the Advocate creating a rule for the given argument structure. In the Create Rule
    FORM, they initialized the argument structure's rule. If the Advocate decides to change the rule (for example,
    because there is a weakness or to protect against future attacks), then they can do so by providing the antecedent
    and consequent in this form. After submitting this form, the process() method must be invoked to update the game
    state as well as switch game control accordingly ---> Critic (Idle).
    
    VALIDATIONS
        --- antecedent          :: after removing whitespace and "if" (if included), make sure the result is non-empty
        --- antecedent          :: make sure the antecedent & consequent do not match the current rule
        --- consequent          :: after removing whitespace and "then" (if included), make sure the result is non-empty
        --- consequent          :: make sure the antecedent & consequent do not match the current rule
"""


class UpdateRuleForm(CreateRuleForm):

    antecedent = forms.CharField(required=False, max_length=1024)
    consequent = forms.CharField(required=False, max_length=1024)

    def clean(self):
        super().clean()
        data = self.cleaned_data

        if self.game.rule_antecedent == data['antecedent'] and self.game.rule_consequent == data['consequent']:
            self.add_error('antecedent', "Rule already exists.")
            WGA_GAME_LOGGER.debug(f"Invalid form: Rule already exists. {data}")

        return self.cleaned_data

    def process(self):
        if self.is_valid():
            form = self.cleaned_data

            self.game.rule_antecedent = form['antecedent']
            self.game.rule_consequent = form['consequent']
            self.game.context = models.Game.Context.IDLE
            self.game.turn = models.Game.Turn.CRITIC

            text = f"Updated the current rule to: IF {form['antecedent']}, THEN {form['consequent']}"
            self.game.add_move(user=self.user, code=models.Move.Code.UPDATE_RULE, text=text)
            WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.UPDATE_RULE}: \"{text}\"")


# -------------------------------------------------------------------------------------------------------------------- #


"""
    (C) Attack FORM
    
    If the Critic wants to point out a weakness in the current argument structure, the Critic can do so by providing
    which link to attack and the explanation of the weakness. Depending on the link chosen, different instructions are
    presented to the Critic. The Critic must be careful that the weakness explanation only takes into consideration
    ONLY the elements presented in the instructions. After submitting this form, the process() method must be invoked to
    update the game state as well as switch game control accordingly ---> Advocate (Attack Response).
"""


class AttackForm(MoveForm):

    link = forms.ChoiceField(required=False, widget=forms.RadioSelect, choices=[
        ('L1', "L.1"),
        ('L2', "L.2"),
        ('L3', "L.3"),
        ('L4', "L.4"),
        ('L5', "L.5")
    ])
    explain_attack = forms.CharField(required=False, label="Why are you attacking this link?", max_length=1024)

    def process(self):
        if self.is_valid():
            form = self.cleaned_data

            self.game.context = models.Game.Context.ATTACK_RESPONSE
            self.game.turn = models.Game.Turn.ADVOCATE
            self.game.set_context_data([
                form['link'],                                                             # chosen link to attack
                form['explain_attack']                                                    # explanation of attack
            ])

            text = f"Attacked link {form['link']} with explanation: {form['explain_attack']}"
            self.game.add_move(user=self.user, code=models.Move.Code.SENT_ATTACK, text=text)
            WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.SENT_ATTACK}: \"{text}\"")


"""
    (A) Attack Response FORM
    
    After the Critic submits an attack form, the Advocate must then respond to the attack (accept / reject). The
    Advocate is allowed to read through the Critic's instructions before making a decision. After submitting this form,
    the process() method must be invoked to update the game state as well as switch game control accordingly:
    
        --- accept  ::  ---> Advocate (Idle)
        --- reject  ::  ---> Critic (Idle)
"""


class AttackResponseForm(MoveForm):

    ACCEPT = 'accept'
    REJECT = 'reject'

    response = forms.ChoiceField(widget=forms.RadioSelect, choices=[
        (ACCEPT, "Accept"),
        (REJECT, "Reject")
    ])
    explanation = forms.CharField(required=False, label="Why is the attack invalid?", max_length=1024)

    def process(self):
        if self.is_valid():
            form = self.cleaned_data
            if form['response'] == self.ACCEPT:
                self._process_accept()
            elif form['response'] == self.REJECT:
                self._process_reject()

    def _process_accept(self):
        form = self.cleaned_data

        self.game.context = models.Game.Context.IDLE
        self.game.turn = models.Game.Turn.ADVOCATE
        self.game.set_context_data([])

        text = "Accepted attack as valid"
        self.game.add_move(user=self.user, code=models.Move.Code.ACCEPTED_ATTACK, text=text)
        WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.ACCEPTED_ATTACK}: \"{text}\"")

    def _process_reject(self):
        form = self.cleaned_data

        self.game.context = models.Game.Context.IDLE
        self.game.turn = models.Game.Turn.CRITIC
        self.game.set_context_data([])

        text = f"Rejected the attack: {form['explanation']}"
        self.game.add_move(user=self.user, code=models.Move.Code.REJECTED_ATTACK, text=text)
        WGA_GAME_LOGGER.info(f"[{self.user.key}] Successfully processed {models.Move.Code.REJECTED_ATTACK}: \"{text}\"")


# -------------------------------------------------------------------------------------------------------------------- #


"""
    (B) Update Facts FORM

    If the Player wants to update a fact pair in the current argument structure, the Player can do so by providing which
    fact pair to update and the corresponding source and target facts to update. The Player should update facts when
    they feel the fact pair is untrue or inaccurate. After submitting this form, the process() method must be invoked to
    update the game state as well as switch game control accordingly ---> Opponent (Proposed Edit).
"""


class UpdateFactsForm(MoveForm):

    source_replace = forms.CharField(required=False, max_length=1024)
    target_replace = forms.CharField(required=False, max_length=1024)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['edit'] = forms.ChoiceField(required=False, label="Which facts will you modify?", choices=[
            (fp.id, str(fp)) for fp in self.game.factpair_set.all()
        ])

    def clean(self):
        super().clean()
        data = self.cleaned_data

        source, target = data['source_replace'], data['target_replace']
        if models.FactPair.objects.filter(game=self.game, source_fact=source, target_fact=target).exists():
            self.add_error('source_replace', forms.ValidationError("Facts already exist"))
            WGA_GAME_LOGGER.debug(f"Invalid form: Facts already exist. {data}")

        return self.cleaned_data

    def process(self):
        if self.is_valid():
            form = self.cleaned_data
            old = get_object_or_404(models.FactPair, id=form['edit'])
            new = models.FactPair(source_fact=form['source_replace'], target_fact=form['target_replace'])

            self.game.context = models.Game.Context.PROPOSED_EDIT
            self.game.turn = models.Game.Turn.ADVOCATE if self.is_critic else models.Game.Turn.CRITIC
            self.game.set_context_data([
                old.source_fact, old.target_fact,                                         # FactPair to be updated
                new.source_fact, new.target_fact,                                         # FactPair used to replace
                int(form['edit']),                                                        # id of FactPair to be updated
                ""                                                                        # explanation of rejection
            ])

            text = f"Proposed modifying facts: [Original] {old} >> [Proposed] {new}"
            self.game.add_move(user=self.user, code=models.Move.Code.PROPOSED_EDIT, text=text)
            WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.PROPOSED_EDIT}: \"{text}\"")


"""
    (B) Proposed Edit FORM

    After the Opponent submits an update facts form, the Player must then respond to the proposal (accept / reject /
    modify). The Player has the option of modifying the proposal, which essentially creates a new proposal (based on the
    old proposal). After submitting this form, the process() method must be invoked to update the game state as well as
    switch game control accordingly:
    
        --- accept  ::  ---> Player (Idle)
        --- reject  ::  ---> Opponent (Idle)
        --- modify  ::  ---> Opponent (Proposed Edit)
"""


class ProposedEditForm(MoveForm):

    ACCEPT = 'accept'
    REJECT = 'reject'
    MODIFY = 'modify'

    response = forms.ChoiceField(widget=forms.RadioSelect, choices=[
        (ACCEPT, "Accept"),
        (REJECT, "Reject"),
        (MODIFY, "Offer alternative")
    ])
    explain_reject = forms.CharField(required=False, label="Why are you rejecting the proposal?", max_length=1024)
    source_replace = forms.CharField(required=False, max_length=1024)
    target_replace = forms.CharField(required=False, max_length=1024)

    def clean(self):
        super().clean()
        data = self.cleaned_data

        source, target = data['source_replace'], data['target_replace']
        if models.FactPair.objects.filter(game=self.game, source_fact=source, target_fact=target).exists():
            self.add_error('source_replace', forms.ValidationError("Facts already exist"))
            WGA_GAME_LOGGER.debug(f"Invalid form: Facts already exist. {data}")

        return self.cleaned_data

    def process(self):
        if self.is_valid():
            form = self.cleaned_data
            if form['response'] == self.ACCEPT:
                self._process_accept()
            elif form['response'] == self.REJECT:
                self._process_reject()
            elif form['response'] == self.MODIFY:
                self._process_modify()

    def _process_accept(self):
        form = self.cleaned_data

        data = self.game.get_context_data()
        models.FactPair.objects.filter(id=data[4]).update(source_fact=data[2], target_fact=data[3])
        self.game.context = models.Game.Context.IDLE
        self.game.turn = models.Game.Turn.CRITIC if self.is_critic else models.Game.Turn.ADVOCATE
        self.game.set_context_data([])

        text = "Accepted the proposed edit"
        self.game.add_move(user=self.user, code=models.Move.Code.ACCEPTED_EDIT, text=text)
        WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.ACCEPTED_EDIT}: \"{text}\"")

    def _process_reject(self):
        form = self.cleaned_data

        self.game.context = models.Game.Context.IDLE
        self.game.turn = models.Game.Turn.ADVOCATE if self.is_critic else models.Game.Turn.CRITIC
        self.game.set_context_data([])

        text = f"Rejected proposed edit: {form['explain_reject']}"
        self.game.add_move(user=self.user, code=models.Move.Code.REJECTED_EDIT, text=text)
        WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.REJECTED_EDIT}: \"{text}\"")

    def _process_modify(self):
        form = self.cleaned_data
        data = self.game.get_context_data()

        self.game.context = models.Game.Context.PROPOSED_EDIT
        self.game.turn = models.Game.Turn.ADVOCATE if self.is_critic else models.Game.Turn.CRITIC
        alt = models.FactPair(source_fact=form['source_replace'], target_fact=form['target_replace'])
        self.game.set_context_data([
            data[0], data[1],                                                             # FactPair to be updated
            alt.source_fact, alt.target_fact,                                             # FactPair used to replace
            data[4],                                                                      # id of FactPair to be updated
            form['explain_reject']                                                        # explanation of rejection
        ])

        text = f"Proposed alternative: {alt}: {form['explain_reject']}"
        self.game.add_move(user=self.user, code=models.Move.Code.MODIFIED_EDIT, text=text)
        WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.MODIFIED_EDIT}: \"{text}\"")


# -------------------------------------------------------------------------------------------------------------------- #


"""
    (B) Add Facts FORM

    If the Player wants to add a new fact pair in the current argument structure, the Player can do so by providing the
    source and target facts to add. The Player should add facts when they feel the new fact pair is relevant to the
    argument structure (either it helps refine or point out weaknesses in the argument structure). After submitting this
    form, the process() method must be invoked to update the game state as well as switch game control
    accordingly ---> Opponent (Proposed Add).
"""


class AddFactsForm(MoveForm):

    source_add = forms.CharField(required=False, max_length=1024)
    target_add = forms.CharField(required=False, max_length=1024)
    explain_add = forms.CharField(required=False, label="Why do you think they are necessary?", max_length=1024)

    def clean(self):
        super().clean()
        data = self.cleaned_data

        source, target = data['source_add'], data['target_add']
        if models.FactPair.objects.filter(game=self.game, source_fact=source, target_fact=target).exists():
            self.add_error('source_add', forms.ValidationError("Facts already exist"))
            WGA_GAME_LOGGER.debug(f"Invalid form: Facts already exist. {data}")

        return self.cleaned_data

    def process(self):
        if self.is_valid():
            form = self.cleaned_data
            new = models.FactPair(source_fact=form['source_add'], target_fact=form['target_add'])

            self.game.context = models.Game.Context.PROPOSED_ADD
            self.game.turn = models.Game.Turn.ADVOCATE if self.is_critic else models.Game.Turn.CRITIC
            self.game.set_context_data([
                form['source_add'], form['target_add'],                                   # FactPair to be added
                form['explain_add']                                                       # explanation of addition
            ])

            text = f"Proposed adding facts: {new}"
            self.game.add_move(user=self.user, code=models.Move.Code.PROPOSED_ADD, text=text)
            WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.PROPOSED_ADD}: \"{text}\"")


"""
    (B) Proposed Add FORM

    After the Opponent submits an add facts form, the Player must then respond to the proposal (accept / reject /
    modify). The Player has the option of modifying the proposal, which essentially creates a new proposal (based on the
    old proposal). After submitting this form, the process() method must be invoked to update the game state as well as
    switch game control accordingly:
    
        --- accept  ::  ---> Player (Idle)
        --- reject  ::  ---> Opponent (Idle)
        --- modify  ::  ---> Opponent (Proposed Add)
"""


class ProposedAddForm(MoveForm):

    ACCEPT = 'accept'
    REJECT = 'reject'
    MODIFY = 'modify'

    response = forms.ChoiceField(widget=forms.RadioSelect, choices=[
        (ACCEPT, "Accept"),
        (REJECT, "Reject"),
        (MODIFY, "Offer alternative")
    ])
    explain_reject = forms.CharField(required=False, label="Why are you rejecting the proposal?", max_length=1024)
    source_add = forms.CharField(required=False, max_length=1024)
    target_add = forms.CharField(required=False, max_length=1024)

    def clean(self):
        super().clean()
        data = self.cleaned_data

        source, target = data['source_add'], data['target_add']
        if models.FactPair.objects.filter(game=self.game, source_fact=source, target_fact=target).exists():
            self.add_error('source_add', forms.ValidationError("Facts already exist"))
            WGA_GAME_LOGGER.debug(f"Invalid form: Facts already exist. {data}")

        return self.cleaned_data

    def process(self):
        if self.is_valid():
            form = self.cleaned_data
            if form['response'] == self.ACCEPT:
                self._process_accept()
            elif form['response'] == self.REJECT:
                self._process_reject()
            elif form['response'] == self.MODIFY:
                self._process_modify()

    def _process_accept(self):
        form = self.cleaned_data
        data = self.game.get_context_data()

        models.FactPair.objects.create(game=self.game, source_fact=data[0], target_fact=data[1])
        self.game.context = models.Game.Context.IDLE
        self.game.turn = models.Game.Turn.CRITIC if self.is_critic else models.Game.Turn.ADVOCATE
        self.game.set_context_data([])

        text = "Accepted proposed addition"
        self.game.add_move(user=self.user, code=models.Move.Code.ACCEPTED_ADD, text=text)
        WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.ACCEPTED_ADD}: \"{text}\"")

    def _process_reject(self):
        form = self.cleaned_data

        self.game.context = models.Game.Context.IDLE
        self.game.turn = models.Game.Turn.ADVOCATE if self.is_critic else models.Game.Turn.CRITIC
        self.game.set_context_data([])

        text = f"Rejected proposed addition: {form['explain_reject']}"
        self.game.add_move(user=self.user, code=models.Move.Code.REJECTED_ADD, text=text)
        WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.REJECTED_ADD}: \"{text}\"")

    def _process_modify(self):
        form = self.cleaned_data

        self.game.context = 'Proposed Add'
        self.game.turn = models.Game.Turn.ADVOCATE if self.is_critic else models.Game.Turn.CRITIC
        alt = models.FactPair(source_fact=form['source_add'], target_fact=form['target_add'])
        self.game.set_context_data([
            form['source_add'], form['target_add'],                                       # FactPair to be added
            form['explain_reject']                                                        # explanation of addition
        ])

        text = f"Proposed alternative: {alt}: {form['explain_reject']}"
        self.game.add_move(user=self.user, code=models.Move.Code.MODIFIED_ADD, text=text)
        WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.MODIFIED_ADD}: \"{text}\"")


# -------------------------------------------------------------------------------------------------------------------- #


"""
    (B) Pass FORM
    
    The Player can opt to pass their turn if they see that there is more reasonable moves they can make. The Advocate
    may pass at anytime but the Critic may only pass after 8 moves have been made (to ensure that an effort was made in
    refining the argument structure). When two consecutive passes have been made (which means both the Advocate and
    Critic cannot see any reasonable moves they can make), the game ends.
"""


class PassForm(MoveForm):

    def process(self):
        if self.is_valid():
            self.game.context = models.Game.Context.IDLE
            self.game.turn = models.Game.Turn.ADVOCATE if self.is_critic else models.Game.Turn.CRITIC

            text = "Passed"
            self.game.add_move(user=self.user, code=models.Move.Code.PASS, text=text)
            WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.PASS}: \"{text}\"")

            self._process_end()

    def _process_end(self):
        if models.Move.Code.PASS in str(list(self.game.move_set.all().order_by('date'))[-2]):  # End the game
            self.game.context = models.Game.Context.COMPLETED
            self.game.turn = models.Game.Turn.COMPLETED
            text = "Registered two consecutive passes, ending the game"
            self.game.add_move(user=self.user, code=models.Move.Code.COMPLETED, text=text)
            WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.COMPLETED}: \"{text}\"")


# -------------------------------------------------------------------------------------------------------------------- #


"""
    (B) Report FORM
    
    If the Player is experiencing a technical or logistic issue (must drop out pre-maturely, for example) or the
    Opponent is behaving contrary to the spirit of the game, the Player can fill out a report form. By doing so, the
    game is suspended until a moderator can review the report. Depending on the moderator's final decisions and
    comments, either the Advocate or Critic can resume the game (at the Idle context). In addition, the game may be
    terminated.
"""


class ReportForm(MoveForm):

    text = forms.CharField(required=False, label="Describe the problem you are reporting", max_length=1024)

    def process(self):
        if self.is_valid():
            form = self.cleaned_data

            models.Report.objects.create(user=self.user, game=self.game, text=form['text'])
            self.game.context = models.Game.Context.SUSPENDED
            self.game.turn = models.Game.Turn.MODERATED
            self.game.set_context_data([])

            text = f"Submitted a report to the administrators: {form['text']}"
            self.game.add_move(user=self.user, code=models.Move.Code.REPORT, text=text)
            WGA_GAME_LOGGER.info(f"[{self.user.key}] Processed {models.Move.Code.REPORT}: \"{text}\"")


# -------------------------------------------------------------------------------------------------------------------- #


"""
    Critic & Advocate Idle FORMS
    
    The main forms that displays all move options for the Advocate and Critic. These two classes inherits the
    appropriate forms above depending on their role. Depending on move_choice, the process() method calls the
    corresponding parent's process() method in order to change game states and turn values.
"""


class CriticIdleForm(UpdateFactsForm, AddFactsForm, AttackForm, ReportForm, PassForm):

    class MoveOptions:
        ATTACK = 'attack'
        UPDATE_FACTS = 'update'
        ADD_FACTS = 'add'
        REPORT = 'report'
        PASS = 'pass'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        CHOICES = [
            (self.MoveOptions.ATTACK, "Attack"),
            (self.MoveOptions.UPDATE_FACTS, "Update facts"),
            (self.MoveOptions.ADD_FACTS, "Add facts"),
            (self.MoveOptions.REPORT, "Contact administrators")
        ]
        if self.game.can_pass():
            CHOICES.append((self.MoveOptions.PASS, "Pass"))
        self.fields['move_choice'] = forms.ChoiceField(widget=forms.RadioSelect, choices=CHOICES)

    def process(self):
        if self.is_valid():
            form = self.cleaned_data
            if form['move_choice'] == self.MoveOptions.UPDATE_FACTS:
                UpdateFactsForm.process(self)
            elif form['move_choice'] == self.MoveOptions.ADD_FACTS:
                AddFactsForm.process(self)
            elif form['move_choice'] == self.MoveOptions.ATTACK:
                AttackForm.process(self)
            elif form['move_choice'] == self.MoveOptions.REPORT:
                ReportForm.process(self)
            elif form['move_choice'] == self.MoveOptions.PASS:
                PassForm.process(self)


class AdvocateIdleForm(UpdateFactsForm, AddFactsForm, UpdateRuleForm, ReportForm, PassForm):

    class MoveOptions:
        UPDATE_RULE = 'update_rule'
        UPDATE_FACTS = 'update'
        ADD_FACTS = 'add'
        REPORT = 'report'
        PASS = 'pass'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        CHOICES = [
            (self.MoveOptions.UPDATE_RULE, "Update rule"),
            (self.MoveOptions.UPDATE_FACTS, "Update facts"),
            (self.MoveOptions.ADD_FACTS, "Add facts"),
            (self.MoveOptions.REPORT, "Contact administrators"),
            (self.MoveOptions.PASS, "Pass")
        ]
        self.fields['move_choice'] = forms.ChoiceField(widget=forms.RadioSelect, choices=CHOICES)

    def process(self):
        if self.is_valid():
            form = self.cleaned_data
            if form['move_choice'] == self.MoveOptions.UPDATE_FACTS:
                UpdateFactsForm.process(self)
            elif form['move_choice'] == self.MoveOptions.ADD_FACTS:
                AddFactsForm.process(self)
            elif form['move_choice'] == self.MoveOptions.UPDATE_RULE:
                UpdateRuleForm.process(self)
            elif form['move_choice'] == self.MoveOptions.REPORT:
                ReportForm.process(self)
            elif form['move_choice'] == self.MoveOptions.PASS:
                PassForm.process(self)


########################################################################################################################
