from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from library.models import Crop
from weather.services import WeatherAPIError

User = get_user_model()

class WeatherTests(APITestCase):
    def setUp(self):
        self.current_url = reverse('api-weather-current')
        self.forecast_url = reverse('api-weather-forecast')
        self.past_url = reverse('api-weather-past')
        self.growth_url = reverse('api-weather-growth-chance')

        # Create a user with saved location
        self.user = User.objects.create_user(
            username='weatheruser',
            password='Password123!',
            latitude=23.0225,
            longitude=72.5714 # Ahmedabad coords
        )
        
        # User with no coordinates saved
        self.user_no_loc = User.objects.create_user(
            username='nolocuser',
            password='Password123!',
            latitude=None,
            longitude=None
        )

        self.crop = Crop.objects.create(
            name='Ideal Crop',
            scientific_name='Idealius cropius',
            description='Grows in normal weather',
            ideal_temp_min_c=20.0,
            ideal_temp_max_c=30.0,
            ideal_humidity_min=50.0,
            ideal_humidity_max=75.0
        )

    def test_requires_authentication(self):
        response = self.client.post(self.current_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('weather.views.OpenWeatherClient.get_current')
    def test_uses_saved_profile_location_when_no_query_params(self, mock_get_current):
        mock_get_current.return_value = {'temperature_c': 28.0, 'humidity': 60.0}
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.current_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that mock was called with user's coordinates
        mock_get_current.assert_called_once_with(23.0225, 72.5714)

    @patch('weather.views.OpenWeatherClient.get_current')
    def test_query_params_override_profile_location(self, mock_get_current):
        mock_get_current.return_value = {'temperature_c': 32.0, 'humidity': 55.0}
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.current_url, {'lat': 12.34, 'lon': 56.78})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_current.assert_called_once_with(12.34, 56.78)

    def test_missing_location_returns_400(self):
        self.client.force_authenticate(user=self.user_no_loc)
        response = self.client.post(self.current_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('weather.views.OpenWeatherClient.get_current')
    def test_upstream_failure_returns_502(self, mock_get_current):
        mock_get_current.side_effect = WeatherAPIError("Service Unavailable")
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.current_url)
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    @patch('weather.views.OpenWeatherClient.get_forecast_next_days')
    def test_forecast_returns_daily_entries(self, mock_get_forecast):
        mock_get_forecast.return_value = [
            {'date': '2026-07-06', 'avg_temperature_c': 25.0, 'avg_humidity': 60.0}
        ]
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.forecast_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('weather.views.OpenWeatherClient.get_past_days')
    def test_past_days_respects_days_param(self, mock_get_past):
        mock_get_past.return_value = []
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.past_url, {'days': 7})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_past.assert_called_once_with(23.0225, 72.5714, 7)

    @patch('weather.views.OpenWeatherClient.get_forecast_next_days')
    def test_growth_chance_good_conditions(self, mock_get_forecast):
        # All days in crop's ideal range (temp 20-30, hum 50-75)
        mock_get_forecast.return_value = [
            {'date': '2026-07-06', 'avg_temperature_c': 25.0, 'avg_humidity': 60.0},
            {'date': '2026-07-07', 'avg_temperature_c': 26.0, 'avg_humidity': 65.0}
        ]
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.growth_url, {'crop_id': self.crop.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['growth_chance_percentage'], 100.0)
        self.assertEqual(response.data['verdict'], 'Good')

    @patch('weather.views.OpenWeatherClient.get_forecast_next_days')
    def test_growth_chance_bad_conditions(self, mock_get_forecast):
        # Temp too high, hum too low
        mock_get_forecast.return_value = [
            {'date': '2026-07-06', 'avg_temperature_c': 35.0, 'avg_humidity': 40.0}
        ]
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.growth_url, {'crop_id': self.crop.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['growth_chance_percentage'], 0.0)
        self.assertEqual(response.data['verdict'], 'Unfavorable')

    @patch('weather.views.OpenWeatherClient.get_forecast_next_days')
    def test_growth_chance_mixed_conditions(self, mock_get_forecast):
        # 3 of 5 days favorable -> 60% growth chance -> "Mixed"
        mock_get_forecast.return_value = [
            {'date': '2026-07-06', 'avg_temperature_c': 25.0, 'avg_humidity': 60.0}, # OK
            {'date': '2026-07-07', 'avg_temperature_c': 25.0, 'avg_humidity': 60.0}, # OK
            {'date': '2026-07-08', 'avg_temperature_c': 25.0, 'avg_humidity': 60.0}, # OK
            {'date': '2026-07-09', 'avg_temperature_c': 35.0, 'avg_humidity': 40.0}, # bad
            {'date': '2026-07-10', 'avg_temperature_c': 15.0, 'avg_humidity': 80.0}  # bad
        ]
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.growth_url, {'crop_id': self.crop.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['growth_chance_percentage'], 60.0)
        self.assertEqual(response.data['verdict'], 'Mixed')

    @patch('weather.views.OpenWeatherClient.get_forecast_next_days')
    def test_growth_chance_with_empty_forecast_returns_zero_not_error(self, mock_get_forecast):
        mock_get_forecast.return_value = []
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.growth_url, {'crop_id': self.crop.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['growth_chance_percentage'], 0.0)
        self.assertEqual(response.data['verdict'], 'Unfavorable')

    def test_missing_crop_id(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.growth_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_crop_returns_404(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.growth_url, {'crop_id': 9999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('weather.views.OpenWeatherClient.geocode_city')
    @patch('weather.views.OpenWeatherClient.get_current')
    def test_uses_location_city_geocode_fallback_first(self, mock_get_current, mock_geocode_city):
        mock_geocode_city.return_value = (19.0760, 72.8777) # Mumbai coords
        mock_get_current.return_value = {'temperature_c': 30.0, 'humidity': 75.0}
        
        user_with_city = User.objects.create_user(
            username='cityuser',
            password='Password123!',
            location_city='Mumbai',
            latitude=23.0225,
            longitude=72.5714
        )
        
        self.client.force_authenticate(user=user_with_city)
        response = self.client.post(self.current_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_geocode_city.assert_called_once_with('Mumbai')
        mock_get_current.assert_called_once_with(19.0760, 72.8777)
