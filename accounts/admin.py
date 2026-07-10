from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = UserAdmin.fieldsets + (
        ('PlantCare Profile', {
            'fields': (
                'phone_number',
                'profile_image',
                'location_city',
                'latitude',
                'longitude',
                'farm_name',
                'farm_size_acres',
                'preferred_language',
                'theme_preference',
            )
        }),
    )
    list_display = UserAdmin.list_display + ('phone_number', 'location_city', 'preferred_language', 'theme_preference')

admin.site.register(User, CustomUserAdmin)
