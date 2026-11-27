from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views import health_check, testing_view
from transaction.api import TransactionViewSet, summary_view

router = DefaultRouter(trailing_slash=True)
router.include_root_view = False
router.register('transactions', TransactionViewSet, basename='api-transaction')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('api/summary/', summary_view, name='api-summary'),
    path('api/', include(router.urls)),
    path('testing', testing_view, name='testing'),
    path('health', health_check, name='health'),
    path('', include('transaction.urls')),
]
