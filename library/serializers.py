from rest_framework import serializers
from .models import Crop, Fertilizer, Disease

class FertilizerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fertilizer
        fields = ['id', 'name', 'fertilizer_type', 'description', 'usage_instructions']

class DiseaseSerializer(serializers.ModelSerializer):
    fertilizers_recommended = FertilizerSerializer(many=True, read_only=True)

    class Meta:
        model = Disease
        fields = ['id', 'name', 'symptoms', 'causes', 'treatment', 'fertilizers_recommended']

class CropListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crop
        fields = ['id', 'name', 'image']

class CropDetailSerializer(serializers.ModelSerializer):
    diseases = DiseaseSerializer(many=True, read_only=True)

    class Meta:
        model = Crop
        fields = [
            'id', 'name', 'scientific_name', 'description', 'image',
            'ideal_temp_min_c', 'ideal_temp_max_c', 'ideal_humidity_min',
            'ideal_humidity_max', 'diseases'
        ]
