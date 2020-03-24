from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack

from wga.assets_user import consumers

application = ProtocolTypeRouter({
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            SessionMiddlewareStack(
                URLRouter([
                    path('ws/wganalogy_app/user/<str:url_key>/', consumers.GameConsumer),
                    path('ws/wganalogy_app/nav', consumers.NavBarConsumer)
                ])
            )
        )
    ),
})
