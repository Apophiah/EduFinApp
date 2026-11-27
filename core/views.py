from django.contrib.auth.decorators import login_not_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import Testing
from core.serializers import TestingSerializer


@login_not_required  # DRF's IsAuthenticated answers 403 itself
@api_view(['GET'])
def testing_view(request):
    items = Testing.objects.all()
    serializer = TestingSerializer(items, many=True)
    return Response(serializer.data)


@login_not_required
@require_GET
def health_check(request):
    return JsonResponse({'status': 'OK'})
