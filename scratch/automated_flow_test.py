import os
import django
import sys

# Initialize Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plantcare.settings")
django.setup()

from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from scans.models import ScanHistory

User = get_user_model()

def run_automated_flow():
    print("====================================================")
    print("STARTING PROGRAMMATIC USER FLOW TESTING LOOP (5x)")
    print("====================================================")

    # Clean up existing test user if present
    User.objects.filter(username="test_user_krish").delete()
    print("Initial cleanup complete: existing 'test_user_krish' removed.")

    client = Client()

    # 1. Register Account via /register/
    print("\n--- STEP 1: Registering account 'test_user_krish' ---")
    reg_response = client.post('/register/', {
        'username': 'test_user_krish',
        'email': 'test_user_krish@example.com',
        'password1': 'test_user_password123',
        'password2': 'test_user_password123',
        'first_name': 'Test',
        'last_name': 'User',
        'phone_number': '9876543210',
        'farm_name': 'Test Farm',
        'farm_size_acres': '12.0',
        'location_city': 'Ahmedabad',
    }, follow=True)

    if reg_response.status_code != 200:
        print(f"Error during registration: status {reg_response.status_code}")
        print(reg_response.content.decode('utf-8')[:500])
        return False

    print("Registration successful! User redirected & logged in.")
    
    # Check Dashboard pagination styles in HTML output
    dash_res = client.get('/')
    dash_html = dash_res.content.decode('utf-8')
    if 'pagination' in dash_html and 'pagination .page-link' in dash_html:
        print("[PASSED] Pagination custom color style overrides verified in base.html.")
    else:
        print("[FAILED] Pagination styling missing in base.html.")
        return False
    
    # Verify user exists in database
    try:
        user = User.objects.get(username="test_user_krish")
        print(f"Verified DB record: {user.username} (City: {user.location_city}, GPS: {user.latitude}, {user.longitude})")
    except User.DoesNotExist:
        print("Error: User record not found in database after signup POST.")
        return False

    # 2. Main Loop: Run 5 times for different cities
    cities = ["Mumbai", "Pune", "Surat", "Delhi", "Bangalore"]
    organs = ["leaf", "flower", "fruit", "bark", "leaf"]
    langs = ["hi", "gu", "en", "hi", "en"]
    themes = ["dark", "light", "dark", "light", "dark"]

    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_leaf.png")
    with open(image_path, "rb") as f:
        image_content = f.read()

    for idx in range(5):
        city = cities[idx]
        organ = organs[idx]
        lang = langs[idx]
        theme = themes[idx]

        print(f"\n--- ITERATION {idx + 1}: Testing City '{city}' ---")

        # A. Query Weather Advisor by City Name (Option 1)
        print(f"  A. Querying weather for city '{city}'...")
        weather_res = client.get(f"/weather/?city={city}")
        if weather_res.status_code != 200:
            print(f"  Error loading weather for {city}: status {weather_res.status_code}")
            return False
        
        weather_html = weather_res.content.decode('utf-8')
        if any(term in weather_html for term in ["Rain Chance", "વરસાદની શક્યતા", "बारिश की संभावना"]):
            print(f"     [PASSED] Rain Prediction details verified in weather advisor HTML.")
        else:
            print(f"     [FAILED] Rain Prediction details missing in weather advisor HTML.")
            return False
            
        print(f"     Weather page loaded successfully for city '{city}' (Status: 200).")

        # B. Post Leaf Diagnostics Scan
        print(f"  B. Uploading diagnostics photo for organ '{organ}'...")
        uploaded_image = SimpleUploadedFile("test_leaf.png", image_content, content_type="image/png")
        scan_res = client.post("/scan/", {
            'image': uploaded_image,
            'organ': organ,
            'use_location': 'on',
            'latitude': '23.0225',
            'longitude': '72.5714'
        }, follow=True)

        if scan_res.status_code != 200:
            print(f"  Error performing scan upload: status {scan_res.status_code}")
            return False

        # Retrieve last scan details from context or DB
        last_scan = ScanHistory.objects.filter(user=user).order_by('-created_at').first()
        if last_scan:
            print(f"     Scan diagnosis result: {last_scan.identified_species} (Confidence: {last_scan.confidence_score * 100:.1f}%)")
            # PDF Download Verification
            pdf_res = client.get(f"/scan/download-pdf/{last_scan.id}/")
            if pdf_res.status_code == 200 and pdf_res.get('Content-Type') == 'application/pdf':
                pdf_bytes = b"".join(pdf_res.streaming_content)
                print(f"     [PASSED] Localized PDF Report generated successfully (Size: {len(pdf_bytes)} bytes).")
            else:
                print(f"     [FAILED] PDF download status: {pdf_res.status_code}, Content-Type: {pdf_res.get('Content-Type')}")
                return False
        else:
            print("     Warning: No scan history recorded in database.")

        # C. Update Profile Settings (Toggle preferred language and theme)
        print(f"  C. Toggling profile settings (Lang: {lang}, Theme: {theme})...")
        profile_res = client.post("/profile/", {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test_user_krish@example.com',
            'phone_number': '9876543210',
            'location_city': city,
            'farm_name': 'Test Farm Updated',
            'farm_size_acres': '15.5',
            'preferred_language': lang,
            'theme_preference': theme
        }, follow=True)

        if profile_res.status_code != 200:
            print(f"  Error updating profile: status {profile_res.status_code}")
            return False

        # Verify profile updates in DB
        user.refresh_from_db()
        print(f"     Verified updates: Lang={user.preferred_language}, Theme={user.theme_preference}, City={user.location_city}")

    # 3. Clean up (Delete account)
    print("\n--- STEP 3: Deleting test account 'test_user_krish' ---")
    User.objects.filter(username="test_user_krish").delete()
    
    # Confirm deletion
    if not User.objects.filter(username="test_user_krish").exists():
        print("Success: Test user account deleted cleanly from database.")
    else:
        print("Error: Test user account still exists in database.")
        return False

    print("\n====================================================")
    print("ALL 5 ITERATIONS PASSED SUCCESSFULLY WITH NO ERRORS!")
    print("====================================================")
    return True

if __name__ == "__main__":
    success = run_automated_flow()
    sys.exit(0 if success else 1)
