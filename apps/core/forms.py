from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.users.legal import (
    MARKETING_CONSENT_SNAPSHOT,
    MARKETING_CONSENT_VERSION,
    PRIVACY_CONSENT_SNAPSHOT,
    PRIVACY_POLICY_VERSION,
)
from apps.users.models import UserProfile
from apps.users.validators import validate_pseudonym

PASSWORD_POLICY_MESSAGE = (
    "Пароль должен иметь ≥8 символов, буквы и цифры, "
    "не должен быть похожим на email или логин"
)


class SignUpForm(UserCreationForm):
    certificate_name = forms.CharField(
        label="Имя и фамилия",
        max_length=120,
        help_text="Будет указано на сертификате о прохождении курса. Укажите настоящие имя и фамилию.",
    )
    pseudonym = forms.CharField(
        label="Псевдоним",
        max_length=10,
        help_text="До 10 символов: латиница, цифры, подчёркивание. Отображается в таблице лидеров.",
    )
    email = forms.EmailField(required=True, label="Электронная почта")
    learning_goal = forms.ChoiceField(
        label="Цель обучения",
        choices=UserProfile.LearningGoal.choices,
    )
    knowledge_level = forms.ChoiceField(
        label="Текущий уровень знаний Git",
        choices=UserProfile.KnowledgeLevel.choices,
    )
    job_role = forms.CharField(label="Должность", max_length=120, required=False)
    company_name = forms.CharField(label="Компания", max_length=160, required=False)
    marketing_opt_in = forms.BooleanField(
        label="Получать новости и советы по email",
        required=False,
    )
    privacy_policy_accepted = forms.BooleanField(
        label="Я принимаю Политику конфиденциальности",
        required=True,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("username", None)
        self.fields["password1"].help_text = ""
        self.fields["password2"].help_text = ""

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует.")
        return email

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if password is None:
            return password
        email = (self.cleaned_data.get("email") or "").strip().lower()
        candidate = User(username=email, email=email)
        try:
            validate_password(password, candidate)
        except ValidationError:
            raise forms.ValidationError(PASSWORD_POLICY_MESSAGE) from None
        return password

    def clean(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email:
            self.cleaned_data["username"] = email
        return super().clean()

    def _post_clean(self):
        # Skip UserCreationForm.validate_password_for_user — password rules are in clean_password1.
        super(forms.ModelForm, self)._post_clean()

    def clean_certificate_name(self):
        value = (self.cleaned_data.get("certificate_name") or "").strip()
        if len(value) < 2:
            raise forms.ValidationError("Укажите имя и фамилию для сертификата.")
        return value

    def clean_pseudonym(self):
        value = validate_pseudonym(self.cleaned_data.get("pseudonym", ""))
        if UserProfile.objects.filter(pseudonym__iexact=value).exists():
            raise forms.ValidationError("Этот псевдоним уже занят.")
        return value

    def clean_privacy_policy_accepted(self):
        if not self.cleaned_data.get("privacy_policy_accepted"):
            raise forms.ValidationError("Необходимо принять Политику конфиденциальности.")
        return True

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data["email"]
        user.username = email
        user.email = email
        if commit:
            user.save()
        return user

    def save_profile(self, user: User) -> UserProfile:
        now = timezone.now()
        marketing_opt_in = bool(self.cleaned_data.get("marketing_opt_in"))
        return UserProfile.objects.create(
            user=user,
            pseudonym=self.cleaned_data["pseudonym"],
            certificate_name=self.cleaned_data["certificate_name"],
            learning_goal=self.cleaned_data["learning_goal"],
            knowledge_level=self.cleaned_data["knowledge_level"],
            job_role=(self.cleaned_data.get("job_role") or "").strip(),
            company_name=(self.cleaned_data.get("company_name") or "").strip(),
            marketing_opt_in=marketing_opt_in,
            marketing_consent_at=now if marketing_opt_in else None,
            marketing_consent_version=MARKETING_CONSENT_VERSION if marketing_opt_in else "",
            marketing_consent_text=MARKETING_CONSENT_SNAPSHOT if marketing_opt_in else "",
            privacy_consent_at=now,
            privacy_consent_version=PRIVACY_POLICY_VERSION,
            privacy_consent_text=PRIVACY_CONSENT_SNAPSHOT,
        )


class ProfileEditForm(forms.Form):
    certificate_name = forms.CharField(label="Имя и фамилия", max_length=120)
    pseudonym = forms.CharField(label="Псевдоним", max_length=10)
    email = forms.EmailField(label="Электронная почта")
    learning_goal = forms.ChoiceField(label="Цель обучения", choices=UserProfile.LearningGoal.choices)
    knowledge_level = forms.ChoiceField(
        label="Текущий уровень знаний Git",
        choices=UserProfile.KnowledgeLevel.choices,
    )
    job_role = forms.CharField(label="Должность", max_length=120, required=False)
    company_name = forms.CharField(label="Компания", max_length=160, required=False)
    marketing_opt_in = forms.BooleanField(
        label="Получать новости и советы по email",
        required=False,
    )

    def __init__(self, *args, user: User, profile: UserProfile, **kwargs):
        self.user = user
        self.profile = profile
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial.update(
                {
                    "certificate_name": profile.certificate_name,
                    "pseudonym": profile.pseudonym,
                    "email": user.email,
                    "learning_goal": profile.learning_goal,
                    "knowledge_level": profile.knowledge_level,
                    "job_role": profile.job_role,
                    "company_name": profile.company_name,
                    "marketing_opt_in": profile.marketing_opt_in,
                }
            )

    def clean_certificate_name(self):
        value = (self.cleaned_data.get("certificate_name") or "").strip()
        if len(value) < 2:
            raise forms.ValidationError("Укажите имя и фамилию для сертификата.")
        return value

    def clean_pseudonym(self):
        value = validate_pseudonym(self.cleaned_data.get("pseudonym", ""))
        if UserProfile.objects.filter(pseudonym__iexact=value).exclude(pk=self.profile.pk).exists():
            raise forms.ValidationError("Этот псевдоним уже занят.")
        return value

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует.")
        return email

    def save(self) -> UserProfile:
        now = timezone.now()
        marketing_opt_in = bool(self.cleaned_data.get("marketing_opt_in"))
        was_opted_in = self.profile.marketing_opt_in
        email = self.cleaned_data["email"]

        self.user.email = email
        self.user.username = email
        self.user.save(update_fields=["email", "username"])

        self.profile.certificate_name = self.cleaned_data["certificate_name"]
        self.profile.pseudonym = self.cleaned_data["pseudonym"]
        self.profile.learning_goal = self.cleaned_data["learning_goal"]
        self.profile.knowledge_level = self.cleaned_data["knowledge_level"]
        self.profile.job_role = (self.cleaned_data.get("job_role") or "").strip()
        self.profile.company_name = (self.cleaned_data.get("company_name") or "").strip()
        self.profile.marketing_opt_in = marketing_opt_in

        if marketing_opt_in and not was_opted_in:
            self.profile.marketing_consent_at = now
            self.profile.marketing_consent_version = MARKETING_CONSENT_VERSION
            self.profile.marketing_consent_text = MARKETING_CONSENT_SNAPSHOT

        self.profile.save()
        return self.profile


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Электронная почта",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    error_messages = {
        "invalid_login": "Неверный email или пароль.",
        "inactive": "Этот аккаунт деактивирован.",
    }

    def clean_username(self):
        return (self.cleaned_data.get("username") or "").strip().lower()
