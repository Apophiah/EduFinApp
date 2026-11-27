from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from . import audit
from .models import AuditEvent, User


class SignUpForm(UserCreationForm):
    """Sign-up form. Passwords go through AUTH_PASSWORD_VALIDATORS and are stored hashed."""

    email = forms.EmailField(required=True, max_length=254)
    first_name = forms.CharField(required=False, max_length=150, label='First name')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_first_name(self):
        return self.cleaned_data.get('first_name', '').strip()


class ThrottledAuthenticationForm(AuthenticationForm):
    """Login form that refuses a username after too many failed attempts."""

    error_messages = {
        **AuthenticationForm.error_messages,
        'locked': 'Too many failed attempts. Please wait 15 minutes and try again.',
    }

    def clean(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if username and audit.is_locked_out(username):
            audit.record(self.request, AuditEvent.LOGIN_BLOCKED, username=username)
            raise forms.ValidationError(self.error_messages['locked'], code='locked')
        return super().clean()
