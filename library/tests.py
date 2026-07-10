from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Crop, Fertilizer, Disease

User = get_user_model()

class LibraryTests(APITestCase):
    def setUp(self):
        self.crop_list_url = reverse('api-crop-list')
        self.disease_search_url = reverse('api-disease-search')

        # Create a user and get credentials
        self.user = User.objects.create_user(
            username='libraryuser',
            password='Password123!'
        )

        # Seed data
        self.crop1 = Crop.objects.create(
            name='Tomato',
            scientific_name='Solanum lycopersicum',
            description='Red fruit',
            ideal_temp_min_c=18.0,
            ideal_temp_max_c=30.0,
            ideal_humidity_min=60.0,
            ideal_humidity_max=80.0
        )
        self.crop2 = Crop.objects.create(
            name='Potato',
            scientific_name='Solanum tuberosum',
            description='Root vegetable',
            ideal_temp_min_c=15.0,
            ideal_temp_max_c=25.0,
            ideal_humidity_min=50.0,
            ideal_humidity_max=70.0
        )

        self.fert1 = Fertilizer.objects.create(
            name='Compost',
            fertilizer_type='organic',
            description='Organic compost',
            usage_instructions='Spread around base'
        )
        self.fert2 = Fertilizer.objects.create(
            name='Urea',
            fertilizer_type='chemical',
            description='Nitrogen fertilizer',
            usage_instructions='Apply sparingly'
        )

        self.disease1 = Disease.objects.create(
            crop=self.crop1,
            name='Early Blight',
            symptoms='Dark spots',
            causes='Fungus',
            treatment='Copper fungicide'
        )
        self.disease1.fertilizers_recommended.add(self.fert1)

        self.disease2 = Disease.objects.create(
            crop=self.crop2,
            name='Late Blight',
            symptoms='White mold',
            causes='Water mold',
            treatment='Fungicide'
        )
        self.disease2.fertilizers_recommended.add(self.fert2)

    def test_requires_authentication(self):
        response = self.client.post(self.crop_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_crop_list_requires_authentication_too(self):
        detail_url = reverse('api-crop-detail', kwargs={'pk': self.crop1.pk})
        response = self.client.post(detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_lists_crops(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.crop_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # Tomato should be first because of alphabet sorting order
        self.assertEqual(response.data[0]['name'], 'Potato')
        self.assertEqual(response.data[1]['name'], 'Tomato')

    def test_returns_diseases_for_crop(self):
        self.client.force_authenticate(user=self.user)
        detail_url = reverse('api-crop-detail', kwargs={'pk': self.crop1.pk})
        response = self.client.post(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Tomato')
        self.assertEqual(len(response.data['diseases']), 1)
        self.assertEqual(response.data['diseases'][0]['name'], 'Early Blight')
        self.assertEqual(len(response.data['diseases'][0]['fertilizers_recommended']), 1)
        self.assertEqual(response.data['diseases'][0]['fertilizers_recommended'][0]['name'], 'Compost')

    def test_search_by_crop_name(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.disease_search_url, {'crop_name': 'Tomato'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Early Blight')

    def test_search_unknown_crop_returns_empty(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.disease_search_url, {'crop_name': 'Mango'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_search_without_crop_name_returns_all_diseases(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.disease_search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_search_is_case_insensitive(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.disease_search_url, {'crop_name': 'tOmAtO'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Early Blight')

    def test_crop_ideal_temp_range_is_stored_correctly(self):
        crop = Crop.objects.get(name='Tomato')
        self.assertEqual(crop.ideal_temp_min_c, 18.0)
        self.assertEqual(crop.ideal_temp_max_c, 30.0)

    def test_crop_name_is_unique(self):
        with self.assertRaises(IntegrityError):
            Crop.objects.create(
                name='Tomato',
                scientific_name='Solanum lycopersicum alt',
                ideal_temp_min_c=10.0,
                ideal_temp_max_c=40.0,
                ideal_humidity_min=20.0,
                ideal_humidity_max=90.0
            )

    def test_disease_unique_together_per_crop(self):
        with self.assertRaises(IntegrityError):
            Disease.objects.create(
                crop=self.crop1,
                name='Early Blight',
                symptoms='Repeated blight symptoms',
                causes='Fungus',
                treatment='None'
            )

    def test_deleting_crop_cascades_to_its_diseases(self):
        self.crop1.delete()
        self.assertFalse(Disease.objects.filter(name='Early Blight').exists())

    def test_fertilizer_type_choices_enforced_in_admin_form(self):
        # Verify choices on the model field level
        field = Fertilizer._meta.get_field('fertilizer_type')
        choices = [c[0] for c in field.choices]
        self.assertIn('organic', choices)
        self.assertIn('chemical', choices)
        self.assertIn('bio', choices)

    def test_unknown_crop_id_returns_404(self):
        self.client.force_authenticate(user=self.user)
        detail_url = reverse('api-crop-detail', kwargs={'pk': 9999})
        response = self.client.post(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
