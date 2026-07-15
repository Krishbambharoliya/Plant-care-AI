import json
from django.conf import settings

def translation_processor(request):
    lang = 'en'
    theme = 'light'
    
    u = request.user
    lang = u.preferred_language if u.is_authenticated else request.session.get('preferred_language', 'en')
    theme = u.theme_preference if u.is_authenticated else request.session.get('theme_preference', 'light')
        
    path = settings.BASE_DIR / 'translations' / f'{lang}.json'
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            flat = json.load(f)
    except Exception:
        flat = {}
        
    # Convert flat keys with dots (like "nav.dashboard") into nested dictionaries
    nested = {}
    for key, val in flat.items():
        parts = key.split('.')
        current = nested
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = val
        
    from accounts.constants import GUJARAT_CITIES
    return {
        't': nested,
        'current_language': lang,
        'current_theme': theme,
        'gujarat_cities': GUJARAT_CITIES
    }
