"""
    WG-A Admin Django URLconf

    This file contains all the URL configurations used by the WG-A Admin app.

    DOCUMENTATION
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
"""

from django.urls import path

from . import views


app_name = 'moderator'


urlpatterns = [

    path('', views.IndexView.as_view(), name='index'),
    path('groups', views.GroupListView.as_view(), name='list-of-groups'),
    path('groups/<str:group_name>/', views.GroupDetailView.as_view(), name='group'),
    path('groups/<str:group_name>/add/', views.AddGameView.as_view(), name='group-add'),
    path('groups/<str:group_name>/add/check', views.CheckAddGameView.as_view(), name='group-add-check'),
    path('groups/<str:group_name>/shuffle', views.ShuffleGamesView.as_view(), name='group-shuffle'),
    path('groups/<str:group_name>/download', views.DownloadView.as_view(), name='group-download'),
    path('groups/<str:group_name>/messages/<str:url_key>', views.MessageCreateView.as_view(), name='messages'),
    path('groups/<str:group_name>/<str:url_key>', views.IntermediaryUpdateView.as_view(), name='group-edit'),
    path('reports', views.ReportListView.as_view(), name='list-of-reports'),
    path('reports/<int:report_id>', views.ReportResolveView.as_view(), name='report-resolve')

]
