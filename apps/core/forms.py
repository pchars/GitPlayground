from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = "Не короче 8 символов."

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует.")
        return email


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Пожалуйста, введите правильные имя пользователя и пароль.",
        "inactive": "Этот аккаунт деактивирован.",
    }
