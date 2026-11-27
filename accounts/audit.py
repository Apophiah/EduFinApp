"""Audit trail and login throttling."""

import logging
from datetime import timedelta

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone

from .models import AuditEvent

logger = logging.getLogger('edufin.security')

MAX_FAILED_LOGINS = 5
LOCKOUT_WINDOW = timedelta(minutes=15)


def client_ip(request):
    # REMOTE_ADDR only: X-Forwarded-For is client-controlled unless a trusted proxy sets it.
    return request.META.get('REMOTE_ADDR') if request is not None else None


def record(request, action, user=None, username='', detail=''):
    if user is None and request is not None:
        current = getattr(request, 'user', None)
        if current is not None and current.is_authenticated:
            user = current
    username = username or (user.get_username() if user else '')
    event = AuditEvent.objects.create(
        user=user, username=username[:150], action=action,
        ip_address=client_ip(request), detail=detail[:255],
    )
    logger.info('%s user=%s ip=%s %s', action, username or '-', event.ip_address, detail)
    return event


def is_locked_out(username):
    """True if this username had too many failed logins in the lockout window."""
    since = timezone.now() - LOCKOUT_WINDOW
    recent = AuditEvent.objects.filter(
        username__iexact=username, created_at__gte=since,
        action__in=[AuditEvent.LOGIN_FAILED, AuditEvent.LOGIN],
    ).order_by('-created_at').values_list('action', flat=True)[:MAX_FAILED_LOGINS]
    recent = list(recent)
    return len(recent) >= MAX_FAILED_LOGINS and all(a == AuditEvent.LOGIN_FAILED for a in recent)


@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs):
    record(request, AuditEvent.LOGIN, user=user)


@receiver(user_logged_out)
def _on_logout(sender, request, user, **kwargs):
    if user is not None:
        record(request, AuditEvent.LOGOUT, user=user)


@receiver(user_login_failed)
def _on_login_failed(sender, credentials, request=None, **kwargs):
    record(request, AuditEvent.LOGIN_FAILED, username=str(credentials.get('username', ''))[:150])
