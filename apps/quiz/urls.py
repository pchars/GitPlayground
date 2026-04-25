from django.urls import path

from . import views

urlpatterns = [
    path("", views.quiz_home, name="quiz-home"),
    path("play/", views.quiz_play, name="quiz-play"),
    path("reset/", views.quiz_reset_progress, name="quiz-reset-progress"),
]
