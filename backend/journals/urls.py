from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_journal, name='create_journal'),
    path('analytics/', views.UserAnalyticsView.as_view(), name='user_analytics'),
    path('insights/', views.user_insights, name='user_insights'),
    path('history/', views.journal_history, name='journal_history'),
    path('reflect/save/', views.save_reflection, name='save_reflection'),
]