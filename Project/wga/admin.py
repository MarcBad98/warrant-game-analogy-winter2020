"""
    WG-A Django Admin

    Register the WG-A Django models here so that they appear in Django's admin app. We can customize what information
    is displayed (in the ListView, but we can view all information in the DetailView) for each model.

    DOCUMENTATION:
    https://docs.djangoproject.com/en/2.2/ref/contrib/admin/
"""

from django.contrib import admin

from . import models


########################################################################################################################


class UserAdmin(admin.ModelAdmin):

    list_display = ['group', 'name', 'key']
    order = ['group', 'name']


class FactPairAdmin(admin.ModelAdmin):

    list_display = ['game', 'source_fact', 'target_fact']
    order = ['game']


class ScenarioPairAdmin(admin.ModelAdmin):

    list_display = ['name', 'source_conclusion', 'target_conclusion']
    order = ['name']


class MoveAdmin(admin.ModelAdmin):

    list_display = ['user', 'game', 'date', 'code', 'text']
    order = ['game', 'date']


class MessageAdmin(admin.ModelAdmin):

    list_display = ['text']
    order = ['text']


class GroupAdmin(admin.ModelAdmin):

    list_display = ['name', 'date', 'case']
    order = ['case', 'date']


class IntermediaryAdmin(admin.ModelAdmin):

    list_display = ['user', 'key', 'role', 'time']
    order = ['user']


class GameAdmin(admin.ModelAdmin):

    list_display = ['group', 'scenario', 'adv_info', 'crt_info', 'rule_antecedent', 'rule_consequent', 'turn']
    order = ['group']


class ReportAdmin(admin.ModelAdmin):

    list_display = ['user', 'date', 'text', 'note', 'resolved', ]
    order = ['resolved']


########################################################################################################################


admin.site.register(models.User, UserAdmin)
admin.site.register(models.FactPair, FactPairAdmin)
admin.site.register(models.ScenarioPair, ScenarioPairAdmin)
admin.site.register(models.Move, MoveAdmin)
admin.site.register(models.Message, MessageAdmin)
admin.site.register(models.Group, GroupAdmin)
admin.site.register(models.Intermediary, IntermediaryAdmin)
admin.site.register(models.Game, GameAdmin)
admin.site.register(models.Report, ReportAdmin)


########################################################################################################################
