from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.urls import include, path

from . import views


urlpatterns = [
    path("healthz/", views.healthcheck, name="healthcheck"),
    path("", views.landing, name="landing"),
    path("signup/", views.signup_view, name="signup"),
    path("activate/<uidb64>/<token>/", views.activate_account, name="activate-account"),
    path("login/", LoginView.as_view(template_name="core/login.html"), name="login"),
    path(
        "password-reset/",
        PasswordResetView.as_view(
            template_name="core/password_reset_form.html",
            email_template_name="core/emails/password_reset_email.txt",
            subject_template_name="core/emails/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path("password-reset/done/", PasswordResetDoneView.as_view(template_name="core/password_reset_done.html"), name="password_reset_done"),
    path(
        "reset/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(template_name="core/password_reset_confirm.html"),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        PasswordResetCompleteView.as_view(template_name="core/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", views.profile_self, name="profile-self"),
    path("tasks/", views.tasks_list, name="tasks"),
    path("tasks/level/<int:level_number>/", views.tasks_list, name="tasks-by-level"),
    path("theory/<int:level_id>/", views.theory_detail, name="theory-detail"),
    path("playground/<str:task_id>/", views.playground, name="playground"),
    path(
        "playground/<str:task_id>/start/",
        views.playground_start,
        name="playground-start",
    ),
    path(
        "playground/<str:task_id>/run/",
        views.playground_run_command,
        name="playground-run-command",
    ),
    path(
        "playground/<str:task_id>/file/read/",
        views.playground_read_file,
        name="playground-read-file",
    ),
    path(
        "playground/<str:task_id>/file/write/",
        views.playground_write_file,
        name="playground-write-file",
    ),
    path(
        "playground/<str:task_id>/validate/",
        views.playground_validate,
        name="playground-validate",
    ),
    path(
        "playground/<str:task_id>/reset/",
        views.playground_reset,
        name="playground-reset",
    ),
    path(
        "playground/<str:task_id>/stop/",
        views.playground_stop,
        name="playground-stop",
    ),
    path(
        "playground/<str:task_id>/hint/",
        views.playground_hint,
        name="playground-hint",
    ),
    path(
        "playground/<str:task_id>/log/",
        views.playground_log,
        name="playground-log",
    ),
    path(
        "playground/<str:task_id>/log-stream/",
        views.playground_log_stream,
        name="playground-log-stream",
    ),
    path("quiz/", include("apps.quiz.urls")),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path("profile/<str:username>/", views.public_profile, name="public-profile"),
]
