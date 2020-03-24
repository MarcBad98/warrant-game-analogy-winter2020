"""
    WG-A Django URLconf

    This file contains all the URL configurations used by the WG-A app, combining the URL patterns from urls_admin.py
    and urls_user.py.

    DOCUMENTATION
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
"""

from django.urls import include, path


urlpatterns = [

    path('moderator/', include('wga.assets_admin.urls')),  # admin pages
    path('user/', include('wga.assets_user.urls')),        # user pages

]
