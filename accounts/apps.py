from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        from . import audit  # noqa: F401  (connects the login/logout signal handlers)
