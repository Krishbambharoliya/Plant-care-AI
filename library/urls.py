from django.urls import path
from .views import CropListView, CropDetailView, DiseaseSearchView

urlpatterns = [
    path('crops/', CropListView.as_view(), name='api-crop-list'),
    path('crops/<int:pk>/', CropDetailView.as_view(), name='api-crop-detail'),
    path('diseases/', DiseaseSearchView.as_view(), name='api-disease-search'),
]
