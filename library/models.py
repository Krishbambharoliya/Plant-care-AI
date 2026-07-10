from django.db import models

class Crop(models.Model):
    name = models.CharField(max_length=100, unique=True)
    scientific_name = models.CharField(max_length=150)
    description = models.TextField()
    
    # 3-Language localized fields
    description_en = models.TextField(blank=True, null=True)
    description_hi = models.TextField(blank=True, null=True)
    description_gu = models.TextField(blank=True, null=True)
    
    image = models.ImageField(upload_to='crops/')
    
    # Ideal environmental ranges
    ideal_temp_min_c = models.FloatField()
    ideal_temp_max_c = models.FloatField()
    ideal_humidity_min = models.FloatField()
    ideal_humidity_max = models.FloatField()

    def __str__(self):
        return self.name

class Fertilizer(models.Model):
    FERTILIZER_TYPES = [
        ('organic', 'Organic'),
        ('chemical', 'Chemical'),
        ('bio', 'Bio'),
    ]
    name = models.CharField(max_length=100, unique=True)
    fertilizer_type = models.CharField(max_length=10, choices=FERTILIZER_TYPES)
    description = models.TextField()
    usage_instructions = models.TextField()
    
    # 3-Language localized fields
    description_en = models.TextField(blank=True, null=True)
    description_hi = models.TextField(blank=True, null=True)
    description_gu = models.TextField(blank=True, null=True)
    
    usage_instructions_en = models.TextField(blank=True, null=True)
    usage_instructions_hi = models.TextField(blank=True, null=True)
    usage_instructions_gu = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Disease(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='diseases')
    name = models.CharField(max_length=100)
    
    # Base fields
    symptoms = models.TextField()
    causes = models.TextField()
    treatment = models.TextField()
    
    # 3-Language localized fields
    symptoms_en = models.TextField(blank=True, null=True)
    symptoms_hi = models.TextField(blank=True, null=True)
    symptoms_gu = models.TextField(blank=True, null=True)
    
    causes_en = models.TextField(blank=True, null=True)
    causes_hi = models.TextField(blank=True, null=True)
    causes_gu = models.TextField(blank=True, null=True)
    
    treatment_en = models.TextField(blank=True, null=True)
    treatment_hi = models.TextField(blank=True, null=True)
    treatment_gu = models.TextField(blank=True, null=True)
    
    fertilizers_recommended = models.ManyToManyField(Fertilizer, blank=True)
    
    # 3-Language localized Pesticides fields
    pesticides_recommended = models.TextField(blank=True, null=True)
    pesticides_recommended_en = models.TextField(blank=True, null=True)
    pesticides_recommended_hi = models.TextField(blank=True, null=True)
    pesticides_recommended_gu = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('crop', 'name')

    def __str__(self):
        return f"{self.crop.name} - {self.name}"
