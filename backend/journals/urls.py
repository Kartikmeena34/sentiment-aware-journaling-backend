from django.urls import path
from .views import create_journal
from .auth_views import register

urlpatterns = [
     path("create/", create_journal),
     path("register/", register),
]