from django.contrib import admin
from .models import ScanHistory

class ScanHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'identified_species', 'matched_crop_name', 'disease_identified', 'is_healthy', 'organ', 'created_at')
    list_filter = ('is_healthy', 'organ', 'created_at')
    search_fields = ('user__username', 'identified_species', 'matched_crop_name', 'disease_identified')

admin.site.register(ScanHistory, ScanHistoryAdmin)
