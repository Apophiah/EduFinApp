"""REST API for transactions (Django REST Framework).

Session authentication + CSRF, IsAuthenticated by default (see REST_FRAMEWORK in
settings), and every queryset is limited to the requesting user.
"""

from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from accounts import audit
from accounts.models import AuditEvent

from . import stats
from .models import Transaction
from .validation import clean_description, validate_category_for_kind, validate_date


def _as_drf_error(exc):
    if hasattr(exc, 'message_dict'):
        return serializers.ValidationError(exc.message_dict)
    return serializers.ValidationError(exc.messages)


class TransactionSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'kind', 'category', 'category_label', 'amount', 'description', 'date',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_date(self, value):
        try:
            return validate_date(value)
        except DjangoValidationError as exc:
            raise _as_drf_error(exc)

    def validate_description(self, value):
        try:
            return clean_description(value)
        except DjangoValidationError as exc:
            raise _as_drf_error(exc)

    def validate(self, attrs):
        kind = attrs.get('kind', getattr(self.instance, 'kind', None))
        category = attrs.get('category', getattr(self.instance, 'category', None))
        try:
            validate_category_for_kind(kind, category)
        except DjangoValidationError as exc:
            raise _as_drf_error(exc)
        return attrs


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer

    @classmethod
    def as_view(cls, *args, **kwargs):
        # Let DRF answer 403 JSON itself instead of LoginRequiredMiddleware redirecting.
        return login_not_required(super().as_view(*args, **kwargs))

    def get_queryset(self):
        return Transaction.objects.for_user(self.request.user)

    def perform_create(self, serializer):
        tx = serializer.save(user=self.request.user)
        audit.record(self.request, AuditEvent.TX_CREATE, detail=f'api id={tx.pk}')

    def perform_update(self, serializer):
        tx = serializer.save()
        audit.record(self.request, AuditEvent.TX_UPDATE, detail=f'api id={tx.pk}')

    def perform_destroy(self, instance):
        audit.record(self.request, AuditEvent.TX_DELETE, detail=f'api id={instance.pk}')
        instance.delete()


@login_not_required
@api_view(['GET'])
def summary_view(request):
    data = stats.summary(request.user)
    return Response({key: str(value) if value is not None else None for key, value in data.items()})
