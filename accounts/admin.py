from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditEvent, User


@admin.register(User)
class EduFinUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('EduFin', {'fields': ('role',)}),)
    list_display = ('username', 'email', 'role', 'is_staff', 'date_joined')


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """Read-only: audit events can be viewed but never edited or deleted from the admin."""

    list_display = ('created_at', 'username', 'action', 'ip_address', 'detail')
    list_filter = ('action',)
    search_fields = ('username', 'detail')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
