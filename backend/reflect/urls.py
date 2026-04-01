from django.urls import path
from . import views

urlpatterns = [
    path('start/', views.start_session, name='reflect_start'),
    path('message/', views.send_message, name='reflect_message'),
    path('end/', views.end_session, name='reflect_end'),
    path('history/', views.session_history, name='reflect_history'),
]