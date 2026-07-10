from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Crop, Disease
from .serializers import CropListSerializer, CropDetailSerializer, DiseaseSerializer

from rest_framework import mixins

class CropListView(mixins.ListModelMixin, generics.GenericAPIView):
    queryset = Crop.objects.all().order_by('name')
    serializer_class = CropListSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

class CropDetailView(mixins.RetrieveModelMixin, generics.GenericAPIView):
    queryset = Crop.objects.all()
    serializer_class = CropDetailSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

class DiseaseSearchView(mixins.ListModelMixin, generics.GenericAPIView):
    serializer_class = DiseaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Disease.objects.all().order_by('name')
        crop_name = self.request.data.get('crop_name', self.request.query_params.get('crop_name'))
        if crop_name:
            queryset = queryset.filter(crop__name__iexact=crop_name)
        return queryset

    def post(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
