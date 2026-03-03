from django.urls import path
from .views import UserAnalyticsView, create_journal, journal_history


urlpatterns = [
     path("create/", create_journal),
     path("analytics/",UserAnalyticsView.as_view()),
     path("history/", journal_history),
]