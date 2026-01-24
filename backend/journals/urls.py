from django.urls import path
from .views import create_journal

urlpatterns = [
     path("create/", create_journal),
]