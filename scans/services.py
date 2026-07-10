import requests
from django.conf import settings

class PlantNetError(Exception):
    pass

class PlantNetClient:
    @staticmethod
    def identify(image_file, organ):
        api_key = getattr(settings, 'PLANTNET_API_KEY', None)
        project = getattr(settings, 'PLANTNET_PROJECT', 'all')
        if not api_key:
            raise PlantNetError("PlantNet API key not configured.")
        
        # Enforce 500 daily API limit check
        import datetime
        from django.utils import timezone
        from scans.models import ScanHistory
        
        day_ago = timezone.now() - datetime.timedelta(days=1)
        recent_scans_count = ScanHistory.objects.filter(created_at__gte=day_ago).count()
        if recent_scans_count >= 500:
            raise PlantNetError("PlantNet API call limit (500) has been reached for today. Please try again tomorrow.")
        
        url = f"https://my-api.plantnet.org/v2/identify/{project}?api-key={api_key}"
        
        # Make sure file pointer is at the beginning
        image_file.seek(0)
        
        files = {
            'images': (image_file.name, image_file.read(), 'image/jpeg')
        }
        data = {
            'organs': [organ]
        }
        
        try:
            response = requests.post(url, files=files, data=data, timeout=15)
            if response.status_code != 200:
                raise PlantNetError(f"PlantNet API returned status code {response.status_code}: {response.text}")
            
            res_json = response.json()
            results = res_json.get('results')
            if not results:
                raise PlantNetError("No identification results returned by PlantNet.")
            
            top_result = results[0]
            species = top_result.get('species', {})
            
            # Extract names
            scientific_name = species.get('scientificNameWithoutAuthor', '')
            if not scientific_name:
                scientific_name = species.get('scientificName', '')
            
            common_names = species.get('commonNames', [])
            common_name = common_names[0] if common_names else None
            
            score = top_result.get('score', 0.0)
            
            return {
                'species': scientific_name,
                'common_name': common_name,
                'confidence_score': score,
                'raw': res_json
            }
        except requests.RequestException as e:
            raise PlantNetError(f"PlantNet API connection failed: {str(e)}")
