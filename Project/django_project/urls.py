from django.urls import include, path

# Project URLconf settings


from django.contrib import admin


urlpatterns = [

    path('admin/', admin.site.urls, name='admin'),
    path('wganalogy_app/', include('wga.urls'))

]
