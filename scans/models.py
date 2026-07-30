from django.db import models
from django.conf import settings

class ScanHistory(models.Model):
    ORGAN_CHOICES = [
        ('leaf', 'Leaf'),
        ('flower', 'Flower'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='scans'
    )
    image = models.ImageField(upload_to='scans/%Y/%m/')
    organ = models.CharField(
        max_length=10, 
        choices=ORGAN_CHOICES, 
        default='leaf'
    )
    
    # Identification details from PlantNet
    identified_species = models.CharField(max_length=200)
    identified_common_name = models.CharField(max_length=200, null=True, blank=True)
    confidence_score = models.FloatField()
    plantnet_raw_response = models.JSONField()
    
    # Library matching details
    matched_crop_name = models.CharField(max_length=100, null=True, blank=True)
    disease_identified = models.CharField(max_length=100, null=True, blank=True)
    is_healthy = models.BooleanField()
    severity = models.CharField(max_length=20, default='N/A')
    
    # Treatment recommendations
    treatment_type = models.CharField(max_length=50, default='None')
    treatment_organic_recommendation = models.TextField(null=True, blank=True)
    treatment_chemical_recommendation = models.TextField(null=True, blank=True)
    treatment_dosage = models.CharField(max_length=100, null=True, blank=True)
    treatment_application_method = models.CharField(max_length=200, null=True, blank=True)
    
    fertilizer_recommendation = models.TextField(null=True, blank=True)
    
    # Location data
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
 
    class Meta:
        ordering = ['-created_at']
 
    def __str__(self):
        return f"{self.user.username} - {self.identified_species} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
 
 
class FutureDataset(models.Model):
    ORGAN_CHOICES = [
        ('leaf', 'Leaf'),
        ('flower', 'Flower'),
    ]
 
    username = models.CharField(max_length=150, null=True, blank=True)
    image_name = models.CharField(max_length=255)
    organ = models.CharField(
        max_length=10, 
        choices=ORGAN_CHOICES, 
        default='leaf'
    )
    
    # Classification prediction outcomes
    identified_species = models.CharField(max_length=200)
    identified_common_name = models.CharField(max_length=200, null=True, blank=True)
    confidence_score = models.FloatField()
    
    is_healthy = models.BooleanField()
    severity = models.CharField(max_length=20, default='N/A')
    disease_identified = models.CharField(max_length=100, null=True, blank=True)
    
    # Treatment recommendations
    treatment_type = models.CharField(max_length=50, default='None')
    treatment_organic_recommendation = models.TextField(null=True, blank=True)
    treatment_chemical_recommendation = models.TextField(null=True, blank=True)
    treatment_dosage = models.CharField(max_length=100, null=True, blank=True)
    treatment_application_method = models.CharField(max_length=200, null=True, blank=True)
    
    fertilizer_recommendation = models.TextField(null=True, blank=True)
    
    # Geolocational tags
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
 
    class Meta:
        db_table = 'FUTUREDATASET'
        ordering = ['-created_at']
 
    def __str__(self):
        return f"{self.username} - {self.identified_species} - {self.disease_identified or 'Healthy'} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
