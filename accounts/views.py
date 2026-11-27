from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from . import audit
from .forms import SignUpForm, ThrottledAuthenticationForm
from .models import AuditEvent


class LoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'
    authentication_form = ThrottledAuthenticationForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    """Logout is POST-only (with a CSRF token), so a link on another site cannot log you out."""


@login_not_required
@require_http_methods(['GET', 'POST'])
def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        audit.record(request, AuditEvent.SIGNUP, user=user)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f'Welcome to EduFin, {user.first_name or user.username}!')
        return redirect('dashboard')
    return render(request, 'accounts/signup.html', {'form': form})
