from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from library.models import Crop, Fertilizer, Disease
from .models import ScanHistory
from .services import PlantNetError

User = get_user_model()

class ScansTests(APITestCase):
    
    def setUp(self):
        self.upload_url = reverse('api-scan-upload')
        self.history_url = reverse('api-scan-history')
        self.stats_url = reverse('api-scan-stats')

        self.user1 = User.objects.create_user(username='user1', password='Password123!')
        self.user2 = User.objects.create_user(username='user2', password='Password123!')

        # Seed Reference Library
        self.crop = Crop.objects.create(
            name='Tomato',
            scientific_name='Solanum lycopersicum',
            description='Seeded crop',
            ideal_temp_min_c=15.0,
            ideal_temp_max_c=35.0,
            ideal_humidity_min=50.0,
            ideal_humidity_max=85.0
        )
        self.fert = Fertilizer.objects.create(
            name='SuperPhosphate',
            fertilizer_type='chemical',
            description='Good for root development',
            usage_instructions='Apply during planting'
        )
        self.disease = Disease.objects.create(
            crop=self.crop,
            name='Tomato Leaf Mold',
            symptoms='Yellow spots on leaves',
            causes='Fungus',
            treatment='Reduce humidity'
        )
        self.disease.fertilizers_recommended.add(self.fert)

        # Helper image file
        self.dummy_image = SimpleUploadedFile(
            name='test_leaf.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b',
            content_type='image/jpeg'
        )

    def test_upload_requires_authentication(self):
        response = self.client.post(self.upload_url, {'image': self.dummy_image})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('scans.views.PlantNetClient.identify')
    def test_upload_matches_known_disease(self, mock_identify):
        mock_identify.return_value = {
            'species': 'Solanum lycopersicum',
            'common_name': 'Tomato',
            'confidence_score': 0.95,
            'raw': {'results': [{'score': 0.95}]}
        }
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.upload_url, {
            'image': self.dummy_image,
            'organ': 'leaf',
            'latitude': 10.0,
            'longitude': 20.0
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['matched_crop_name'], 'Tomato')
        self.assertEqual(response.data['is_healthy'], False)
        self.assertEqual(response.data['disease_identified'], 'Tomato Leaf Mold')
        self.assertEqual(response.data['fertilizer_recommendation'], 'SuperPhosphate')
        self.assertEqual(response.data['latitude'], 10.0)
        self.assertEqual(response.data['longitude'], 20.0)

    @patch('scans.views.PlantNetClient.identify')
    def test_upload_with_unknown_species_marked_healthy(self, mock_identify):
        mock_identify.return_value = {
            'species': 'Rosa rubiginosa',
            'common_name': 'Sweetbriar Rose',
            'confidence_score': 0.85,
            'raw': {'results': []}
        }
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.upload_url, {
            'image': self.dummy_image,
            'organ': 'flower'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['is_healthy'], True)
        self.assertEqual(response.data['disease_identified'], None)
        self.assertEqual(response.data['fertilizer_recommendation'], None)

    @patch('scans.views.PlantNetClient.identify')
    def test_organ_defaults_to_leaf_when_omitted(self, mock_identify):
        mock_identify.return_value = {
            'species': 'Solanum lycopersicum',
            'common_name': 'Tomato',
            'confidence_score': 0.9,
            'raw': {}
        }
        self.client.force_authenticate(user=self.user1)
        # Omit 'organ' field
        response = self.client.post(self.upload_url, {'image': self.dummy_image})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['organ'], 'leaf')

    def test_invalid_organ_choice_rejected(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.upload_url, {
            'image': self.dummy_image,
            'organ': 'roots' # Invalid choice
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('scans.views.PlantNetClient.identify')
    def test_plantnet_failure_returns_502_but_keeps_no_partial_state(self, mock_identify):
        mock_identify.side_effect = PlantNetError("Server timeout")
        self.client.force_authenticate(user=self.user1)
        initial_count = ScanHistory.objects.count()
        response = self.client.post(self.upload_url, {'image': self.dummy_image})
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(ScanHistory.objects.count(), initial_count)

    def test_history_only_shows_own_scans(self):
        # Create scans for user1 and user2
        ScanHistory.objects.create(
            user=self.user1, image='scans/1.jpg', organ='leaf',
            identified_species='Sp1', confidence_score=0.9, plantnet_raw_response={},
            is_healthy=True
        )
        ScanHistory.objects.create(
            user=self.user2, image='scans/2.jpg', organ='leaf',
            identified_species='Sp2', confidence_score=0.8, plantnet_raw_response={},
            is_healthy=True
        )
        # Auth user1
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.history_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['identified_species'], 'Sp1')

    def test_history_ordered_newest_first(self):
        from django.utils import timezone
        scan1 = ScanHistory.objects.create(
            user=self.user1, image='scans/1.jpg', organ='leaf',
            identified_species='Sp1', confidence_score=0.9, plantnet_raw_response={},
            is_healthy=True
        )
        scan2 = ScanHistory.objects.create(
            user=self.user1, image='scans/2.jpg', organ='leaf',
            identified_species='Sp2', confidence_score=0.8, plantnet_raw_response={},
            is_healthy=True
        )
        # Modify created_at manually to guarantee ordering
        scan1.created_at = timezone.now() - timezone.timedelta(days=1)
        scan1.save()
        
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.history_url)
        self.assertEqual(response.data['results'][0]['identified_species'], 'Sp2')
        self.assertEqual(response.data['results'][1]['identified_species'], 'Sp1')

    def test_detail_view_of_other_users_scan_returns_404(self):
        scan2 = ScanHistory.objects.create(
            user=self.user2, image='scans/2.jpg', organ='leaf',
            identified_species='Sp2', confidence_score=0.8, plantnet_raw_response={},
            is_healthy=True
        )
        self.client.force_authenticate(user=self.user1)
        detail_url = reverse('api-scan-detail', kwargs={'pk': scan2.pk})
        response = self.client.post(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_stats_with_zero_scans_returns_zero_not_error(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 0)
        self.assertEqual(response.data['healthy_count'], 0)
        self.assertEqual(response.data['diseased_count'], 0)
        self.assertEqual(response.data['scans_by_crop'], {})
        self.assertEqual(response.data['scans_by_month'], {})

    def test_stats_totals_are_correct(self):
        # 2 healthy, 1 diseased
        ScanHistory.objects.create(
            user=self.user1, image='scans/1.jpg', organ='leaf',
            identified_species='Tomato Species', matched_crop_name='Tomato',
            confidence_score=0.9, plantnet_raw_response={}, is_healthy=True
        )
        ScanHistory.objects.create(
            user=self.user1, image='scans/2.jpg', organ='leaf',
            identified_species='Tomato Species', matched_crop_name='Tomato',
            confidence_score=0.9, plantnet_raw_response={}, is_healthy=True
        )
        ScanHistory.objects.create(
            user=self.user1, image='scans/3.jpg', organ='leaf',
            identified_species='Potato Species', matched_crop_name='Potato',
            confidence_score=0.9, plantnet_raw_response={}, is_healthy=False
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 3)
        self.assertEqual(response.data['healthy_count'], 2)
        self.assertEqual(response.data['diseased_count'], 1)
        self.assertEqual(response.data['scans_by_crop']['Tomato'], 2)
        self.assertEqual(response.data['scans_by_crop']['Potato'], 1)

    # ==========================================
    # NEW DIAGNOSTIC & PESTICIDES TESTS (15)
    # ==========================================
    def test_check_image_health_keyword_healthy(self):
        from plantcare.utils import check_image_health
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("cotton_healty_leaf.jpg", b"fake_data")
        self.assertTrue(check_image_health(f))

    def test_check_image_health_keyword_disease(self):
        from plantcare.utils import check_image_health
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("cotton_disease_leaf.jpg", b"fake_data")
        self.assertFalse(check_image_health(f))

    def test_check_image_health_keyword_spot(self):
        from plantcare.utils import check_image_health
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("banana_leaf_spot.jpg", b"fake_data")
        self.assertFalse(check_image_health(f))

    def test_check_image_health_color_mostly_green(self):
        from plantcare.utils import check_image_health
        from PIL import Image
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        img = Image.new('RGB', (100, 100), color=(80, 150, 50))
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        img_file = SimpleUploadedFile("leaf.jpg", img_io.getvalue(), content_type="image/jpeg")
        self.assertTrue(check_image_health(img_file))

    def test_check_image_health_color_mostly_brown(self):
        from plantcare.utils import check_image_health
        from PIL import Image
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        img = Image.new('RGB', (100, 100), color=(140, 90, 40))
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        img_file = SimpleUploadedFile("leaf.jpg", img_io.getvalue(), content_type="image/jpeg")
        self.assertFalse(check_image_health(img_file))

    def test_get_structured_pesticides_case1_en(self):
        from plantcare.utils import get_structured_pesticides
        res = get_structured_pesticides("Apply Chlorothalonil or Mancozeb fungicide spray once every 10-14 days.", "en")
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]['name'], 'Neem Oil Spray (1%)')

    def test_get_structured_pesticides_case1_hi(self):
        from plantcare.utils import get_structured_pesticides
        res = get_structured_pesticides("Apply Chlorothalonil or Mancozeb fungicide spray once every 10-14 days.", "hi")
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]['name'], 'नीम का तेल स्प्रे (1%)')

    def test_get_structured_pesticides_case1_gu(self):
        from plantcare.utils import get_structured_pesticides
        res = get_structured_pesticides("Apply Chlorothalonil or Mancozeb fungicide spray once every 10-14 days.", "gu")
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]['name'], 'લીમડાનું તેલ સ્પ્રે (1%)')

    def test_get_structured_pesticides_case2_en(self):
        from plantcare.utils import get_structured_pesticides
        res = get_structured_pesticides("Apply Chlorothalonil, Mancozeb, or copper-based fungicides once every 7-10 days.", "en")
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]['name'], 'Neem & Garlic Foliar Spray')

    def test_get_structured_pesticides_case3_en(self):
        from plantcare.utils import get_structured_pesticides
        res = get_structured_pesticides("Spray sulfur-based fungicides or systemic Metalaxyl sprays.", "en")
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]['name'], 'Baking Soda & Neem Spray')

    def test_get_structured_pesticides_case4_en(self):
        from plantcare.utils import get_structured_pesticides
        res = get_structured_pesticides("Use systemic fungicides containing Metalaxyl, Chlorothalonil, or Fluopicolide.", "en")
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]['name'], 'Organic Compost Tea Spray')

    def test_get_structured_pesticides_empty(self):
        from plantcare.utils import get_structured_pesticides
        res = get_structured_pesticides("", "en")
        self.assertEqual(res, [])

    @patch('scans.views.PlantNetClient.identify')
    def test_integration_upload_healthy_classified_healthy(self, mock_identify):
        mock_identify.return_value = {
            'species': 'Solanum lycopersicum',
            'common_name': 'Tomato',
            'confidence_score': 0.95,
            'raw': {'results': [{'images': [{'organ': 'leaf'}]}]}
        }
        # In-memory green leaf image
        from PIL import Image
        import io
        img = Image.new('RGB', (100, 100), color=(80, 150, 50))
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        healthy_file = SimpleUploadedFile("tomato_healthy_leaf.jpg", img_io.getvalue(), content_type="image/jpeg")

        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.upload_url, {
            'image': healthy_file,
            'organ': 'leaf'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_healthy'])
        self.assertIsNone(response.data['disease_identified'])

    @patch('scans.views.PlantNetClient.identify')
    def test_integration_upload_diseased_classified_diseased(self, mock_identify):
        mock_identify.return_value = {
            'species': 'Solanum lycopersicum',
            'common_name': 'Tomato',
            'confidence_score': 0.95,
            'raw': {'results': [{'images': [{'organ': 'leaf'}]}]}
        }
        # In-memory brown leaf image
        from PIL import Image
        import io
        img = Image.new('RGB', (100, 100), color=(140, 90, 40))
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        diseased_file = SimpleUploadedFile("tomato_diseased_leaf.jpg", img_io.getvalue(), content_type="image/jpeg")

        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.upload_url, {
            'image': diseased_file,
            'organ': 'leaf'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['is_healthy'])
        self.assertEqual(response.data['disease_identified'], 'Tomato Leaf Mold')

    def test_pdf_download_endpoint_success(self):
        scan = ScanHistory.objects.create(
            user=self.user1, image='scans/1.jpg', organ='leaf',
            identified_species='Tomato Species', matched_crop_name='Tomato',
            confidence_score=0.9, plantnet_raw_response={}, is_healthy=False,
            disease_identified='Tomato Leaf Mold'
        )
        self.client.force_login(self.user1)
        pdf_url = reverse('download_scan_pdf', kwargs={'result_id': scan.id})
        response = self.client.post(pdf_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

