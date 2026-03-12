from django.http import JsonResponse
from django.shortcuts import render
from core.models import Testing
from core.serializers import TestingSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(["GET"])
def testing_view(request):
    
    data_to_test = Testing.objects.all()
    serializer = TestingSerializer(data_to_test, many=True)

    return Response(serializer.data_to_test)
def health_check(request):
    return JsonResponse ({'status': 'OK'})