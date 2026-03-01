from django.urls import path
from .views import UserAnalyticsView, create_journal


urlpatterns = [
     path("create/", create_journal),
     path("analytics/",UserAnalyticsView.as_view()),
]