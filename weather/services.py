import os
import requests
from datetime import datetime, timedelta
from django.conf import settings

class WeatherAPIError(Exception):
    pass

class OpenWeatherClient:
    @staticmethod
    def get_current(lat, lon):
        api_key = getattr(settings, 'OPENWEATHER_API_KEY', None)
        if not api_key:
            raise WeatherAPIError("OpenWeather API key not configured.")
        
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'units': 'metric',
            'appid': api_key
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                raise WeatherAPIError(f"OpenWeather current failed with status {response.status_code}: {response.text}")
            
            data = response.json()
            main = data.get('main', {})
            weather_list = data.get('weather', [{}])
            wind = data.get('wind', {})
            
            return {
                'temperature_c': main.get('temp'),
                'humidity': main.get('humidity'),
                'wind_speed_m_s': wind.get('speed'),
                'description': weather_list[0].get('description') if weather_list else 'unknown',
                'raw': data
            }
        except requests.RequestException as e:
            raise WeatherAPIError(f"OpenWeather connection failed: {str(e)}")

    @staticmethod
    def get_forecast_next_days(lat, lon):
        api_key = getattr(settings, 'OPENWEATHER_API_KEY', None)
        if not api_key:
            raise WeatherAPIError("OpenWeather API key not configured.")
        
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'units': 'metric',
            'appid': api_key
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                raise WeatherAPIError(f"OpenWeather forecast failed with status {response.status_code}: {response.text}")
            
            data = response.json()
            entries = data.get('list', [])
            
            # Group entries by calendar date
            by_date = {}
            for entry in entries:
                dt_txt = entry.get('dt_txt', '')
                if not dt_txt:
                    continue
                date_str = dt_txt.split(' ')[0]
                
                main = entry.get('main', {})
                temp = main.get('temp')
                humidity = main.get('humidity')
                
                if temp is not None and humidity is not None:
                    if date_str not in by_date:
                        by_date[date_str] = {'temps': [], 'humidities': []}
                    by_date[date_str]['temps'].append(temp)
                    by_date[date_str]['humidities'].append(humidity)
            
            # Average temp and humidity for each date
            forecast = []
            for date_str, lists in sorted(by_date.items()):
                avg_temp = sum(lists['temps']) / len(lists['temps']) if lists['temps'] else 0.0
                avg_hum = sum(lists['humidities']) / len(lists['humidities']) if lists['humidities'] else 0.0
                forecast.append({
                    'date': date_str,
                    'avg_temperature_c': round(avg_temp, 2),
                    'avg_humidity': round(avg_hum, 2)
                })
            
            return forecast
        except requests.RequestException as e:
            raise WeatherAPIError(f"OpenWeather connection failed: {str(e)}")

    @staticmethod
    def geocode_city(city_name):
        api_key = getattr(settings, 'OPENWEATHER_API_KEY', None)
        if not api_key or not city_name:
            return None, None
        
        url = "https://api.openweathermap.org/geo/1.0/direct"
        params = {
            'q': city_name,
            'limit': 1,
            'appid': api_key
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data:
                    return float(data[0]['lat']), float(data[0]['lon'])
        except Exception:
            pass
        return None, None

    @staticmethod
    def get_rain_prediction(lat, lon):
        api_key = getattr(settings, 'OPENWEATHER_API_KEY', None)
        if not api_key:
            return False, 0
        
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'units': 'metric',
            'appid': api_key
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                entries = data.get('list', [])
                
                # Check for rain in forecast conditions
                rain_entries = [entry for entry in entries if 'rain' in [w.get('main', '').lower() for w in entry.get('weather', [])]]
                rain_predicted = len(rain_entries) > 0
                
                # Get max pop (chance of rain)
                pops = [entry.get('pop', 0) for entry in entries]
                rain_chance = int(max(pops) * 100) if pops else (100 if rain_predicted else 0)
                
                return rain_predicted, rain_chance
        except Exception:
            pass
        return False, 0

    @staticmethod
    def get_past_days(lat, lon, days):
        # Open-Meteo archive API for historical data
        today = datetime.utcnow().date()
        start_date = (today - timedelta(days=int(days))).strftime('%Y-%m-%d')
        end_date = (today - timedelta(days=1)).strftime('%Y-%m-%d')
        
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            'latitude': lat,
            'longitude': lon,
            'start_date': start_date,
            'end_date': end_date,
            'daily': 'temperature_2m_mean,relative_humidity_2m_mean',
            'timezone': 'UTC'
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                raise WeatherAPIError(f"Open-Meteo failed with status {response.status_code}: {response.text}")
            
            data = response.json()
            daily = data.get('daily', {})
            times = daily.get('time', [])
            temps = daily.get('temperature_2m_mean', [])
            humidities = daily.get('relative_humidity_2m_mean', [])
            
            history = []
            for i in range(len(times)):
                # Ensure values aren't None before rounding/saving
                t_val = temps[i] if i < len(temps) and temps[i] is not None else 0.0
                h_val = humidities[i] if i < len(humidities) and humidities[i] is not None else 0.0
                history.append({
                    'date': times[i],
                    'avg_temperature_c': float(t_val),
                    'avg_humidity': float(h_val)
                })
            return history
        except requests.RequestException as e:
            raise WeatherAPIError(f"Open-Meteo connection failed: {str(e)}")

def calculate_growth_chance(crop, forecast_days):
    if not forecast_days:
        return 0.0, "Unfavorable"
    
    favorable_days = 0
    total_days = len(forecast_days)
    
    for day in forecast_days:
        temp = day['avg_temperature_c']
        hum = day['avg_humidity']
        
        temp_ok = crop.ideal_temp_min_c <= temp <= crop.ideal_temp_max_c
        hum_ok = crop.ideal_humidity_min <= hum <= crop.ideal_humidity_max
        
        if temp_ok and hum_ok:
            favorable_days += 1
            
    pct = (favorable_days / total_days) * 100
    verdict = "Good" if pct >= 70.0 else "Mixed" if pct >= 40.0 else "Unfavorable"
        
    return round(pct, 2), verdict
