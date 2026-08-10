from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from library.models import Crop
from .services import OpenWeatherClient, calculate_growth_chance, WeatherAPIError

def _resolve_coordinates(request):
    lat_param = request.data.get('lat', request.query_params.get('lat'))
    lon_param = request.data.get('lon', request.query_params.get('lon'))
    
    if lat_param is not None and lon_param is not None and lat_param != '' and lon_param != '':
        try:
            return float(lat_param), float(lon_param)
        except ValueError:
            return None, None
            
    # Fallback to logged-in user's profile location
    if request.user.is_authenticated:
        # 1. Resolve via user location_city
        if request.user.location_city:
            resolved_lat, resolved_lon = OpenWeatherClient.geocode_city(request.user.location_city)
            if resolved_lat is not None and resolved_lon is not None:
                return resolved_lat, resolved_lon
        
        # 2. Resolve via user saved coordinates
        if request.user.latitude is not None and request.user.longitude is not None:
            return request.user.latitude, request.user.longitude
            
    return None, None


class CurrentWeatherView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        lat, lon = _resolve_coordinates(request)
        if lat is None or lon is None:
            return Response({"error": "Latitude and longitude are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            data = OpenWeatherClient.get_current(lat, lon)
            return Response(data, status=status.HTTP_200_OK)
        except WeatherAPIError as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

    def post(self, request, *args, **kwargs):
        lat, lon = _resolve_coordinates(request)
        if lat is None or lon is None:
            return Response({"error": "Latitude and longitude are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            data = OpenWeatherClient.get_current(lat, lon)
            return Response(data, status=status.HTTP_200_OK)
        except WeatherAPIError as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class ForecastWeatherView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        lat, lon = _resolve_coordinates(request)
        if lat is None or lon is None:
            return Response({"error": "Latitude and longitude are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            data = OpenWeatherClient.get_forecast_next_days(lat, lon)
            return Response(data, status=status.HTTP_200_OK)
        except WeatherAPIError as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class HistoricalWeatherView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        lat, lon = _resolve_coordinates(request)
        if lat is None or lon is None:
            return Response({"error": "Latitude and longitude are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        days = request.data.get('days', request.query_params.get('days'))
        if not days:
            return Response({"error": "Query param 'days' is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            days_int = int(days)
            if days_int <= 0:
                raise ValueError()
        except ValueError:
            return Response({"error": "Invalid value for 'days'. Must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = OpenWeatherClient.get_past_days(lat, lon, days_int)
            return Response(data, status=status.HTTP_200_OK)
        except WeatherAPIError as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class GrowthChanceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        crop_id = request.data.get('crop_id', request.query_params.get('crop_id'))
        if not crop_id:
            return Response({"error": "Query param 'crop_id' is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 404 if crop doesn't exist
        crop = get_object_or_404(Crop, pk=crop_id)
        
        lat, lon = _resolve_coordinates(request)
        if lat is None or lon is None:
            return Response({"error": "Latitude and longitude are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            forecast_days = OpenWeatherClient.get_forecast_next_days(lat, lon)
            pct, verdict = calculate_growth_chance(crop, forecast_days)
            return Response({
                'crop_id': crop.id,
                'crop_name': crop.name,
                'growth_chance_percentage': pct,
                'verdict': verdict,
                'forecast_days': forecast_days
            }, status=status.HTTP_200_OK)
        except WeatherAPIError as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

from django.http import JsonResponse

class GeocodeCityView(APIView):
    permission_classes = []  # Allow public geocoding for signup/registration pages

    def get(self, request, *args, **kwargs):
        city = request.query_params.get('city', '').strip()
        if not city:
            return JsonResponse({"error": "City parameter is required"}, status=400)
        
        try:
            lat, lon = OpenWeatherClient.geocode_city(city)
            if lat is not None and lon is not None:
                return JsonResponse({"lat": lat, "lon": lon}, status=200)
            return JsonResponse({"error": "City name does not match; please enter a valid city name."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

class ReverseGeocodeView(APIView):
    permission_classes = []  # Allow public geocoding for signup pages

    def get(self, request, *args, **kwargs):
        """
        Public endpoint that reverse-geocodes GPS coordinates (lat, lon) into
        village, taluka, city and state names using Nominatim + OpenWeather fallback.
        """
        lat = request.query_params.get('lat', '').strip()
        lon = request.query_params.get('lon', '').strip()
        lang = request.query_params.get('lang', 'en').strip()
        if not lat or not lon:
            return JsonResponse({"error": "Latitude and longitude parameters are required"}, status=400)
        
        try:
            result = OpenWeatherClient.reverse_geocode(float(lat), float(lon))
            # result is a dict: {village, taluka, city, state}
            if result.get('city') or result.get('village') or result.get('state'):
                if lang and lang != 'en':
                    from accounts.views import translate_list
                    keys = ['village', 'taluka', 'city', 'state']
                    vals = [result.get(k, '') for k in keys]
                    translated_vals = translate_list(vals, lang)
                    for k, val in zip(keys, translated_vals):
                        result[k] = val
                return JsonResponse(result, status=200)
            return JsonResponse({"error": "No location found for the given coordinates."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

