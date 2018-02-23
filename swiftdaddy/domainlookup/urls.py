from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.desktop, name='desktop'),
    url(r'^text_query$', views.text_query, name='text_query'),
    url(r'^file_query$', views.file_query, name='file_query'),
    url(r'^database$', views.database, name='database'),
    url(r'^upload_domains', views.upload_domains, name='upload_domains'),
    url(r'^card$', views.card, name='card'),
    url(r'^greetings$', views.greetings, name='greetings'),
    url(r'^welcome$', views.welcome, name='welcome'),
    url(r'^confetti$', views.confetti, name='confetti'),
]