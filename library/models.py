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

    # Soil type requirements
    soil_type = models.CharField(max_length=200, default='Loamy Soil')
    soil_type_en = models.CharField(max_length=200, blank=True, null=True)
    soil_type_hi = models.CharField(max_length=200, blank=True, null=True)
    soil_type_gu = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name

    @property
    def image_url(self):
        curated = {
            'Tomato': 'https://images.unsplash.com/photo-1592417817098-8f3d6eb19675?auto=format&fit=crop&w=600&q=80',
            'Potato': 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=600&q=80',
            'Wheat': 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=600&q=80',
            'Rice': 'https://images.unsplash.com/photo-1536657464919-8925412403c1?auto=format&fit=crop&w=600&q=80',
            'Cotton': 'https://images.unsplash.com/photo-1594900222168-5d2dfba2e5ad?auto=format&fit=crop&w=600&q=80',
            'Corn': 'https://images.unsplash.com/photo-1551754655-cd27e38d2076?auto=format&fit=crop&w=600&q=80',
            'Onion': 'https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=600&q=80',
            'Garlic': 'https://images.unsplash.com/photo-1540148426945-6cf22a6b2383?auto=format&fit=crop&w=600&q=80',
            'Ginger': 'https://images.unsplash.com/photo-1599940824399-b87987ceb72a?auto=format&fit=crop&w=600&q=80',
            'Turmeric': 'https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=600&q=80',
            'Carrot': 'https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?auto=format&fit=crop&w=600&q=80',
            'Cabbage': 'https://images.unsplash.com/photo-1550147760-44c9966d6bc7?auto=format&fit=crop&w=600&q=80',
            'Cauliflower': 'https://images.unsplash.com/photo-1568584711271-6c8ca8ed24a6?auto=format&fit=crop&w=600&q=80',
            'Spinach': 'https://images.unsplash.com/photo-1576045057995-568f588f82fb?auto=format&fit=crop&w=600&q=80',
            'Banana': 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?auto=format&fit=crop&w=600&q=80',
            'Mango': 'https://images.unsplash.com/photo-1553279768-865429fa0078?auto=format&fit=crop&w=600&q=80',
            'Apple': 'https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?auto=format&fit=crop&w=600&q=80',
            'Orange': 'https://images.unsplash.com/photo-1547514701-42782101795e?auto=format&fit=crop&w=600&q=80',
            'Grapes': 'https://images.unsplash.com/photo-1537640538966-79f369143f8f?auto=format&fit=crop&w=600&q=80',
            'Strawberry': 'https://images.unsplash.com/photo-1464965911861-746a04b4bca6?auto=format&fit=crop&w=600&q=80',
            'Rosemary': 'https://images.unsplash.com/photo-1515543904379-3d757afe72e2?auto=format&fit=crop&w=600&q=80',
            'Basil': 'https://images.unsplash.com/photo-1618220179428-22790b461013?auto=format&fit=crop&w=600&q=80',
            'Mint': 'https://images.unsplash.com/photo-1608686207856-001b95cf60ca?auto=format&fit=crop&w=600&q=80',
        }
        if self.name in curated:
            return curated[self.name]
        return 'https://images.unsplash.com/photo-1464226184884-fa280b87c3a9?auto=format&fit=crop&w=600&q=80'


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
    AFFECTED_PART_CHOICES = [
        ('fruit', 'Fruit'),
        ('leaf', 'Leaf'),
        ('branch_stem', 'Branch/Stem'),
        ('root', 'Root'),
        ('other', 'Other'),
    ]
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='diseases')
    name = models.CharField(max_length=100)
    affected_part = models.CharField(max_length=20, choices=AFFECTED_PART_CHOICES, default='leaf')
    
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
