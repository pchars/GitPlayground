from apps.core.views.auth_rate_limited import RateLimitedLoginView, RateLimitedPasswordResetView
from django.contrib.auth.views import (
    LogoutView,
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
    path("login/", RateLimitedLoginView.as_view(), name="login"),
    path(
        "password-reset/",
        RateLimitedPasswordResetView.as_view(),
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
    path("profile/edit/", views.profile_edit, name="profile-edit"),
    path("profile/certificate.pdf", views.certificate_download, name="certificate-download"),
    path("profile/certificate/resend/", views.certificate_resend, name="certificate-resend"),
    path("certificate/verify/<str:code>/", views.certificate_verify, name="certificate-verify"),
    path("legal/privacy/", views.privacy_policy, name="privacy-policy"),
    path("legal/marketing/", views.marketing_consent_info, name="marketing-consent"),
    path("support/donate/", views.support_donate, name="support-donate"),
    path("tasks/", views.tasks_list, name="tasks"),
    path("tasks/level/<int:level_number>/", views.tasks_list, name="tasks-by-level"),
    path("theory/", views.theory_home, name="theory-home"),
    path("theory/<int:level_id>/", views.theory_detail, name="theory-detail"),
    path("playground/<str:task_id>/", views.playground, name="playground"),
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
        "playground/<str:task_id>/hint/",
        views.playground_hint,
        name="playground-hint",
    ),
    path("quiz/", include("apps.quiz.urls")),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path("profile/<str:username>/", views.public_profile, name="public-profile"),
]
