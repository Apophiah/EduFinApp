from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """EduFin user. `role` lets the app tell students and staff apart."""

    ROLE_CHOICES = [('student', 'Student'), ('staff', 'Staff')]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')


class AuditEvent(models.Model):
    """Append-only record of security-relevant actions (logins, data changes)."""

    LOGIN = 'login'
    LOGIN_FAILED = 'login_failed'
    LOGIN_BLOCKED = 'login_blocked'
    LOGOUT = 'logout'
    SIGNUP = 'signup'
    TX_CREATE = 'tx_create'
    TX_UPDATE = 'tx_update'
    TX_DELETE = 'tx_delete'
    BUDGET_SAVE = 'budget_save'
    BUDGET_DELETE = 'budget_delete'
    ACTION_CHOICES = [
        (LOGIN, 'Login'),
        (LOGIN_FAILED, 'Failed login'),
        (LOGIN_BLOCKED, 'Login blocked (too many attempts)'),
        (LOGOUT, 'Logout'),
        (SIGNUP, 'Sign up'),
        (TX_CREATE, 'Transaction created'),
        (TX_UPDATE, 'Transaction updated'),
        (TX_DELETE, 'Transaction deleted'),
        (BUDGET_SAVE, 'Budget saved'),
        (BUDGET_DELETE, 'Budget deleted'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    username = models.CharField(max_length=150, blank=True, db_index=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    detail = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.username or "-"} {self.action}'
