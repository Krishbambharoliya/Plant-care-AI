from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('gu', 'Gujarati'),
        ('mr', 'Marathi'),
    ]
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
    ]

    phone_number = models.CharField(max_length=15, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    location_city = models.CharField(max_length=100, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    farm_name = models.CharField(max_length=150, null=True, blank=True)
    farm_size_acres = models.FloatField(null=True, blank=True)
    
    preferred_language = models.CharField(
        max_length=2, 
        choices=LANGUAGE_CHOICES, 
        default='en'
    )
    theme_preference = models.CharField(
        max_length=5, 
        choices=THEME_CHOICES, 
        default='light'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username


class EmailOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20)  # 'register' or 'password_reset'
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.is_verified:
            try:
                import os
                from django.conf import settings
                filepath = os.path.join(settings.BASE_DIR, 'otp_debug.txt')
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"EMAIL: {self.email}\n")
                    f.write(f"OTP CODE: {self.otp}\n")
                    f.write(f"PURPOSE: {self.purpose}\n")
            except Exception:
                pass

    def __str__(self):
        return f"{self.email} - {self.otp} - {self.purpose} (Verified: {self.is_verified})"


class APILimitTracker(models.Model):
    api_name = models.CharField(max_length=50, unique=True, default='crop_api')
    call_count = models.IntegerField(default=0)
    max_limit = models.IntegerField(default=500)

    def __str__(self):
        return f"{self.api_name}: {self.call_count}/{self.max_limit}"


class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='searches')
    query_type = models.CharField(max_length=20)  # 'crop', 'disease', 'weather'
    query_text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.query_type}: {self.query_text}"


class RecoveryTracker(models.Model):
    STATUS_CHOICES = [
        ('ongoing', 'Ongoing Recovery'),
        ('recovered', 'Fully Recovered & Healthy'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recovery_journeys')
    plant_name = models.CharField(max_length=100)
    crop_type = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ongoing', db_index=True)
    watering_frequency = models.CharField(max_length=50, default='Once a day')
    estimated_recovery_weeks = models.IntegerField(default=4)
    light_requirement = models.CharField(max_length=50, default='Direct Sunlight')
    from django.utils import timezone
    start_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s {self.plant_name} ({self.status})"


class RecoveryCheckIn(models.Model):
    tracker = models.ForeignKey(RecoveryTracker, on_delete=models.CASCADE, related_name='checkins')
    week_number = models.IntegerField(db_index=True)
    image = models.ImageField(upload_to='recovery/%Y/%m/')
    symptoms = models.TextField(blank=True, null=True)
    farmer_notes = models.TextField(blank=True, null=True)
    recovery_percentage = models.IntegerField(default=0)
    pest_activity = models.CharField(max_length=20, default='None')
    care_advice = models.TextField()
    is_healthy = models.BooleanField(default=False)
    checkin_date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['week_number']

    def __str__(self):
        return f"{self.tracker.plant_name} - Week {self.week_number}"

