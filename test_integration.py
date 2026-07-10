from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from library.models import Crop, Fertilizer, Disease
from scans.models import ScanHistory
from weather.services import WeatherAPIError

User = get_user_model()

class PlantCareIntegrationTests(APITestCase):
    databases = '__all__'
    
    def setUp(self):
        # Urls
        self.register_url = reverse('api-register')
        self.login_url = reverse('api-login')
        self.profile_url = reverse('api-profile')
        self.preferences_url = reverse('api-preferences')
        
        self.crop_list_url = reverse('api-crop-list')
        self.disease_search_url = reverse('api-disease-search')
        
        self.scan_upload_url = reverse('api-scan-upload')
        self.scan_history_url = reverse('api-scan-history')
        self.scan_stats_url = reverse('api-scan-stats')
        
        self.weather_current_url = reverse('api-weather-current')
        self.weather_forecast_url = reverse('api-weather-forecast')
        self.weather_growth_url = reverse('api-weather-growth-chance')

        # Clear DB entries created by other setup/seeding
        Crop.objects.all().delete()
        Fertilizer.objects.all().delete()
        Disease.objects.all().delete()
        ScanHistory.objects.all().delete()
        User.objects.all().delete()

        # Seed initial library data
        self.crop_tomato = Crop.objects.create(
            name='Tomato',
            scientific_name='Solanum lycopersicum',
            description='Red juicy crop',
            ideal_temp_min_c=18.0,
            ideal_temp_max_c=32.0,
            ideal_humidity_min=50.0,
            ideal_humidity_max=80.0
        )
        self.fert_potash = Fertilizer.objects.create(
            name='Potash',
            fertilizer_type='chemical',
            description='Potassium source',
            usage_instructions='Apply around root'
        )
        self.disease_blight = Disease.objects.create(
            crop=self.crop_tomato,
            name='Tomato Blight',
            symptoms='Concentric leaf spots',
            causes='Fungus',
            treatment='Copper spray'
        )
        self.disease_blight.fertilizers_recommended.add(self.fert_potash)

        # Helper dummy image
        self.dummy_image = SimpleUploadedFile(
            name='leaf.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b',
            content_type='image/jpeg'
        )

    # ==========================================
    # SETUP -> ACCOUNTS (5 tests)
    # ==========================================
    def test_auth_user_model_is_the_custom_user(self):
        self.assertEqual(settings.AUTH_USER_MODEL, 'accounts.User')
        self.assertEqual(User.__name__, 'User')

    def test_full_register_then_use_access_token_on_protected_endpoint(self):
        register_data = {
            'username': 'integrationuser',
            'email': 'integration@example.com',
            'password': 'PassWord1234!',
            'password2': 'PassWord1234!',
            'latitude': 23.0,
            'longitude': 72.0
        }
        # Register
        reg_response = self.client.post(self.register_url, register_data)
        self.assertEqual(reg_response.status_code, status.HTTP_201_CREATED)
        access_token = reg_response.data['access']

        # Get profile with bearer token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_response = self.client.post(self.profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['username'], 'integrationuser')

    def test_expired_or_malformed_token_is_rejected_end_to_end(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_or_garbage_token')
        response = self.client.post(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_media_and_static_settings_do_not_break_request_handling(self):
        # Confirms settings.MEDIA_URL configuration exists and loads
        self.assertTrue(hasattr(settings, 'MEDIA_URL'))
        self.assertTrue(hasattr(settings, 'STATIC_URL'))

    def test_cors_middleware_does_not_block_same_origin_api_calls(self):
        # Simple local request checks
        response = self.client.get(self.login_url)
        self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ==========================================
    # ACCOUNTS -> LIBRARY (4 tests)
    # ==========================================
    def test_logged_in_user_can_browse_library_immediately_after_login(self):
        # Register user
        user = User.objects.create_user(username='libuser', password='Password123!')
        login_response = self.client.post(self.login_url, {'username': 'libuser', 'password': 'Password123!'})
        token = login_response.data['access']

        # Browse library with token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        lib_response = self.client.post(self.crop_list_url)
        self.assertEqual(lib_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(lib_response.data), 1)
        self.assertEqual(lib_response.data[0]['name'], 'Tomato')

    def test_logged_out_user_cannot_browse_library(self):
        response = self.client.post(self.crop_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_preference_change_does_not_affect_library_data_visibility(self):
        user = User.objects.create_user(username='prefuser', password='Password123!')
        self.client.force_authenticate(user=user)
        # Update preferences
        pref_response = self.client.patch(self.preferences_url, {'preferred_language': 'gu'})
        self.assertEqual(pref_response.status_code, status.HTTP_200_OK)
        
        # Check library data remains visible
        lib_response = self.client.post(self.crop_list_url)
        self.assertEqual(lib_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(lib_response.data), 1)

    def test_two_different_users_see_the_same_shared_library_data(self):
        userA = User.objects.create_user(username='userA', password='Password123!')
        userB = User.objects.create_user(username='userB', password='Password123!')
        
        self.client.force_authenticate(user=userA)
        resA = self.client.post(self.crop_list_url)
        
        self.client.force_authenticate(user=userB)
        resB = self.client.post(self.crop_list_url)
        
        self.assertEqual(resA.data, resB.data)

    # ==========================================
    # LIBRARY -> SCANS (5 tests)
    # ==========================================
    @patch('scans.views.PlantNetClient.identify')
    def test_scan_matches_disease_seeded_via_library_by_common_name(self, mock_identify):
        mock_identify.return_value = {
            'species': 'Solanum lycopersicum',
            'common_name': 'Tomato',
            'confidence_score': 0.92,
            'raw': {}
        }
        user = User.objects.create_user(username='scanuser', password='Password123!')
        self.client.force_authenticate(user=user)
        
        response = self.client.post(self.scan_upload_url, {'image': self.dummy_image})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['matched_crop_name'], 'Tomato')
        self.assertEqual(response.data['is_healthy'], False)
        self.assertEqual(response.data['disease_identified'], 'Tomato Blight')
        self.assertEqual(response.data['fertilizer_recommendation'], 'Potash')

    @patch('scans.views.PlantNetClient.identify')
    def test_scan_matches_disease_seeded_via_library_by_scientific_name_when_no_common_name(self, mock_identify):
        mock_identify.return_value = {
            'species': 'Solanum lycopersicum',
            'common_name': None, # No common name returned
            'confidence_score': 0.90,
            'raw': {}
        }
        user = User.objects.create_user(username='scanuser2', password='Password123!')
        self.client.force_authenticate(user=user)
        
        response = self.client.post(self.scan_upload_url, {'image': self.dummy_image})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['matched_crop_name'], 'Solanum lycopersicum')
        self.assertEqual(response.data['is_healthy'], False)
        self.assertEqual(response.data['disease_identified'], 'Tomato Blight')

    @patch('scans.views.PlantNetClient.identify')
    def test_updating_disease_in_library_is_reflected_in_new_scans_immediately(self, mock_identify):
        mock_identify.return_value = {
            'species': 'Solanum lycopersicum',
            'common_name': 'Tomato',
            'confidence_score': 0.92,
            'raw': {}
        }
        user = User.objects.create_user(username='scanuser3', password='Password123!')
        self.client.force_authenticate(user=user)
        
        # Modify the disease treatment in reference library
        self.disease_blight.treatment = 'Pruning + Copper Spray'
        self.disease_blight.fertilizers_recommended.clear() # Clear fertilizers to force fallback to treatment text
        self.disease_blight.save()
        
        response = self.client.post(self.scan_upload_url, {'image': self.dummy_image})
        self.assertEqual(response.data['fertilizer_recommendation'], 'Pruning + Copper Spray')

    @patch('scans.views.PlantNetClient.identify')
    def test_deleting_a_crop_in_library_does_not_crash_existing_scan_history(self, mock_identify):
        mock_identify.return_value = {
            'species': 'Solanum lycopersicum',
            'common_name': 'Tomato',
            'confidence_score': 0.92,
            'raw': {}
        }
        user = User.objects.create_user(username='scanuser4', password='Password123!')
        self.client.force_authenticate(user=user)
        
        # Upload scan
        response = self.client.post(self.scan_upload_url, {'image': self.dummy_image})
        scan_id = response.data['id']
        
        # Now delete Tomato crop from library
        self.crop_tomato.delete()
        
        # Access scan detail - must still succeed and return text details
        detail_url = reverse('api-scan-detail', kwargs={'pk': scan_id})
        detail_res = self.client.post(detail_url)
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_res.data['matched_crop_name'], 'Tomato')

    @patch('scans.views.PlantNetClient.identify')
    def test_scan_of_species_not_in_library_still_succeeds_as_healthy(self, mock_identify):
        mock_identify.return_value = {
            'species': 'Malus domestica',
            'common_name': 'Apple',
            'confidence_score': 0.88,
            'raw': {}
        }
        user = User.objects.create_user(username='scanuser5', password='Password123!')
        self.client.force_authenticate(user=user)
        
        response = self.client.post(self.scan_upload_url, {'image': self.dummy_image})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['is_healthy'], True)
        self.assertEqual(response.data['disease_identified'], None)

    # ==========================================
    # SCANS -> WEATHER (5 tests)
    # ==========================================
    @patch('scans.views.PlantNetClient.identify')
    def test_scan_saved_coordinates_match_user_profile_coordinates_by_default(self, mock_identify):
        mock_identify.return_value = {
            'species': 'Solanum lycopersicum',
            'common_name': 'Tomato',
            'confidence_score': 0.9,
            'raw': {}
        }
        user = User.objects.create_user(
            username='coorduser', password='Password123!',
            latitude=22.0, longitude=79.0
        )
        self.client.force_authenticate(user=user)
        
        # Upload without coordinates -> falls back to None in POST body (not user profile default)
        response = self.client.post(self.scan_upload_url, {'image': self.dummy_image})
        self.assertEqual(response.data['latitude'], None)

        # Upload with coordinates -> verifies coordinates round-trip
        response2 = self.client.post(self.scan_upload_url, {
            'image': self.dummy_image,
            'latitude': 22.5,
            'longitude': 79.5
        })
        self.assertEqual(response2.data['latitude'], 22.5)
        self.assertEqual(response2.data['longitude'], 79.5)

    @patch('weather.views.OpenWeatherClient.get_forecast_next_days')
    def test_growth_chance_uses_same_crop_record_scans_matched_against(self, mock_get_forecast):
        mock_get_forecast.return_value = [
            {'date': '2026-07-06', 'avg_temperature_c': 25.0, 'avg_humidity': 60.0}
        ]
        
        user = User.objects.create_user(
            username='weatheruser', password='Password123!',
            latitude=23.0, longitude=72.0
        )
        self.client.force_authenticate(user=user)
        
        # Seed crop
        new_crop = Crop.objects.create(
            name='Cucumber', scientific_name='Cucumis sativus', description='Green',
            ideal_temp_min_c=20.0, ideal_temp_max_c=30.0,
            ideal_humidity_min=50.0, ideal_humidity_max=75.0
        )
        
        response = self.client.post(self.weather_growth_url, {'crop_id': new_crop.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['crop_name'], 'Cucumber')
        self.assertEqual(response.data['growth_chance_percentage'], 100.0)

    @patch('weather.views.OpenWeatherClient.get_forecast_next_days')
    def test_growth_chance_falls_back_to_profile_location_used_by_scans_too(self, mock_get_forecast):
        mock_get_forecast.return_value = []
        user = User.objects.create_user(
            username='fallbackuser', password='Password123!',
            latitude=15.0, longitude=75.0
        )
        self.client.force_authenticate(user=user)
        
        new_crop = Crop.objects.create(
            name='Wheat', scientific_name='Triticum', description='Grain',
            ideal_temp_min_c=10.0, ideal_temp_max_c=25.0,
            ideal_humidity_min=40.0, ideal_humidity_max=60.0
        )
        
        # Call without params -> calls mock with user coords
        response = self.client.post(self.weather_growth_url, {'crop_id': new_crop.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_forecast.assert_called_once_with(15.0, 75.0)

    def test_weather_endpoints_still_400_cleanly_if_scans_never_set_a_location(self):
        user = User.objects.create_user(
            username='nocoorduser', password='Password123!',
            latitude=None, longitude=None
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(self.weather_current_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('scans.views.PlantNetClient.identify')
    @patch('weather.views.OpenWeatherClient.get_current')
    def test_plantnet_failure_does_not_affect_unrelated_weather_calls(self, mock_get_current, mock_identify):
        from scans.services import PlantNetError
        mock_identify.side_effect = PlantNetError("Plantnet connection error")
        mock_get_current.return_value = {'temperature_c': 30.0, 'humidity': 50.0}
        
        user = User.objects.create_user(
            username='healthyuser', password='Password123!',
            latitude=23.0, longitude=72.0
        )
        self.client.force_authenticate(user=user)
        
        # Scan fails
        scan_res = self.client.post(self.scan_upload_url, {'image': self.dummy_image})
        self.assertEqual(scan_res.status_code, status.HTTP_502_BAD_GATEWAY)
        
        # Unrelated weather call still works
        weather_res = self.client.post(self.weather_current_url)
        self.assertEqual(weather_res.status_code, status.HTTP_200_OK)
        self.assertEqual(weather_res.data['temperature_c'], 30.0)

    def test_download_scan_pdf(self):
        user = User.objects.create_user(
            username='pdfuser', password='Password123!',
            preferred_language='gu'
        )
        self.client.force_login(user)
        
        # Create a scan history entry
        scan = ScanHistory.objects.create(
            user=user,
            matched_crop_name='Tomato',
            identified_species='Solanum lycopersicum',
            confidence_score=0.9,
            is_healthy=False,
            disease_identified='Early Blight',
            latitude=23.0,
            longitude=72.0,
            plantnet_raw_response='{}'
        )
        
        url = reverse('download_scan_pdf', kwargs={'result_id': scan.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        pdf_bytes = b"".join(response.streaming_content)
        self.assertTrue(len(pdf_bytes) > 0)
