from django.contrib import admin
from .models import Crop, Fertilizer, Disease

class CropAdmin(admin.ModelAdmin):
    list_display = ('name', 'scientific_name', 'ideal_temp_min_c', 'ideal_temp_max_c', 'ideal_humidity_min', 'ideal_humidity_max')
    search_fields = ('name', 'scientific_name')

class FertilizerAdmin(admin.ModelAdmin):
    list_display = ('name', 'fertilizer_type')
    search_fields = ('name',)
    list_filter = ('fertilizer_type',)

class DiseaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'crop')
    search_fields = ('name', 'crop__name')
    list_filter = ('crop',)
    filter_horizontal = ('fertilizers_recommended',)

admin.site.register(Crop, CropAdmin)
admin.site.register(Fertilizer, FertilizerAdmin)
admin.site.register(Disease, DiseaseAdmin)
