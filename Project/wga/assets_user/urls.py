from django.urls import include, path

from . import views


app_name = 'user'


urlpatterns = [

    path('', views.LoginView.as_view(), name='login'),
    path('instruction', views.InstructionsView.as_view(), name='instructions'),
    path('faq', views.FAQView.as_view(), name='faq'),
    path('<str:url_key>/', views.GameView.as_view(), name='game')

]
