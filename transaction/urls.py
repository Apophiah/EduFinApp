from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/new/', views.transaction_create, name='transaction_create'),
    path('transactions/<int:pk>/edit/', views.transaction_update, name='transaction_update'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    path('budgets/', views.budgets, name='budgets'),
    path('budgets/<int:pk>/delete/', views.budget_delete, name='budget_delete'),
    path('learn/', views.learn, name='learn'),
]
