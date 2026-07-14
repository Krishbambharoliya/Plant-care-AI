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
        name_lower = self.name.lower().strip()
        curated = {
            'potato': 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=600&q=80',
            'tomato': 'https://images.unsplash.com/photo-1592417817098-8f3d6eb19675?auto=format&fit=crop&w=600&q=80',
            'chili pepper': 'https://images.unsplash.com/photo-1588252393666-515c11f7c00e?auto=format&fit=crop&w=600&q=80',
            'chilli': 'https://images.unsplash.com/photo-1588252393666-515c11f7c00e?auto=format&fit=crop&w=600&q=80',
            'maize': 'https://images.unsplash.com/photo-1551754655-cd27e38d2076?auto=format&fit=crop&w=600&q=80',
            'corn': 'https://images.unsplash.com/photo-1551754655-cd27e38d2076?auto=format&fit=crop&w=600&q=80',
            'rice': 'https://images.unsplash.com/photo-1536657464919-8925412403c1?auto=format&fit=crop&w=600&q=80',
            'wheat': 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=600&q=80',
            'cotton': 'https://images.unsplash.com/photo-1594900222168-5d2dfba2e5ad?auto=format&fit=crop&w=600&q=80',
            'sugarcane': 'https://images.unsplash.com/photo-1593113630400-ea4288922497?auto=format&fit=crop&w=600&q=80',
            'soybean': 'https://images.unsplash.com/photo-1599599810769-bcde5a160d32?auto=format&fit=crop&w=600&q=80',
            'soybeans': 'https://images.unsplash.com/photo-1599599810769-bcde5a160d32?auto=format&fit=crop&w=600&q=80',
            'groundnut': 'https://images.unsplash.com/photo-1567894340315-735d7c361db0?auto=format&fit=crop&w=600&q=80',
            'onion': 'https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=600&q=80',
            'garlic': 'https://images.unsplash.com/photo-1540148426945-6cf22a6b2383?auto=format&fit=crop&w=600&q=80',
            'ginger': 'https://images.unsplash.com/photo-1599940824399-b87987ceb72a?auto=format&fit=crop&w=600&q=80',
            'turmeric': 'https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=600&q=80',
            'cabbage': 'https://images.unsplash.com/photo-1550147760-44c9966d6bc7?auto=format&fit=crop&w=600&q=80',
            'cauliflower': 'https://images.unsplash.com/photo-1568584711271-6c8ca8ed24a6?auto=format&fit=crop&w=600&q=80',
            'spinach': 'https://images.unsplash.com/photo-1576045057995-568f588f82fb?auto=format&fit=crop&w=600&q=80',
            'carrot': 'https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?auto=format&fit=crop&w=600&q=80',
            'radish': 'https://images.unsplash.com/photo-1590779033100-9f60a05a013d?auto=format&fit=crop&w=600&q=80',
            'eggplant': 'https://images.unsplash.com/photo-1590301157890-4810ed352733?auto=format&fit=crop&w=600&q=80',
            'okra': 'https://images.unsplash.com/photo-1625938146369-adc83368bda7?auto=format&fit=crop&w=600&q=80',
            'cucumber': 'https://images.unsplash.com/photo-1449339854873-750e6dfc3140?auto=format&fit=crop&w=600&q=80',
            'watermelon': 'https://images.unsplash.com/photo-1587049352846-4a222e784d38?auto=format&fit=crop&w=600&q=80',
            'barley': 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=600&q=80',
            'millet': 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=600&q=80',
            'sorghum': 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=600&q=80',
            'chickpea': 'https://images.unsplash.com/photo-1547058881-aa0edd92aab3?auto=format&fit=crop&w=600&q=80',
            'pigeon pea': 'https://images.unsplash.com/photo-1547058881-aa0edd92aab3?auto=format&fit=crop&w=600&q=80',
            'black gram': 'https://images.unsplash.com/photo-1547058881-aa0edd92aab3?auto=format&fit=crop&w=600&q=80',
            'green gram': 'https://images.unsplash.com/photo-1547058881-aa0edd92aab3?auto=format&fit=crop&w=600&q=80',
            'lentil': 'https://images.unsplash.com/photo-1547058881-aa0edd92aab3?auto=format&fit=crop&w=600&q=80',
            'mustard': 'https://images.unsplash.com/photo-1508747705131-7e04b4a1236a?auto=format&fit=crop&w=600&q=80',
            'sesame': 'https://images.unsplash.com/photo-1567894340315-735d7c361db0?auto=format&fit=crop&w=600&q=80',
            'sunflower': 'https://images.unsplash.com/photo-1597848212624-a19eb35e2651?auto=format&fit=crop&w=600&q=80',
            'coconut': 'https://images.unsplash.com/photo-1584905066893-7d5c14eaafcf?auto=format&fit=crop&w=600&q=80',
            'coffee': 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=600&q=80',
            'tea': 'https://images.unsplash.com/photo-1554995207-c18c203602cb?auto=format&fit=crop&w=600&q=80',
            'cardamom': 'https://images.unsplash.com/photo-1515543904379-3d757afe72e2?auto=format&fit=crop&w=600&q=80',
            'black pepper': 'https://images.unsplash.com/photo-1540148426945-6cf22a6b2383?auto=format&fit=crop&w=600&q=80',
            'coriander': 'https://images.unsplash.com/photo-1618220179428-22790b461013?auto=format&fit=crop&w=600&q=80',
            'cumin': 'https://images.unsplash.com/photo-1618220179428-22790b461013?auto=format&fit=crop&w=600&q=80',
            'fennel': 'https://images.unsplash.com/photo-1618220179428-22790b461013?auto=format&fit=crop&w=600&q=80',
            'apple': 'https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?auto=format&fit=crop&w=600&q=80',
            'pear': 'https://images.unsplash.com/photo-1514756331096-242fdeb70d4a?auto=format&fit=crop&w=600&q=80',
            'peach': 'https://images.unsplash.com/photo-1595124250248-1112d7c4309b?auto=format&fit=crop&w=600&q=80',
            'plum': 'https://images.unsplash.com/photo-1603059080553-73cbd98ff6b8?auto=format&fit=crop&w=600&q=80',
            'mango': 'https://images.unsplash.com/photo-1553279768-865429fa0078?auto=format&fit=crop&w=600&q=80',
            'banana': 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?auto=format&fit=crop&w=600&q=80',
            'citrus': 'https://images.unsplash.com/photo-1547514701-42782101795e?auto=format&fit=crop&w=600&q=80',
            'grapes': 'https://images.unsplash.com/photo-1537640538966-79f369143f8f?auto=format&fit=crop&w=600&q=80',
            'guava': 'https://images.unsplash.com/photo-1595124250248-1112d7c4309b?auto=format&fit=crop&w=600&q=80',
            'papaya': 'https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=600&q=80',
            'pomegranate': 'https://images.unsplash.com/photo-1601004890684-d8cbf643f5f2?auto=format&fit=crop&w=600&q=80',
            'pineapple': 'https://images.unsplash.com/photo-1550258224-2ae249575a39?auto=format&fit=crop&w=600&q=80',
            'sapota': 'https://images.unsplash.com/photo-1595124250248-1112d7c4309b?auto=format&fit=crop&w=600&q=80',
            'strawberry': 'https://images.unsplash.com/photo-1464965911861-746a04b4bca6?auto=format&fit=crop&w=600&q=80',
            'sweet potato': 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=600&q=80',
            'lettuce': 'https://images.unsplash.com/photo-1550147760-44c9966d6bc7?auto=format&fit=crop&w=600&q=80',
            'broccoli': 'https://images.unsplash.com/photo-1568584711271-6c8ca8ed24a6?auto=format&fit=crop&w=600&q=80',
            'peas': 'https://images.unsplash.com/photo-1576045057995-568f588f82fb?auto=format&fit=crop&w=600&q=80',
            'pumpkin': 'https://images.unsplash.com/photo-1570586437263-ab629fccc818?auto=format&fit=crop&w=600&q=80',
            'bottle gourd': 'https://images.unsplash.com/photo-1449339854873-750e6dfc3140?auto=format&fit=crop&w=600&q=80',
            'bitter gourd': 'https://images.unsplash.com/photo-1567894340315-735d7c361db0?auto=format&fit=crop&w=600&q=80',
            'ridge gourd': 'https://images.unsplash.com/photo-1567894340315-735d7c361db0?auto=format&fit=crop&w=600&q=80',
            'sponge gourd': 'https://images.unsplash.com/photo-1567894340315-735d7c361db0?auto=format&fit=crop&w=600&q=80',
            'ash gourd': 'https://images.unsplash.com/photo-1570586437263-ab629fccc818?auto=format&fit=crop&w=600&q=80',
            'snake gourd': 'https://images.unsplash.com/photo-1567894340315-735d7c361db0?auto=format&fit=crop&w=600&q=80',
            'mint': 'https://images.unsplash.com/photo-1608686207856-001b95cf60ca?auto=format&fit=crop&w=600&q=80',
            'basil': 'https://images.unsplash.com/photo-1618220179428-22790b461013?auto=format&fit=crop&w=600&q=80',
            'rosemary': 'https://images.unsplash.com/photo-1515543904379-3d757afe72e2?auto=format&fit=crop&w=600&q=80',
        }
        if name_lower in curated:
            return curated[name_lower]
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
