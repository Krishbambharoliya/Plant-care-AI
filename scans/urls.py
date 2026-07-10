from django.urls import path
from .views import ScanUploadView, ScanHistoryView, ScanDetailView, ScanStatsView

urlpatterns = [
    path('upload/', ScanUploadView.as_view(), name='api-scan-upload'),
    path('history/', ScanHistoryView.as_view(), name='api-scan-history'),
    path('history/<int:pk>/', ScanDetailView.as_view(), name='api-scan-detail'),
    path('stats/', ScanStatsView.as_view(), name='api-scan-stats'),
]
