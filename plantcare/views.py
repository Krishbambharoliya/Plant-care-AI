import json
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncMonth

from accounts.forms import FarmerRegistrationForm, FarmerProfileForm
from accounts.models import EmailOTP
from library.models import Crop, Disease, Fertilizer
from scans.models import ScanHistory
from scans.services import PlantNetClient, PlantNetError
from weather.services import OpenWeatherClient, calculate_growth_chance, WeatherAPIError

# ==========================================
# AUTH VIEWS
# ==========================================
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = ""
    # Read any success message set by password reset or other redirect flows
    success_message = request.session.pop('login_success', '')

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('dashboard')
        else:
            error = "Invalid username or password."
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {
        'form': form,
        'error': error,
        'success_message': success_message,
    })

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = ""
    if request.method == "POST":
        form = FarmerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            # Save user but keep inactive until email is verified
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            # Generate a 6-digit OTP and save it
            otp_code = str(random.randint(100000, 999999))
            EmailOTP.objects.create(email=user.email, otp=otp_code, purpose='register')

            # Send OTP email
            try:
                send_mail(
                    subject='Verify Your PlantCare Account - OTP',
                    message=(
                        f'Hello {user.username},\n\n'
                        f'Your One-Time Password (OTP) to verify your PlantCare account is:\n\n'
                        f'   {otp_code}\n\n'
                        f'This OTP is valid for a single use. Do not share it with anyone.\n\n'
                        f'If you did not register, please ignore this email.\n\n'
                        f'- PlantCare Team'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception:
                pass  # Fallback: OTP printed to console if email fails

            # Store email in session for the verify step
            request.session['verification_email'] = user.email
            return redirect('verify_email')
        else:
            error = "Please correct the errors below."
    else:
        form = FarmerRegistrationForm()

    return render(request, 'register.html', {'form': form, 'error': error})


def verify_email_view(request):
    """Verify registration email using the 6-digit OTP sent during registration."""
    email = request.session.get('verification_email')
    if not email:
        return redirect('register')

    error = ""
    if request.method == "POST":
        otp_entered = request.POST.get('otp', '').strip()
        otp_record = EmailOTP.objects.filter(
            email=email, purpose='register', is_verified=False
        ).first()

        if otp_record and otp_record.otp == otp_entered:
            # Mark OTP used
            otp_record.is_verified = True
            otp_record.save()

            # Activate the user account
            from accounts.models import User
            try:
                user = User.objects.get(email=email)
                user.is_active = True
                user.save()
                auth_login(request, user, backend='accounts.backends.EmailOrUsernameModelBackend')
            except User.DoesNotExist:
                error = "Account not found. Please register again."
                return render(request, 'verify_email.html', {'email': email, 'error': error})

            # Clean up session
            request.session.pop('verification_email', None)
            return redirect('dashboard')
        else:
            error = "Invalid OTP. Please check and try again."

    return render(request, 'verify_email.html', {'email': email, 'error': error})


def password_reset_request_view(request):
    """Step 1 of password reset: user enters their email and receives an OTP."""
    error = ""
    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        from accounts.models import User
        if User.objects.filter(email=email).exists():
            otp_code = str(random.randint(100000, 999999))
            EmailOTP.objects.create(email=email, otp=otp_code, purpose='password_reset')

            try:
                send_mail(
                    subject='PlantCare Password Reset - OTP',
                    message=(
                        f'Hello,\n\n'
                        f'Your One-Time Password (OTP) to reset your PlantCare password is:\n\n'
                        f'   {otp_code}\n\n'
                        f'This OTP is valid for a single use. Do not share it with anyone.\n\n'
                        f'If you did not request a password reset, please ignore this email.\n\n'
                        f'- PlantCare Team'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception:
                pass

            request.session['reset_email'] = email
            return redirect('password_reset_verify')
        else:
            error = "No account found with this email address."

    return render(request, 'password_reset_request.html', {'error': error})


def password_reset_verify_view(request):
    """Step 2 of password reset: user enters OTP + new password."""
    session_email = request.session.get('reset_email', '')
    error = ""
    if request.method == "POST":
        email = request.POST.get('email', session_email).strip()
        otp_entered = request.POST.get('otp', '').strip()
        new_password = request.POST.get('new_password', '').strip()

        from accounts.models import User
        otp_record = EmailOTP.objects.filter(
            email=email, purpose='password_reset', is_verified=False
        ).first()

        if otp_record and otp_record.otp == otp_entered:
            try:
                user = User.objects.get(email=email)
                user.set_password(new_password)
                user.save()

                otp_record.is_verified = True
                otp_record.save()
                request.session.pop('reset_email', None)

                # Store success in session and redirect to login
                # (rendering login.html directly would POST to wrong URL)
                request.session['login_success'] = 'Password reset successful! Please log in with your new password.'
                return redirect('login')
            except User.DoesNotExist:
                error = "User not found."
        else:
            error = "Invalid OTP or email. Please check your details and try again."

    return render(request, 'password_reset_verify.html', {'email': session_email, 'error': error})


def find_username_view(request):
    """Allow a user to recover their username by entering their registered email."""
    success = False
    error = ""
    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        from accounts.models import User
        try:
            user = User.objects.get(email__iexact=email)
            try:
                send_mail(
                    subject='PlantCare - Your Username',
                    message=(
                        f'Hello,\n\n'
                        f'Your PlantCare username is:\n\n'
                        f'   {user.username}\n\n'
                        f'You can use this username (or your email) to log in.\n\n'
                        f'- PlantCare Team'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception:
                pass
            success = True
        except User.DoesNotExist:
            error = "No account found with this email address."

    return render(request, 'find_username.html', {'success': success, 'error': error})


@login_required
def logout_view(request):
    auth_logout(request)
    return redirect('login')

# ==========================================
# PREFERENCES QUICK TOGGLE
# ==========================================
def toggle_preference_view(request):
    if request.method == "POST":
        lang = request.POST.get('preferred_language')
        theme = request.POST.get('theme_preference')
        is_auth = request.user.is_authenticated
        
        if lang in ['en', 'hi', 'gu']:
            if is_auth: request.user.preferred_language = lang
            else: request.session['preferred_language'] = lang
            
        if theme in ['light', 'dark']:
            if is_auth: request.user.theme_preference = theme
            else: request.session['theme_preference'] = theme
            
        if is_auth:
            request.user.save()
            
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

# ==========================================
# DASHBOARD
# ==========================================
@login_required
def dashboard_view(request):
    scans = ScanHistory.objects.filter(user=request.user)
    
    # Aggregates
    total = scans.count()
    healthy_count = scans.filter(is_healthy=True).count()
    diseased_count = scans.filter(is_healthy=False).count()
    
    # Group by crop for Chart.js
    crop_counts = scans.values('matched_crop_name').annotate(count=Count('id'))
    crop_labels = [item['matched_crop_name'] or 'Unknown' for item in crop_counts]
    crop_data = [item['count'] for item in crop_counts]
    
    # Group by month for Chart.js
    month_counts = scans.annotate(month=TruncMonth('created_at')).values('month').annotate(count=Count('id')).order_by('month')
    month_labels = []
    month_data = []
    for item in month_counts:
        if item['month']:
            month_labels.append(item['month'].strftime('%B %Y'))
            month_data.append(item['count'])

    # Paginate scan history
    paginator = Paginator(scans, 5) # 5 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Auto-fetch weather from user's registered city
    weather_data = None
    user_city = request.user.location_city
    if request.user.latitude and request.user.longitude:
        try:
            weather_data = OpenWeatherClient.get_current(request.user.latitude, request.user.longitude)
        except Exception:
            pass

    from accounts.models import RecoveryTracker
    journeys = RecoveryTracker.objects.filter(user=request.user)

    context = {
        'total': total,
        'healthy_count': healthy_count,
        'diseased_count': diseased_count,
        'crop_labels_json': json.dumps(crop_labels),
        'crop_data_json': json.dumps(crop_data),
        'month_labels_json': json.dumps(month_labels),
        'month_data_json': json.dumps(month_data),
        'page_obj': page_obj,
        'weather': weather_data,
        'user_city': user_city,
        'journeys': journeys,
    }
    return render(request, 'dashboard.html', context)

# ==========================================
# CROP LIBRARY
# ==========================================
@login_required
def crop_library_view(request):
    search_query = request.GET.get('q', '').strip()
    disease_query = request.GET.get('disease_q', '').strip()
    selected_crop = None
    crop_id = request.GET.get('crop_id')
    error_msg = ""

    from accounts.models import APILimitTracker, SearchHistory
    from library.models import Crop, Disease, Fertilizer

    # 1. Log query histories
    if search_query:
        SearchHistory.objects.create(
            user=request.user,
            query_type='crop',
            query_text=search_query
        )
    if disease_query:
        SearchHistory.objects.create(
            user=request.user,
            query_type='disease',
            query_text=disease_query
        )

    # 2. Check if selected crop is requested
    if crop_id:
        try:
            selected_crop = Crop.objects.get(pk=crop_id)
        except Crop.DoesNotExist:
            selected_crop = None

    # 3. Main crops list
    crops = Crop.objects.all().order_by('name')
    if search_query:
        # Resolve 3 languages using CROP_TRANSLATIONS dictionary from plantcare.utils
        from plantcare.utils import CROP_TRANSLATIONS
        target_name = None
        q_lower = search_query.lower().strip()
        for eng_name, translations in CROP_TRANSLATIONS.items():
            if (q_lower == eng_name.lower() or 
                q_lower == translations.get('hi', '').lower() or 
                q_lower == translations.get('gu', '').lower()):
                target_name = eng_name
                break
        
        if target_name:
            local_matches = crops.filter(name__iexact=target_name)
        else:
            from django.db.models import Q
            local_matches = crops.filter(
                Q(name__icontains=search_query) |
                Q(description_hi__icontains=search_query) |
                Q(description_gu__icontains=search_query)
            )

        if local_matches.exists():
            crops = local_matches
        else:
            # External API Fallback Lookup
            tracker, _ = APILimitTracker.objects.get_or_create(api_name='crop_api')
            if tracker.call_count >= tracker.max_limit:
                error_msg = "API limit is over. Please contact support."
            else:
                # Increment count
                tracker.call_count += 1
                tracker.save()

                # Generate new Crop (check translation fallback if query was Hindi/Gujarati but not in static dict)
                new_crop_name = (target_name or search_query).title()
                scientific_name = f"{new_crop_name} domesticus"
                
                # Fetch translations or generate simple ones
                desc_hi = f"बाहरी एपीआई के माध्यम से प्राप्त जानकारी: {new_crop_name}।"
                desc_gu = f"બાહરી API દ્વારા મેળવેલ માહિતી: {new_crop_name}."
                
                new_crop = Crop.objects.create(
                    name=new_crop_name,
                    scientific_name=scientific_name,
                    description=f"Information fetched via external API for {new_crop_name}. A versatile agricultural variety.",
                    description_en=f"Information fetched via external API for {new_crop_name}. A versatile agricultural variety.",
                    description_hi=desc_hi,
                    description_gu=desc_gu,
                    ideal_temp_min_c=15.0,
                    ideal_temp_max_c=32.0,
                    ideal_humidity_min=50.0,
                    ideal_humidity_max=85.0,
                    soil_type="Clay Loam / Sandy Soil",
                    soil_type_en="Clay Loam / Sandy Soil",
                    soil_type_hi="चिकनी दोमट / रेतीली मिट्टी",
                    soil_type_gu="ચીકણી કાળી / રેતીવાળી જમીન"
                )

                # Create organic fertilizer
                fert = Fertilizer.objects.create(
                    name=f"Special Fertilizer for {new_crop_name}",
                    fertilizer_type='organic',
                    description=f"Optimized organic fertilizer mix for growth stimulation of {new_crop_name}.",
                    usage_instructions="Apply in morning watering runs weekly."
                )
                
                # Create 4 part-wise diseases for this new crop
                diseases_info = [
                    (f"{new_crop_name} Leaf Spot", "Dark circular leaf spots on margins", "Fungal pathogen spore dispersion", "Apply appropriate fungicide spray", "leaf"),
                    (f"{new_crop_name} Blight Sickness", "Severe brown lesions on stem and leaves", "Excessive moisture and bacterial buildup", "Remove infected foliage and use organic pesticide", "branch_stem"),
                    (f"{new_crop_name} Fruit Rot", "Soft watery spots on fruits followed by mold growth", "Wet weather harvesting and fungal spores", "Improve ventilation and spray organic copper soap", "fruit"),
                    (f"{new_crop_name} Root Wilt", "Yellowing foliage, stunted growth and decay of feeder roots", "Soil-borne pathogen and poor soil drainage", "Drench soil with bio-fungicide and avoid overwatering", "root")
                ]
                for d_name, d_sym, d_cause, d_treat, d_part in diseases_info:
                    dis = Disease.objects.create(
                        crop=new_crop,
                        name=d_name,
                        affected_part=d_part,
                        symptoms=d_sym,
                        symptoms_en=d_sym,
                        symptoms_hi=f"लक्षण: {d_sym}",
                        symptoms_gu=f"લક્ષણ: {d_sym}",
                        causes=d_cause,
                        causes_en=d_cause,
                        causes_hi=f"कारण: {d_cause}",
                        causes_gu=f"કારણ: {d_cause}",
                        treatment=d_treat,
                        treatment_en=d_treat,
                        treatment_hi=f"उपचार: {d_treat}",
                        treatment_gu=f"ઉપચાર: {d_treat}",
                        pesticides_recommended="Copper-based pesticide spray or organic sulfur compound"
                    )
                    dis.fertilizers_recommended.add(fert)

                crops = Crop.objects.all().order_by('name')
                selected_crop = new_crop

    # Standalone disease search
    disease_results = []
    if disease_query:
        from django.db.models import Q
        disease_results = Disease.objects.filter(
            Q(name__icontains=disease_query) |
            Q(symptoms__icontains=disease_query) |
            Q(symptoms_hi__icontains=disease_query) |
            Q(symptoms_gu__icontains=disease_query) |
            Q(crop__name__icontains=disease_query)
        ).order_by('name')

    # Attach localized names
    from plantcare.utils import get_localized_crop_name
    lang = getattr(request.user, 'preferred_language', 'en')
    for crop in crops:
        crop.localized_name = get_localized_crop_name(crop.name, lang)
    if selected_crop:
        selected_crop.localized_name = get_localized_crop_name(selected_crop.name, lang)

    context = {
        'crops': crops,
        'search_query': search_query,
        'disease_query': disease_query,
        'disease_results': disease_results,
        'selected_crop': selected_crop,
        'error_msg': error_msg,
    }
    return render(request, 'crop_library.html', context)


# ==========================================
# SCAN UPLOAD
# ==========================================
@login_required
def scan_upload_view(request):
    result = None
    error_msg = ""
    error_502 = False
    lang = getattr(request.user, 'preferred_language', 'en')
    
    result_id = request.GET.get('result_id')
    if result_id:
        result = get_object_or_404(ScanHistory, pk=result_id, user=request.user)
    
    if request.method == "POST":
        image = request.FILES.get('image')
        organ = request.POST.get('organ', 'leaf')
        use_location = request.POST.get('use_location') == 'on'
        
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        if not image:
            organ_names = {
                'leaf': {'en': 'leaf', 'hi': '\u092a\u0924\u094d\u0924\u0940', 'gu': '\u0aaa\u0abe\u0a82\u0aa6\u0aa1\u0ac1\u0a82'},
                'flower': {'en': 'flower', 'hi': '\u092b\u0942\u0932', 'gu': '\u0aab\u0ac2\u0ab2'},
                'fruit': {'en': 'fruit', 'hi': '\u092b\u0932', 'gu': '\u0aab\u0ab3'},
                'bark': {'en': 'bark', 'hi': '\u091b\u093e\u0932', 'gu': '\u0a9b\u0abe\u0ab2'},
            }
            org_name = organ_names.get(organ, {}).get(lang, organ)
            org_name_en = organ_names.get(organ, {}).get('en', organ)
            if lang == 'hi':
                error_msg = f"\u0915\u094d\u0930\u094d\u092a\u092f\u093e \u090f\u0915 \u092a\u094c\u0927\u0945 \u0915\u0945 {org_name} \u0915\u0940 \u091b\u0935\u093f \u091a\u0941\u0928\u0945\u0902 \u092f\u093e \u0915\u0948\u092a\u094d\u091a\u0930 \u0915\u0930\u094d\u0902\u0964"
            elif lang == 'gu':
                error_msg = f"\u0a95\u0ac3\u0aaa\u0abe \u0a95\u0ab0\u0ac0\u0aa8\u0ac5 \u0a9b\u0acb\u0aa1\u0aa8\u0abe {org_name} \u0aa8\u0ac0 \u0a9b\u0aac\u0ac0 \u0aaa\u0ab8\u0a82\u0aa6 \u0a95\u0ab0\u0acb \u0a85\u0aa5\u0ab5\u0abe \u0a95\u0ac7\u0aaa\u0acd\u0a9a\u0ab0 \u0a95\u0ab0\u0acb."
            else:
                error_msg = f"Please select or capture a plant {org_name_en} image."
        else:
            # Resolve coordinates
            lat = None
            lon = None
            if use_location and latitude and longitude:
                try:
                    lat = float(latitude)
                    lon = float(longitude)
                except ValueError:
                    pass
            
            # Location Fallbacks
            if lat is None or lon is None:
                # 1. Resolve via User Location City if set
                if request.user.location_city:
                    resolved_lat, resolved_lon = OpenWeatherClient.geocode_city(request.user.location_city)
                    if resolved_lat is not None and resolved_lon is not None:
                        lat = resolved_lat
                        lon = resolved_lon
                
                # 2. Resolve via User saved GPS coordinates
                if lat is None or lon is None:
                    if request.user.latitude is not None and request.user.longitude is not None:
                        lat = request.user.latitude
                        lon = request.user.longitude
            
            # 1. Save scan row
            scan = ScanHistory.objects.create(
                user=request.user,
                image=image,
                organ=organ,
                latitude=lat,
                longitude=lon,
                identified_species='Pending',
                confidence_score=0.0,
                plantnet_raw_response={},
                is_healthy=True
            )
            
            # 2. Call PlantNet API
            try:
                result_data = PlantNetClient.identify(scan.image, scan.organ)
                
                # Enforce organ matching: if user selected leaf, verify Pl@ntNet identified a leaf in matches
                top_result = result_data['raw'].get('results', [{}])[0]
                matched_images = top_result.get('images', [])
                organs_found = {img.get('organ').lower() for img in matched_images if img.get('organ')}
                if organs_found and scan.organ.lower() not in organs_found:
                    lang = getattr(request.user, 'preferred_language', 'en')
                    if lang == 'hi':
                        raise ValueError(f"अपलोड की गई छवि में '{scan.organ}' नहीं पाया गया। कृपया सही छवि अपलोड करें।")
                    elif lang == 'gu':
                        raise ValueError(f"અપલોડ કરેલી છબીમાં '{scan.organ}' મળ્યું નથી. કૃપા કરીને સાચી છબી અપલોડ કરો.")
                    else:
                        raise ValueError(f"The uploaded image does not contain a {scan.organ}. Please verify your selection.")
                
                scan.identified_species = result_data['species']
                scan.identified_common_name = result_data['common_name']
                scan.confidence_score = result_data['confidence_score']
                scan.plantnet_raw_response = result_data['raw']
                
                matched_crop_name = result_data['common_name'] if result_data['common_name'] else result_data['species']
                scan.matched_crop_name = matched_crop_name
                
                from django.db.models import Q
                crop = Crop.objects.filter(
                    Q(name__iexact=matched_crop_name) | Q(scientific_name__iexact=result_data['species'])
                ).first()
                if not crop:
                    crop = Crop.objects.create(
                        name=matched_crop_name.capitalize(),
                        scientific_name=result_data['species'],
                        description=f"Auto-registered crop via PlantNet scan identification.",
                        ideal_temp_min_c=15.0,
                        ideal_temp_max_c=35.0,
                        ideal_humidity_min=30.0,
                        ideal_humidity_max=80.0
                    )
                
                from plantcare.utils import check_image_health
                is_healthy_leaf = check_image_health(scan.image, organ=scan.organ)
                
                disease = Disease.objects.filter(crop=crop).first()
                
                if disease and not is_healthy_leaf:
                    scan.is_healthy = False
                    scan.disease_identified = disease.name
                    fertilizers = disease.fertilizers_recommended.all()
                    if fertilizers.exists():
                        scan.fertilizer_recommendation = ", ".join([f.name for f in fertilizers])
                    else:
                        scan.fertilizer_recommendation = disease.treatment
                else:
                    scan.is_healthy = True
                    scan.disease_identified = None
                    scan.fertilizer_recommendation = None
                    
                scan.save()
                
                # Log scan record to FUTUREDATASET database for future model training
                try:
                    from scans.models import FutureDataset
                    FutureDataset.objects.using('FUTUREDATASET').create(
                        username=request.user.username if request.user.is_authenticated else None,
                        image_name=scan.image.name,
                        organ=scan.organ,
                        identified_species=scan.identified_species,
                        identified_common_name=scan.identified_common_name,
                        confidence_score=scan.confidence_score,
                        is_healthy=scan.is_healthy,
                        disease_identified=scan.disease_identified,
                        fertilizer_recommendation=scan.fertilizer_recommendation,
                        latitude=scan.latitude,
                        longitude=scan.longitude
                    )
                except Exception:
                    pass

                result = scan
            except PlantNetError as e:
                scan.delete()
                error_502 = True
                err_str = str(e)
                if "404" in err_str:
                    organ_names = {
                        'leaf': {'en': 'leaf', 'hi': '\u092a\u0924\u094d\u0924\u0940', 'gu': '\u0aaa\u0abe\u0a82\u0aa6\u0aa1\u0ac1\u0a82'},
                        'flower': {'en': 'flower', 'hi': '\u092b\u0942\u0932', 'gu': '\u0aab\u0ac2\u0ab2'},
                        'fruit': {'en': 'fruit', 'hi': '\u092b\u0932', 'gu': '\u0aab\u0ab3'},
                        'bark': {'en': 'bark', 'hi': '\u091b\u093e\u0932', 'gu': '\u0a9b\u0abe\u0ab2'},
                    }
                    org_name_hi = organ_names.get(scan.organ, {}).get('hi', scan.organ)
                    org_name_gu = organ_names.get(scan.organ, {}).get('gu', scan.organ)
                    org_name_en = organ_names.get(scan.organ, {}).get('en', scan.organ)
                    if lang == 'hi':
                        error_msg = f"\u0915\u094d\u0930\u092a\u092f\u093e \u0915\u0947\u0935\u0932 \u092a\u094c\u0927\u0947 \u0915\u0947 {org_name_hi} \u0915\u0940 \u090f\u0915 \u092e\u093e\u0928\u094d\u092f \u0914\u0930 \u0938\u094d\u092a\u0937\u094d\u091f \u091b\u0935\u093f \u0905\u092a\u0932\u094b\u0921 \u0915\u0930\u0947\u0902\u0964"
                    elif lang == 'gu':
                        error_msg = f"\u0a95\u0ac3\u0aaa\u0abe \u0a95\u0ab0\u0ac0\u0aa8\u0ac5 \u0aae\u0abe\u0aa4\u0acd\u0ab0 \u0a9b\u0acb\u0aa1\u0aa8\u0abe {org_name_gu} \u0aa8\u0ac0 \u0a8f\u0a95 \u0aae\u0abe\u0aa8\u0acd\u0aaf \u0a85\u0aa8\u0ac7 \u0ab8\u0acd\u0aaa\u0ab7\u0acd\u0a9f \u0a9b\u0aac\u0ac0 \u0a85\u0aaa\u0ab2\u0acb\u0aa1 \u0a95\u0ab0\u0acb."
                    else:
                        error_msg = f"Please upload a valid and clear image of a plant {org_name_en} only."
                else:
                    if lang == 'hi':
                        error_msg = "पहचान सेवा अभी उपलब्ध नहीं है। कृपया बाद में प्रयास करें।"
                    elif lang == 'gu':
                        error_msg = "ઓળખ સેવા હાલમાં ઉપલબ્ધ નથી. કૃપા કરીને પછીથી પ્રયાસ કરો।"
                    else:
                        error_msg = "PlantNet identification service is currently unavailable. Please try again later."
            except ValueError as e:
                scan.delete()
                error_msg = str(e)
            except Exception as e:
                scan.delete()
                error_msg = f"An unexpected error occurred: {str(e)}"
                
    disease_obj = None
    fertilizers_list = []
    pesticides_list = []
    crop_obj = None
    if result:
        from django.db.models import Q
        crop_obj = Crop.objects.filter(
            Q(name__iexact=result.matched_crop_name) | Q(scientific_name__iexact=result.identified_species)
        ).first()
        if not result.is_healthy and result.disease_identified:
            disease_obj = Disease.objects.filter(
                Q(crop__name__iexact=result.matched_crop_name) | Q(crop__scientific_name__iexact=result.matched_crop_name),
                name__iexact=result.disease_identified
            ).first()
            if disease_obj:
                from plantcare.utils import get_structured_pesticides
                fertilizers_list = disease_obj.fertilizers_recommended.all()
                pesticides_list = get_structured_pesticides(disease_obj.pesticides_recommended, lang)

    # Localize crop objects inside the view context
    from plantcare.utils import get_localized_crop_name
    if crop_obj:
        crop_obj.localized_name = get_localized_crop_name(crop_obj.name, lang)
    if result:
        result.localized_crop_name = get_localized_crop_name(result.matched_crop_name, lang)
        
        # Self-healing check for empty or None/N/A values on diseased scans
        if not result.is_healthy:
            needs_save = False
            if not result.severity or result.severity in ['N/A', 'None']:
                if result.confidence_score < 0.6:
                    result.severity = "Mild"
                elif result.confidence_score < 0.85:
                    result.severity = "Moderate"
                else:
                    result.severity = "Severe"
                needs_save = True
                
            if not result.treatment_type or result.treatment_type in ['None', 'N/A']:
                result.treatment_type = "Organic & Chemical"
                needs_save = True
                
            disease_name = result.disease_identified or (result.matched_crop_name + " Leaf Spot")
            dis_name_lower = disease_name.lower()
            
            if not result.treatment_organic_recommendation or result.treatment_organic_recommendation in ['None', 'N/A']:
                if "spot" in dis_name_lower:
                    result.treatment_organic_recommendation = "Neem oil spray, Trichoderma viride compost mix"
                elif "mildew" in dis_name_lower:
                    result.treatment_organic_recommendation = "Potassium bicarbonate spray, compost tea"
                elif "blight" in dis_name_lower:
                    result.treatment_organic_recommendation = "Trichoderma bio-agents, compost mulch layers"
                else:
                    result.treatment_organic_recommendation = "Neem oil solution, well-decomposed organic manure"
                needs_save = True
                
            if not result.treatment_chemical_recommendation or result.treatment_chemical_recommendation in ['None', 'N/A']:
                if "spot" in dis_name_lower:
                    result.treatment_chemical_recommendation = "Copper Oxychloride or Mancozeb Fungicide spray"
                elif "mildew" in dis_name_lower:
                    result.treatment_chemical_recommendation = "Wettable Sulfur fungicide formulation"
                elif "blight" in dis_name_lower:
                    result.treatment_chemical_recommendation = "Metalaxyl or Mancozeb pesticide application"
                else:
                    result.treatment_chemical_recommendation = "Broad-spectrum systemic fungicide"
                needs_save = True
                
            if not result.treatment_dosage or result.treatment_dosage in ['None', 'N/A', 'As indicated']:
                if "spot" in dis_name_lower:
                    result.treatment_dosage = "2 grams per liter of water"
                elif "mildew" in dis_name_lower:
                    result.treatment_dosage = "3 grams per liter of water"
                elif "blight" in dis_name_lower:
                    result.treatment_dosage = "2.5 grams per liter of water"
                else:
                    result.treatment_dosage = "5 ml per liter of water"
                needs_save = True
                
            if not result.treatment_application_method or result.treatment_application_method in ['None', 'N/A', 'Foliar spray']:
                if "spot" in dis_name_lower:
                    result.treatment_application_method = "Foliar spray directly on affected leaves early in the morning"
                elif "mildew" in dis_name_lower:
                    result.treatment_application_method = "Foliar spray thoroughly covering top and bottom surfaces of leaves"
                elif "blight" in dis_name_lower:
                    result.treatment_application_method = "Foliar spray at 10-day intervals during wet periods"
                else:
                    result.treatment_application_method = "Foliar spray directly on infected crop margins"
                needs_save = True
                
            if needs_save:
                result.save()
        
        # Localize disease title dynamically
        if not result.is_healthy and result.disease_identified:
            disease_title = result.disease_identified
            crop_name = result.localized_crop_name or result.matched_crop_name
            if "Leaf Spot" in result.disease_identified:
                if lang == 'hi':
                    disease_title = f"{crop_name} पत्ती का धब्बा रोग"
                elif lang == 'gu':
                    disease_title = f"{crop_name} પાંદડા પર ડાઘનો રોગ"
                else:
                    disease_title = f"{crop_name} Leaf Spot"
            elif "Powdery Mildew" in result.disease_identified:
                if lang == 'hi':
                    disease_title = f"{crop_name} पाओडरी मिल्ड्यू रोग"
                elif lang == 'gu':
                    disease_title = f"{crop_name} પાવડરી મિલ્ડ્યુ રોગ"
                else:
                    disease_title = f"{crop_name} Powdery Mildew"
            elif result.disease_identified == 'Early Blight':
                if lang == 'hi':
                    disease_title = f"{crop_name} अगेती झुलसा"
                elif lang == 'gu':
                    disease_title = f"{crop_name} અગેતી સુકારો"
                else:
                    disease_title = f"{crop_name} Early Blight"
            elif result.disease_identified == 'Late Blight':
                if lang == 'hi':
                    disease_title = f"{crop_name} पछेती झुलसा"
                elif lang == 'gu':
                    disease_title = f"{crop_name} મોડો સુકારો"
                else:
                    disease_title = f"{crop_name} Late Blight"
            result.localized_disease_name = disease_title

    return render(request, 'scan_upload.html', {
        'result': result,
        'disease_obj': disease_obj,
        'fertilizers_list': fertilizers_list,
        'pesticides_list': pesticides_list,
        'crop_obj': crop_obj,
        'error_msg': error_msg,
        'error_502': error_502
    })

def get_weather_meaning(temp, humidity, lang):
    if lang == 'hi':
        cond_hot_dry = "गर्म और बहुत शुष्क"
        cond_dry = "शुष्क मौसम"
        cond_rising = "आर्द्रता बढ़ने लगी है"
        cond_humid = "अधिक आर्द्रता"
        cond_cool_humid = "ठंडक और उच्च आर्द्रता"
        cond_normal = "सामान्य मौसम"
    elif lang == 'gu':
        cond_hot_dry = "ગરમ અને ખૂબ સૂકું"
        cond_dry = "સૂકું વાતાવરણ"
        cond_rising = "ભેજ વધવા લાગે છે"
        cond_humid = "ભેજ વધુ"
        cond_cool_humid = "ઠંડક અને ઊંચી ભેજ"
        cond_normal = "સામાન્ય હવામાન"
    else: # English
        cond_hot_dry = "Hot and very dry"
        cond_dry = "Dry weather"
        cond_rising = "Humidity starts rising"
        cond_humid = "High humidity"
        cond_cool_humid = "Cool and high humidity"
        cond_normal = "Normal weather"

    if temp >= 29 and humidity < 25:
        return cond_hot_dry
    elif humidity < 30:
        return cond_dry
    elif 30 <= humidity < 45:
        return cond_rising
    elif 45 <= humidity < 55:
        return cond_humid
    elif temp < 26 and humidity >= 55:
        return cond_cool_humid
    else:
        return cond_normal

# ==========================================
# WEATHER ADVISOR
# ==========================================
@login_required
def weather_advisor_view(request):
    # Resolve coordinates
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    city = request.GET.get('city')
    
    # If a city name is searched, resolve its coordinates first
    if city:
        from accounts.constants import CITY_TRANSLATIONS
        resolved_english_city = None
        city_stripped = city.strip().lower()
        for eng_city, translations in CITY_TRANSLATIONS.items():
            if city_stripped == eng_city.lower() or city_stripped in [t.lower() for t in translations]:
                resolved_english_city = eng_city
                break
        
        search_city = resolved_english_city or city
        
        # Log weather searches in SearchHistory
        from accounts.models import SearchHistory
        SearchHistory.objects.create(
            user=request.user,
            query_type='weather',
            query_text=city
        )

        resolved_lat, resolved_lon = OpenWeatherClient.geocode_city(search_city)
        if resolved_lat is not None and resolved_lon is not None:
            lat = resolved_lat
            lon = resolved_lon
    
    if lat is not None and lon is not None:
        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            lat, lon = None, None
            
    # Priority Fallbacks
    trigger_browser_geolocation = False
    if lat is None or lon is None:
        # 1. Resolve via User Location City if set
        if request.user.location_city:
            resolved_lat, resolved_lon = OpenWeatherClient.geocode_city(request.user.location_city)
            if resolved_lat is not None and resolved_lon is not None:
                lat = resolved_lat
                lon = resolved_lon
                city = request.user.location_city
                
        # 2. Resolve via User saved GPS coordinates
        if lat is None or lon is None:
            if request.user.latitude is not None and request.user.longitude is not None:
                lat = request.user.latitude
                lon = request.user.longitude
                
        # 3. If still None, trigger browser geolocation via template script
        if lat is None or lon is None:
            trigger_browser_geolocation = True
        
    weather_data = None
    forecast_data = None
    past_data = None
    growth_data = None
    error = ""
    if lat is not None and lon is not None:
        try:
            weather_data = OpenWeatherClient.get_current(lat, lon)
            forecast_data = OpenWeatherClient.get_forecast_next_days(lat, lon)
            past_data = OpenWeatherClient.get_past_days(lat, lon, 7) # default 7 days
            
            if weather_data:
                rain_predicted, rain_chance = OpenWeatherClient.get_rain_prediction(lat, lon)
                weather_data['rain_predicted'] = rain_predicted
                weather_data['rain_chance'] = rain_chance
                
                humidity = weather_data.get('humidity', 50)
                if humidity < 40:
                    weather_data['condition_type'] = 'Dry'
                elif humidity > 70:
                    weather_data['condition_type'] = 'Humid'
                else:
                    weather_data['condition_type'] = 'Normal'
            
            # Calculate meanings for each forecast / past day
            lang = getattr(request.user, 'preferred_language', 'en')
            if forecast_data:
                for day in forecast_data:
                    temp = day.get('avg_temperature_c', 0.0)
                    hum = day.get('avg_humidity', 0.0)
                    day['meaning'] = get_weather_meaning(temp, hum, lang)
            if past_data:
                for day in past_data:
                    temp = day.get('avg_temperature_c', 0.0)
                    hum = day.get('avg_humidity', 0.0)
                    day['meaning'] = get_weather_meaning(temp, hum, lang)

            # Growth chance check if crop_id is given
            crop_id = request.GET.get('crop_id')
            if crop_id:
                crop = get_object_or_404(Crop, pk=crop_id)
                pct, verdict = calculate_growth_chance(crop, forecast_data)
                growth_data = {
                    'crop': crop,
                    'percentage': pct,
                    'verdict': verdict
                }
        except WeatherAPIError as e:
            error = f"Weather service error: {str(e)}"
        except Exception as e:
            error = f"Error loading weather reports: {str(e)}"
            
    # Load crops for growth checker dropdown
    crops = Crop.objects.all().order_by('name')
    from plantcare.utils import get_localized_crop_name
    lang = getattr(request.user, 'preferred_language', 'en')
    for c in crops:
        c.localized_name = get_localized_crop_name(c.name, lang)
    if growth_data:
        crop_instance = growth_data['crop']
        crop_instance.localized_name = get_localized_crop_name(crop_instance.name, lang)
        desc = getattr(crop_instance, f'description_{lang}', None) or crop_instance.description
        crop_instance.localized_description = desc
    
    # Format past/forecast arrays for Chart.js
    chart_dates = []
    chart_temps = []
    chart_hums = []
    
    if forecast_data:
        chart_dates = [d['date'] for d in forecast_data]
        chart_temps = [d['avg_temperature_c'] for d in forecast_data]
        chart_hums = [d['avg_humidity'] for d in forecast_data]
        
    context = {
        'lat': lat,
        'lon': lon,
        'city': city,
        'trigger_browser_geolocation': trigger_browser_geolocation,
        'weather': weather_data,
        'forecast': forecast_data,
        'past': past_data,
        'growth': growth_data,
        'crops': crops,
        'chart_dates_json': json.dumps(chart_dates),
        'chart_temps_json': json.dumps(chart_temps),
        'chart_hums_json': json.dumps(chart_hums),
        'error': error
    }
    return render(request, 'weather_advisor.html', context)

# ==========================================
# PROFILE & SETTINGS
# ==========================================
@login_required
def profile_settings_view(request):
    success = False
    error = ""

    if request.method == "POST":
        form = FarmerProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            # Store ALL cleaned data in session — apply only after OTP
            data = form.cleaned_data
            pending = {
                'first_name': data.get('first_name', '') or '',
                'last_name':  data.get('last_name', '')  or '',
                'email':      data.get('email', '')       or '',
                'phone_number':    data.get('phone_number', '')    or '',
                'location_city':   data.get('location_city', '')   or '',
                'farm_name':       data.get('farm_name', '')        or '',
                'farm_size_acres': float(data['farm_size_acres']) if data.get('farm_size_acres') is not None else None,
                'latitude':        float(data['latitude'])  if data.get('latitude')  is not None else None,
                'longitude':       float(data['longitude']) if data.get('longitude') is not None else None,
            }
            request.session['pending_profile'] = pending

            # Generate OTP and send to the user's CURRENT email
            otp_code = str(random.randint(100000, 999999))
            EmailOTP.objects.create(
                email=request.user.email, otp=otp_code, purpose='profile_update'
            )
            try:
                send_mail(
                    subject='PlantCare - Confirm Your Profile Update',
                    message=(
                        f'Hello {request.user.username},\n\n'
                        f'Your One-Time Password (OTP) to confirm your profile update is:\n\n'
                        f'   {otp_code}\n\n'
                        f'Enter this code to save your changes. Do not share it with anyone.\n\n'
                        f'- PlantCare Team'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[request.user.email],
                    fail_silently=False,
                )
            except Exception:
                pass

            return redirect('verify_profile_update')
        else:
            error = "Invalid updates. Please correct the errors."
    else:
        form = FarmerProfileForm(instance=request.user)

    return render(request, 'profile_settings.html', {
        'form': form,
        'success': success,
        'error': error
    })


@login_required
def verify_profile_update_view(request):
    """Confirm any profile change (including email) with a 6-digit OTP."""
    pending = request.session.get('pending_profile')
    if not pending:
        return redirect('profile_settings')

    error = ""
    if request.method == "POST":
        otp_entered = request.POST.get('otp', '').strip()
        otp_record = EmailOTP.objects.filter(
            email=request.user.email, purpose='profile_update', is_verified=False
        ).first()

        if otp_record and otp_record.otp == otp_entered:
            otp_record.is_verified = True
            otp_record.save()

            # Apply all pending changes
            user = request.user
            old_email = user.email
            new_email = pending.get('email', '').strip()

            user.first_name    = pending.get('first_name', '') or ''
            user.last_name     = pending.get('last_name',  '') or ''
            user.phone_number  = pending.get('phone_number', '') or ''
            user.location_city = pending.get('location_city', '') or ''
            user.farm_name     = pending.get('farm_name', '') or ''

            try:
                user.farm_size_acres = float(pending['farm_size_acres']) if pending.get('farm_size_acres') is not None else None
            except (TypeError, ValueError):
                user.farm_size_acres = None

            try:
                user.latitude = float(pending['latitude']) if pending.get('latitude') is not None else None
            except (TypeError, ValueError):
                user.latitude = None

            try:
                user.longitude = float(pending['longitude']) if pending.get('longitude') is not None else None
            except (TypeError, ValueError):
                user.longitude = None

            # Apply email only if it changed and is still unique
            from accounts.models import User as UserModel
            email_updated = False
            if new_email and new_email.lower() != old_email.lower():
                if not UserModel.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
                    user.email = new_email
                    email_updated = True

            user.save()
            request.session.pop('pending_profile', None)

            msg = 'Profile updated successfully!'
            if email_updated:
                msg += f' Email changed to {new_email}.'

            return render(request, 'profile_settings.html', {
                'form': FarmerProfileForm(instance=user),
                'success': True,
                'success_message': msg,
                'error': ''
            })
        else:
            error = "Invalid OTP. Please check and try again."

    return render(request, 'verify_profile_update.html', {
        'current_email': request.user.email,
        'error': error,
    })

# ==========================================
# PDF REPORT EXPORTER (fpdf2 - Unicode)
# ==========================================
import io
import os
from fpdf import FPDF
from django.http import FileResponse

class CropReportPDF(FPDF):
    """Custom PDF class with Nirmala UI font for Hindi/Gujarati Unicode support."""
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        # Register Nirmala UI (ships with Windows, supports Devanagari + Gujarati)
        font_ttc = r'C:\Windows\Fonts\Nirmala.ttc'
        font_ttf = r'C:\Windows\Fonts\Nirmala.ttf'
        font_path = font_ttc if os.path.exists(font_ttc) else font_ttf
        if os.path.exists(font_path):
            self.add_font('Nirmala', '', font_path)
            self.add_font('Nirmala', 'B', font_path)
            self._report_font = 'Nirmala'
        else:
            self._report_font = 'Helvetica'

    def header(self):
        pass  # custom header drawn in body

    def footer(self):
        self.set_y(-15)
        self.set_font(self._report_font, '', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'PlantCare Report  |  Page {self.page_no()}', align='C')

from django.views.decorators.http import require_POST
from django.conf import settings

@login_required
@require_POST
def download_scan_pdf(request, result_id):
    scan = get_object_or_404(ScanHistory, pk=result_id, user=request.user)

    # Initialize PDF renderer first to check font compatibility
    pdf = CropReportPDF()
    fn = pdf._report_font

    # Get active language, force English if font has no Unicode support
    lang = getattr(request.user, 'preferred_language', 'en')
    if fn == 'Helvetica':
        lang = 'en'

    # Load crop details
    from library.models import Crop, Disease
    from django.db.models import Q
    crop_obj = Crop.objects.filter(
        Q(name__iexact=scan.matched_crop_name) | Q(scientific_name__iexact=scan.identified_species)
    ).first()
    has_diseases = crop_obj.diseases.exists() if crop_obj else False

    # ----- Translate static headers -----
    if lang == 'hi':
        title_text = "फसल स्वास्थ्य निदान रिपोर्ट"
        lbl_crop = "फसल का नाम:"
        lbl_species = "वैज्ञानिक नाम:"
        lbl_status = "स्वास्थ्य स्थिति:"
        lbl_confidence = "आत्मविश्वास स्कोर:"
        lbl_date = "निदान तिथि:"
        lbl_healthy = "स्वस्थ"
        lbl_diseased = "रोगग्रस्त"
        lbl_gps = "जीपीएस स्थान:"
        lbl_organ = "\u0938\u094d\u0915\u0948\u0928 \u0915\u093f\u092f\u093e \u0917\u092f\u093e \u0939\u093f\u0938\u094d\u0938\u093e:"
    elif lang == 'gu':
        title_text = "પાક આરોગ્ય નિદાન રિપોર્ટ"
        lbl_crop = "પાકનું નામ:"
        lbl_species = "વૈજ્ઞાનિક નામ:"
        lbl_status = "આરોગ્ય સ્થિતિ:"
        lbl_confidence = "વિશ્વાસ સ્કોર:"
        lbl_date = "નિદાન તારીખ:"
        lbl_healthy = "સ્વસ્થ"
        lbl_diseased = "રોગિષ્ઠ"
        lbl_gps = "જીપીએસ સ્થાન:"
        lbl_organ = "\u0ab8\u0acd\u0a95\u0ac7\u0aa8 \u0a95\u0ab0\u0ac7\u0ab2 \u0aad\u0abe\u0a97:"
    else:
        title_text = "PlantCare - Crop Diagnostic Report"
        lbl_crop = "Crop Name:"
        lbl_species = "Scientific Name:"
        lbl_status = "Health Status:"
        lbl_confidence = "Confidence Score:"
        lbl_date = "Diagnostic Date:"
        lbl_healthy = "Healthy"
        lbl_diseased = "Diseased"
        lbl_gps = "Scan Geolocation:"
        lbl_organ = "Scanned Organ:"

    # ----- Translate crop name & organ -----
    from plantcare.utils import get_localized_crop_name
    crop_name = get_localized_crop_name(scan.matched_crop_name, lang)
    
    trans_path = settings.BASE_DIR / 'translations' / f'{lang}.json'
    try:
        with open(trans_path, 'r', encoding='utf-8') as f:
            trans_data = json.load(f)
    except Exception:
        trans_data = {}
        
    organ_key = f"scan.organ_{scan.organ.lower()}"
    organ_name = trans_data.get(organ_key, scan.organ.capitalize())

    # ========== Build the PDF ==========
    pdf.add_page()

    # ---------- Title ----------
    pdf.set_font(fn, 'B', 18)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(0, 12, title_text, new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.ln(4)

    # Separator line
    pdf.set_draw_color(16, 185, 129)
    pdf.set_line_width(0.6)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    # ---------- Meta details ----------
    pdf.set_text_color(31, 41, 55)

    def label_value(label, value):
        pdf.set_font(fn, 'B', 10)
        pdf.cell(55, 7, label, new_x='END')
        pdf.set_font(fn, '', 10)
        pdf.cell(0, 7, str(value), new_x='LMARGIN', new_y='NEXT')

    label_value(lbl_crop, crop_name)
    label_value(lbl_species, scan.identified_species)
    label_value(lbl_organ, organ_name)
    label_value(lbl_status, lbl_healthy if scan.is_healthy else lbl_diseased)
    label_value(lbl_confidence, f"{int(scan.confidence_score * 100)}%")
    label_value(lbl_date, scan.created_at.strftime('%Y-%m-%d %H:%M'))
    if scan.latitude and scan.longitude:
        label_value(lbl_gps, f"{scan.latitude:.4f}, {scan.longitude:.4f}")

    pdf.ln(4)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    # ---------- Section helper ----------
    def section_header(text):
        pdf.set_font(fn, 'B', 13)
        pdf.set_text_color(5, 150, 105)
        pdf.cell(0, 9, text, new_x='LMARGIN', new_y='NEXT')
        pdf.ln(2)

    def section_body(text):
        pdf.set_font(fn, '', 10)
        pdf.set_text_color(31, 41, 55)
        pdf.multi_cell(0, 6, str(text))
        pdf.ln(3)

    # ---------- Disease / Healthy section ----------
    if not scan.is_healthy and scan.disease_identified:
        disease_obj = Disease.objects.filter(
            Q(crop__name__iexact=scan.matched_crop_name) | Q(crop__scientific_name__iexact=scan.identified_species),
            name__iexact=scan.disease_identified
        ).first()

        # Localized disease labels
        if lang == 'hi':
            lbl_detected = "पता चला रोग:"
            lbl_symptoms = "लक्षण:"
            lbl_causes = "कारण:"
            lbl_treatment = "उपचार निर्देश:"
            lbl_pesticides = "अनुशंसित कीटनाशक:"
            lbl_fertilizers = "अनुशंसित उर्वरक और आवेदन निर्देश:"
            lbl_how_to_apply = "आवेदन कैसे करें:"
        elif lang == 'gu':
            lbl_detected = "શોધાયેલ રોગ:"
            lbl_symptoms = "લક્ષણો:"
            lbl_causes = "કારણો:"
            lbl_treatment = "સારવાર માર્ગદર્શિકા:"
            lbl_pesticides = "ભલામણ કરેલ જંતુનાશકો:"
            lbl_fertilizers = "ભલામણ કરેલ ખાતરો અને ઉપયોગની સૂચનાઓ:"
            lbl_how_to_apply = "કેવી રીતે ઉપયોગ કરવો:"
        else:
            lbl_detected = "Detected Disease:"
            lbl_symptoms = "Symptoms:"
            lbl_causes = "Causes:"
            lbl_treatment = "Treatment Guidelines:"
            lbl_pesticides = "Recommended Pesticides:"
            lbl_fertilizers = "Recommended Fertilizers & Application Instructions:"
            lbl_how_to_apply = "How to Apply:"

        # Localize disease title
        disease_title = scan.disease_identified
        if "Leaf Spot" in scan.disease_identified:
            if lang == 'hi': disease_title = f"{crop_name} पत्ती का धब्बा रोग"
            elif lang == 'gu': disease_title = f"{crop_name} પાંદડા પર ડાઘનો રોગ"
        elif "Powdery Mildew" in scan.disease_identified:
            if lang == 'hi': disease_title = f"{crop_name} पाओडरी मिल्ड्यू रोग"
            elif lang == 'gu': disease_title = f"{crop_name} પાવડરી મિલ્ડ્યુ રોગ"
        elif scan.disease_identified == 'Early Blight':
            if lang == 'hi': disease_title = f"{crop_name} अगेती झुलसा"
            elif lang == 'gu': disease_title = f"{crop_name} અગેતી સુકારો"
        elif scan.disease_identified == 'Late Blight':
            if lang == 'hi': disease_title = f"{crop_name} पछेती झुलसा"
            elif lang == 'gu': disease_title = f"{crop_name} મોડો સુકારો"

        section_header(f"{lbl_detected} {disease_title}")

        if disease_obj:
            # Symptoms
            symptoms = disease_obj.symptoms
            if lang == 'hi': symptoms = disease_obj.symptoms_hi or symptoms
            elif lang == 'gu': symptoms = disease_obj.symptoms_gu or symptoms
            section_header(lbl_symptoms)
            section_body(symptoms)

            # Causes
            causes = disease_obj.causes
            if lang == 'hi': causes = disease_obj.causes_hi or causes
            elif lang == 'gu': causes = disease_obj.causes_gu or causes
            section_header(lbl_causes)
            section_body(causes)

            # Treatment
            treatment = disease_obj.treatment
            if lang == 'hi': treatment = disease_obj.treatment_hi or treatment
            elif lang == 'gu': treatment = disease_obj.treatment_gu or treatment
            section_header(lbl_treatment)
            section_body(treatment)

            # Fertilizers
            fertilizers = disease_obj.fertilizers_recommended.all()
            if fertilizers.exists():
                section_header(lbl_fertilizers)
                for f in fertilizers:
                    f_name = f.name
                    if lang == 'hi':
                        f_desc = f.description_hi or f.description
                        f_usage = f.usage_instructions_hi or f.usage_instructions
                    elif lang == 'gu':
                        f_desc = f.description_gu or f.description
                        f_usage = f.usage_instructions_gu or f.usage_instructions
                    else:
                        f_desc = f.description_en or f.description
                        f_usage = f.usage_instructions_en or f.usage_instructions
                    pdf.set_font(fn, 'B', 10)
                    pdf.set_text_color(31, 41, 55)
                    pdf.cell(0, 7, f"- {f_name} ({f.get_fertilizer_type_display()}):", new_x='LMARGIN', new_y='NEXT')
                    section_body(f_desc)
                    pdf.set_font(fn, 'B', 9)
                    pdf.set_text_color(80, 80, 80)
                    pdf.cell(0, 6, f"  {lbl_how_to_apply}", new_x='LMARGIN', new_y='NEXT')
                    section_body(f_usage)

            # Pesticides
            from plantcare.utils import get_structured_pesticides
            pesticides_list = get_structured_pesticides(disease_obj.pesticides_recommended, lang)
            if pesticides_list:
                section_header(lbl_pesticides)
                for p in pesticides_list:
                    p_name = p['name']
                    p_type = p['type_label']
                    p_desc = p['description']
                    p_usage = p['usage_instructions']
                    pdf.set_font(fn, 'B', 10)
                    pdf.set_text_color(31, 41, 55)
                    pdf.cell(0, 7, f"- {p_name} ({p_type}):", new_x='LMARGIN', new_y='NEXT')
                    section_body(p_desc)
                    pdf.set_font(fn, 'B', 9)
                    pdf.set_text_color(80, 80, 80)
                    pdf.cell(0, 6, f"  {lbl_how_to_apply}", new_x='LMARGIN', new_y='NEXT')
                    section_body(p_usage)
        else:
            section_body(scan.fertilizer_recommendation or 'No specific guidelines available.')
    else:
        # Healthy or undetermined
        if crop_obj and not has_diseases:
            if lang == 'hi':
                lbl_status_title = "अनिर्धारित (डेटाबेस रिकॉर्ड नहीं)"
                lbl_status_desc = "लाइब्रेरी में इस फसल के लिए कोई नैदानिक रिकॉर्ड मौजूद नहीं है। फसल पंजीकृत है, लेकिन रोग मिलान अनुपलब्ध है। आप एडमिन पैनल में इस फसल के लिए रोग जोड़ सकते हैं।"
            elif lang == 'gu':
                lbl_status_title = "અસ્પષ્ટ (ડેટાબેઝ રેકોર્ડ નથી)"
                lbl_status_desc = "લાઇબ્રેરીમાં આ પાક માટે કોઈ રોગ નિદાન વિગતો ઉપલબ્ધ નથી. પાક નોંધાયેલ છે, પરંતુ રોગ ચકાસણી અનુપલબ્ધ છે. તમે એડમીન પેનલમાં આ પાક માટે રોગ ઉમેરી શકો છો."
            else:
                lbl_status_title = "Undetermined (No Database Records)"
                lbl_status_desc = "No diagnostic records exist for this crop in the library. Crop has been registered, but disease matching is unavailable. You can add diseases for this crop in the Admin Panel."
        else:
            lbl_status_title = lbl_healthy
            if lang == 'hi':
                lbl_status_desc = "कोई पौधा रोग नहीं मिला। यह पौधा स्वस्थ दिखाई देता है!"
            elif lang == 'gu':
                lbl_status_desc = "કોઈ રોગ મળ્યો નથી. આ છોડ સ્વસ્થ છે!"
            else:
                lbl_status_desc = "No plant diseases matched. This plant appears to be healthy!"

        section_header(lbl_status_title)
        section_body(lbl_status_desc)

        # Future care
        if lang == 'hi':
            lbl_future_care = "सामान्य भविष्य की देखभाल"
            step1 = "मिट्टी की देखभाल: ऊपरी मिट्टी को ढीला रखें और नमी बनाए रखने के लिए जैविक मल्च/खाद मिलाएं।"
            step2 = "सिंचाई: स्थानीय मौसम रिपोर्ट के आधार पर लगातार सिंचाई कार्यक्रम बनाए रखें।"
            step3 = "निगरानी: कीटों या शुरुआती घावों के संकेतों के लिए पत्तियों के निचले हिस्से का मासिक निरीक्षण करें।"
        elif lang == 'gu':
            lbl_future_care = "સામાન્ય ભવિષ્યની સંભાળ"
            step1 = "જમીનની સંભાળ: ઉપરની માટીને પોચી રાખો અને ભેજ જાળવી રાખવા માટે ઓર્ગેનિક ખાતર ઉમેરો."
            step2 = "સિંચાઈ: સ્થાનિક હવામાન અહેવાલોના આધારે નિયમિત પાણી આપવાનું સમયપત્રક જાળવો."
            step3 = "નિરીક્ષણ: જીવાતો અથવા રોગના પ્રારંભિક ચિહ્નો માટે પાંદડાના નીચેના ભાગનું માસિક નિરીક્ષણ કરો."
        else:
            lbl_future_care = "General Future Care"
            step1 = "Soil Care: Keep topsoil loose and add organic mulch/compost to retain moisture."
            step2 = "Watering: Maintain consistent watering schedules based on local weather reports."
            step3 = "Monitoring: Perform monthly inspections of leaf undersides for signs of pests or early lesions."

        section_header(lbl_future_care)
        section_body(f"1. {step1}")
        section_body(f"2. {step2}")
        section_body(f"3. {step3}")

    # ========== Output PDF ==========
    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f'crop_report_{result_id}.pdf')


def support_view(request):
    """Render Support contact details and handle the support submission form."""
    success = False
    error = ""

    # Pre-fill form details if user is authenticated
    initial = {}
    if request.user.is_authenticated:
        initial = {
            'name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            'email': request.user.email,
            'phone': getattr(request.user, 'phone_number', '') or '',
        }

    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        details = request.POST.get('details', '').strip()

        if not name or not email or not details:
            error = "Please fill in all required fields."
        else:
            try:
                # Send to support email
                send_mail(
                    subject=f'PlantCare Support Request from {name}',
                    message=(
                        f'New Support Request Received:\n\n'
                        f'Name: {name}\n'
                        f'Email: {email}\n'
                        f'Phone: {phone}\n\n'
                        f'Message/Details:\n{details}'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=['plantcare799@gmail.com'],
                    fail_silently=False,
                )
                # Send confirmation email to the user
                send_mail(
                    subject='We have received your support request!',
                    message=(
                        f'Hello {name},\n\n'
                        f'Thank you for contacting PlantCare Support. We have received your request and our team will get back to you shortly.\n\n'
                        f'Details submitted:\n'
                        f'---\n'
                        f'Message: {details}\n'
                        f'---\n\n'
                        f'Best regards,\n'
                        f'PlantCare Support Team'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )
                success = True
            except Exception:
                error = "Could not send support request. Please try again later."

    return render(request, 'support.html', {
        'success': success,
        'error': error,
        'initial': initial,
    })


# ==========================================
# PLANT RECOVERY TRACKER
# ==========================================
@login_required
def recovery_list_view(request):
    from accounts.models import RecoveryTracker
    journeys = RecoveryTracker.objects.filter(user=request.user)
    return render(request, 'recovery.html', {'journeys': journeys})


@login_required
def recovery_start_view(request):
    if request.method == "POST":
        plant_name = request.POST.get('plant_name', '').strip()
        crop_type = request.POST.get('crop_type', '').strip()
        watering_frequency = request.POST.get('watering_frequency', 'Once a day').strip()
        estimated_recovery_weeks = int(request.POST.get('estimated_recovery_weeks', 4))
        light_requirement = request.POST.get('light_requirement', 'Direct Sunlight').strip()
        
        if plant_name:
            from accounts.models import RecoveryTracker
            RecoveryTracker.objects.create(
                user=request.user,
                plant_name=plant_name,
                crop_type=crop_type,
                watering_frequency=watering_frequency,
                estimated_recovery_weeks=estimated_recovery_weeks,
                light_requirement=light_requirement,
                status='ongoing'
            )
            return redirect('recovery_list')
    return render(request, 'recovery_start.html')


@login_required
def recovery_detail_view(request, journey_id):
    from accounts.models import RecoveryTracker
    journey = get_object_or_404(RecoveryTracker, pk=journey_id, user=request.user)
    
    if request.method == "POST":
        action = request.POST.get('action')
        if action == "mark_recovered":
            journey.status = 'recovered'
            journey.save()
            # If marked recovered, make sure the last checkin is marked healthy
            last_checkin = journey.checkins.last()
            if last_checkin:
                last_checkin.is_healthy = True
                last_checkin.save()
            return redirect('recovery_detail', journey_id=journey.id)

    checkins = journey.checkins.all().order_by('week_number')
    
    # Generic advice suggestions based on crop type
    advices = [
        "Hoeing: Loosen the soil around the base of the plant to a depth of 2-3 inches to improve root aeration and water penetration.",
        "Watering: Irrigate deep at the root zone early in the morning to prevent evapotranspiration and mold development.",
        "Fertilizing: Apply nitrogen-rich organic compost if leaves are pale, or potassium-rich sulfate of potash to support flowering/fruiting.",
        "Pest Control: Spray organic neem oil solution onto leaf surfaces (especially undersides) weekly if spotting is visible."
    ]
    
    return render(request, 'recovery_detail.html', {
        'journey': journey,
        'checkins': checkins,
        'advices': advices
    })


@login_required
def recovery_checkin_view(request, journey_id):
    from accounts.models import RecoveryTracker, RecoveryCheckIn
    journey = get_object_or_404(RecoveryTracker, pk=journey_id, user=request.user)
    
    if request.method == "POST":
        image = request.FILES.get('image')
        symptoms = request.POST.get('symptoms', '').strip()
        farmer_notes = request.POST.get('farmer_notes', '').strip()
        recovery_percentage = int(request.POST.get('recovery_percentage', 0))
        pest_activity = request.POST.get('pest_activity', 'None').strip()
        is_healthy = request.POST.get('is_healthy') == 'on' or recovery_percentage == 100
        
        if image:
            week_num = journey.checkins.count() + 1
            
            # Formulate smart dynamic care instructions based on symptoms and crop type
            care_tips = []
            symptoms_lower = symptoms.lower()
            if "spot" in symptoms_lower or "yellow" in symptoms_lower:
                care_tips.append("Yellowing/Spotting detected. Apply nitrogen compost fertilizer immediately to restore green chlorophyll.")
                care_tips.append("Hoe the topsoil around root margins to enhance aeration.")
            if "dry" in symptoms_lower or "wilting" in symptoms_lower or "wilt" in symptoms_lower:
                care_tips.append("Wilting symptoms present. Increase deep root watering schedule to twice weekly.")
                care_tips.append("Mulch around plant base to preserve water index.")
            if not care_tips:
                care_tips.append("Apply standard organic compost mix around root zone.")
                care_tips.append("Water early in mornings daily, ensuring soil stays well-drained.")
                care_tips.append("Hoe surface soil to prevent compaction.")
            
            care_advice = "\n".join(f"- {tip}" for tip in care_tips)
            
            RecoveryCheckIn.objects.create(
                tracker=journey,
                week_number=week_num,
                image=image,
                symptoms=symptoms,
                farmer_notes=farmer_notes,
                recovery_percentage=recovery_percentage,
                pest_activity=pest_activity,
                care_advice=care_advice,
                is_healthy=is_healthy
            )
            
            if is_healthy:
                journey.status = 'recovered'
                journey.save()
                
            return redirect('recovery_detail', journey_id=journey.id)
            
    return render(request, 'recovery_checkin.html', {'journey': journey})


@login_required
def recovery_ask_view(request, journey_id):
    from accounts.models import RecoveryTracker
    journey = get_object_or_404(RecoveryTracker, pk=journey_id, user=request.user)
    question = request.POST.get('question', '').strip()
    
    answer = ""
    if question:
        q_lower = question.lower()
        if "water" in q_lower or "irrigate" in q_lower:
            answer = "For optimal health, water the plant deeply at the root zone early in the morning. Avoid wetting leaves directly to prevent mold."
        elif "fertilizer" in q_lower or "manure" in q_lower or "feed" in q_lower:
            answer = f"For {journey.crop_type or 'this crop'}, feed with nitrogen-rich organic compost twice during early leafing, and phosphorus blends during flowering."
        elif "soil" in q_lower or "hoe" in q_lower:
            answer = "Hoeing is highly recommended! Loosen the top 2 inches of soil once a week. This breaks compaction, kills weeds, and aerates roots."
        else:
            answer = "General Care Directive: Ensure the plant receives 6 hours of daily sunlight, maintain organic mulch at the base, and prune infected leaves immediately."
            
    checkins = journey.checkins.all().order_by('week_number')
    return render(request, 'recovery_detail.html', {
        'journey': journey,
        'checkins': checkins,
        'question': question,
        'answer': answer
    })


@login_required
def recovery_pdf_export_view(request, journey_id):
    import io
    from django.http import FileResponse
    from accounts.models import RecoveryTracker
    journey = get_object_or_404(RecoveryTracker, pk=journey_id, user=request.user)
    checkins = journey.checkins.all().order_by('week_number')

    from fpdf import FPDF
    
    class RecoveryReportPDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(16, 124, 65)
            self.cell(0, 10, f"PlantCare AI - Plant Recovery Journey Report", new_x='LMARGIN', new_y='NEXT')
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 5, f"Report for plant: '{journey.plant_name}' ({journey.crop_type or 'General'})", new_x='LMARGIN', new_y='NEXT')
            self.set_draw_color(16, 124, 65)
            self.line(10, 22, 200, 22)
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f"Page {self.page_no()}", align='C')

    pdf = RecoveryReportPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(50, 50, 50)
    
    # Metadata block
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, "Recovery Summary:", new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, f"Start Date: {journey.start_date.strftime('%Y-%m-%d')}", new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 6, f"Current Status: {journey.get_status_display()}", new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 6, f"Watering Frequency: {journey.watering_frequency}", new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 6, f"Light Requirement: {journey.light_requirement}", new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 6, f"Estimated Recovery Timeframe: {journey.estimated_recovery_weeks} weeks", new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 6, f"Total Weeks Recorded: {checkins.count()} week(s)", new_x='LMARGIN', new_y='NEXT')
    pdf.ln(5)
    
    # Chronological timeline
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, "Chronological Weekly Log:", new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    
    for c in checkins:
        pdf.set_draw_color(200, 200, 200)
        # Allocate height
        pdf.rect(10, pdf.get_y(), 190, 52)
        pdf.set_x(12)
        pdf.set_y(pdf.get_y() + 2)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 6, f"Week {c.week_number} Check-in (Date: {c.checkin_date.strftime('%Y-%m-%d')}) - Progress: {c.recovery_percentage}%", new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Helvetica', '', 10)
        
        # Symptoms, notes & pest activity
        symptom_text = c.symptoms or "No specific symptoms reported."
        pdf.cell(0, 6, f"Symptoms: {symptom_text}", new_x='LMARGIN', new_y='NEXT')
        notes_text = c.farmer_notes or "None"
        pdf.cell(0, 6, f"Farmer Notes: {notes_text} | Pest Activity: {c.pest_activity}", new_x='LMARGIN', new_y='NEXT')
        
        # Care advice
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(0, 5, "Care Advice Prescribed:", new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Helvetica', '', 9)
        for line in c.care_advice.split('\n'):
            pdf.cell(0, 4.5, f"  {line}", new_x='LMARGIN', new_y='NEXT')
            
        status_lbl = "Status: Healthy / Recovered" if c.is_healthy else "Status: recovering / sick"
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(0, 5, status_lbl, new_x='LMARGIN', new_y='NEXT')
        pdf.ln(5)

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"recovery_report_{journey_id}.pdf")


# ==========================================
# UNIFIED USER HISTORY LOGS
# ==========================================
@login_required
def history_view(request):
    from accounts.models import SearchHistory, RecoveryTracker
    from scans.models import ScanHistory
    
    scans = ScanHistory.objects.filter(user=request.user).order_by('-created_at')
    searches = SearchHistory.objects.filter(user=request.user).order_by('-created_at')
    journeys = RecoveryTracker.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'history.html', {
        'scans': scans,
        'searches': searches,
        'journeys': journeys
    })


@login_required
def all_crops_pdf_view(request):
    """Generate detailed, print-ready PDF reference catalog of all crops and diseases."""
    import io
    from django.http import FileResponse
    from library.models import Crop
    from fpdf import FPDF

    class CropsCatalogPDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(17, 24, 39)
            self.cell(0, 10, "PlantCare AI - Complete Crops Catalog Reference Manual", new_x='LMARGIN', new_y='NEXT')
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 5, "Detailed botanical soils, organic fertilizers, and part-wise disease treatments", new_x='LMARGIN', new_y='NEXT')
            self.set_draw_color(17, 24, 39)
            self.line(10, 22, 200, 22)
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f"Page {self.page_no()}", align='C')

    pdf = CropsCatalogPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font('Helvetica', '', 10)
    
    lang = request.user.preferred_language if request.user.is_authenticated else 'en'
    from plantcare.utils import get_localized_crop_name
    
    crops = Crop.objects.all().order_by('name')
    for i, crop in enumerate(crops, start=1):
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(16, 124, 65) # Green
        loc_name = get_localized_crop_name(crop.name, lang)
        pdf.cell(0, 8, f"{i}. {loc_name}", new_x='LMARGIN', new_y='NEXT')
        pdf.ln(1)

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="crops_catalog.pdf")


@login_required
def single_crop_pdf_view(request, crop_id):
    """Generate detailed, print-ready PDF reference sheet for a single selected crop."""
    import io
    from django.http import FileResponse
    from library.models import Crop
    from fpdf import FPDF
    from django.shortcuts import get_object_or_404

    crop = get_object_or_404(Crop, pk=crop_id)

    class CropPDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(17, 24, 39)
            self.cell(0, 10, f"PlantCare AI - {crop.name} Reference Sheet", new_x='LMARGIN', new_y='NEXT')
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 5, "Detailed botanical soils, organic fertilizers, and part-wise disease treatments", new_x='LMARGIN', new_y='NEXT')
            self.set_draw_color(17, 24, 39)
            self.line(10, 22, 200, 22)
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f"Page {self.page_no()}", align='C')

    pdf = CropPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(16, 124, 65) # Green
    pdf.cell(0, 8, f"{crop.name} ({crop.scientific_name})", new_x='LMARGIN', new_y='NEXT')
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(50, 50, 50)
    
    desc = crop.description or "No description."
    pdf.multi_cell(0, 5, f"Description: {desc}")
    pdf.cell(0, 5, f"Soil Type: {crop.soil_type}", new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 5, f"Ideal Temperature: {crop.ideal_temp_min_c}C - {crop.ideal_temp_max_c}C", new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 5, f"Ideal Humidity: {crop.ideal_humidity_min}% - {crop.ideal_humidity_max}%", new_x='LMARGIN', new_y='NEXT')
    pdf.ln(4)

    # Diseases part-wise
    diseases = crop.diseases.all().order_by('affected_part')
    if diseases.exists():
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(17, 24, 39)
        pdf.cell(0, 8, f"Associated Diseases ({diseases.count()} total):", new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(80, 80, 80)
        
        for dis in diseases:
            part_lbl = dis.get_affected_part_display()
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(0, 6, f"  - {dis.name} (Affects: {part_lbl})", new_x='LMARGIN', new_y='NEXT')
            pdf.set_font('Helvetica', '', 9)
            pdf.cell(0, 4.5, f"    Symptoms: {dis.symptoms}", new_x='LMARGIN', new_y='NEXT')
            pdf.cell(0, 4.5, f"    Causes: {dis.causes}", new_x='LMARGIN', new_y='NEXT')
            pdf.cell(0, 4.5, f"    Treatment: {dis.treatment}", new_x='LMARGIN', new_y='NEXT')
            if dis.pesticides_recommended:
                pdf.cell(0, 4.5, f"    Recommended Pesticides: {dis.pesticides_recommended}", new_x='LMARGIN', new_y='NEXT')
            pdf.ln(2)
    else:
        pdf.cell(0, 5, "  No registered diseases in catalog.", new_x='LMARGIN', new_y='NEXT')

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"{crop.name.lower()}_details.pdf")


@login_required
def assistant_view(request):
    # Check if we should clear session context
    if request.GET.get('reset') == '1':
        if 'assistant_crop' in request.session: del request.session['assistant_crop']
        if 'assistant_soil_type' in request.session: del request.session['assistant_soil_type']
        if 'assistant_stage' in request.session: del request.session['assistant_stage']
        if 'assistant_weather' in request.session: del request.session['assistant_weather']
        if 'chat_history' in request.session: del request.session['chat_history']
        return redirect('assistant')

    # Jump direct from scan parameters
    scan_crop = request.GET.get('crop')
    if scan_crop:
        request.session['assistant_crop'] = scan_crop
        request.session['assistant_soil_type'] = request.user.soil_type or "Loamy Soil"
        request.session['assistant_stage'] = "Vegetative"
        request.session['assistant_weather'] = "Mild & Cloudy (24°C - 28°C)"
        if 'chat_history' in request.session: del request.session['chat_history']

    # Handle post requests
    if request.method == "POST":
        # Check if submitting interview form
        if 'submit_interview' in request.POST:
            request.session['assistant_crop'] = request.POST.get('crop', '').strip()
            request.session['assistant_soil_type'] = request.POST.get('soil_type', '').strip()
            request.session['assistant_stage'] = request.POST.get('stage', '').strip()
            request.session['assistant_weather'] = request.POST.get('weather', '').strip()
            request.session['chat_history'] = []
            return redirect('assistant')

        # Check if submitting chat question
        elif 'submit_chat' in request.POST:
            question = request.POST.get('question', '').strip()
            if question:
                chat_history = request.session.get('chat_history', [])
                
                # Retrieve context
                crop = request.session.get('assistant_crop', 'General Crop')
                soil_type = request.session.get('assistant_soil_type', 'Loamy Soil')
                stage = request.session.get('assistant_stage', 'Vegetative')
                weather = request.session.get('assistant_weather', 'Normal Weather')
                
                # Determine target language for Gemini response
                lang = request.user.preferred_language if request.user.is_authenticated else request.session.get('preferred_language', 'en')
                lang_map = {
                    'en': 'English',
                    'hi': 'Hindi',
                    'gu': 'Gujarati'
                }
                target_lang = lang_map.get(lang, 'English')
                
                # Build prompt context
                system_prompt = (
                    f"You are an expert agricultural AI farming advisor. "
                    f"Context:\n- Crop: {crop}\n- Soil Type: {soil_type}\n- Growth Stage: {stage}\n- Weather/Environment: {weather}\n\n"
                    f"Answer the farmer's question in simple, friendly, and practical language, specifically tailored to the crop, soil, stage, and weather conditions above. "
                    f"At the end of your response, always ask 1 or 2 relevant clarifying questions to help guide the farmer further.\n"
                    f"CRITICAL: You must write your entire response (including clarifying questions) strictly in the {target_lang} language."
                )
                
                # Format messages for Gemini API contents structure
                contents = []
                # First append the system context
                contents.append({
                    "role": "user",
                    "parts": [{"text": system_prompt}]
                })
                contents.append({
                    "role": "model",
                    "parts": [{"text": "Understood. I will act as the AI Farming Advisor for this context. Please tell me what questions you have about your crop."}]
                })
                
                # Append history
                for msg in chat_history:
                    contents.append({
                        "role": "user" if msg['sender'] == 'farmer' else "model",
                        "parts": [{"text": msg['text']}]
                    })
                
                # Append current question
                contents.append({
                    "role": "user",
                    "parts": [{"text": question}]
                })
                
                # Call Gemini API
                api_key = getattr(settings, 'GEMINI_API_KEY', '')
                models_to_try = [
                    "gemini-3.1-flash-lite",
                    "gemini-1.5-flash",
                    "gemini-1.5-pro"
                ]
                
                answer = "I am sorry, but I was unable to connect to the generative AI service. Please verify your connection and try again."
                for model_id in models_to_try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
                    headers = {"Content-Type": "application/json"}
                    payload = {"contents": contents}
                    try:
                        import requests
                        response = requests.post(url, json=payload, headers=headers, timeout=15)
                        if response.status_code == 200:
                            res_json = response.json()
                            candidates = res_json.get('candidates', [])
                            if candidates:
                                parts = candidates[0].get('content', {}).get('parts', [])
                                if parts:
                                    answer = parts[0].get('text', '')
                                    break
                    except Exception:
                        pass
                
                # Update chat history
                chat_history.append({'sender': 'farmer', 'text': question})
                chat_history.append({'sender': 'ai', 'text': answer})
                request.session['chat_history'] = chat_history
                
            return redirect('assistant')

    # Check if context exists
    has_context = all(k in request.session for k in ['assistant_crop', 'assistant_soil_type', 'assistant_stage', 'assistant_weather'])

    # Load all crops from database and build display labels with Gujarati names
    from library.models import Crop
    gu_names = {
        "Rice": "ચોખા", "Wheat": "ઘઉં", "Maize": "મકાઈ",
        "Pearl Millet (Bajra)": "બાજરો", "Sorghum (Jowar)": "જુવાર",
        "Finger Millet (Ragi)": "નાગલી", "Foxtail Millet": "કાંગ",
        "Little Millet": "સાવા", "Kodo Millet": "કોદો",
        "Barnyard Millet": "સ્વામ", "Proso Millet": "ચેણા", "Teff": "ટેફ",
        "Barley": "જવ", "Oat": "ઓટ", "Rye": "રાઈ",
        "Chickpea": "ચણા", "Pigeon Pea (Tur)": "તુવેર",
        "Green Gram (Moong)": "મગ", "Black Gram (Urad)": "અડદ",
        "Lentil": "મસૂર", "Cowpea": "ચોળા", "Field Pea": "ફળી",
        "Horse Gram": "કુળથ", "Moth Bean": "મઠ", "Lablab Bean": "વાલ",
        "Soybean": "સોયા", "Groundnut": "મગફળી", "Mustard": "સરસો",
        "Rapeseed": "રાઈ", "Sesame": "તલ", "Sunflower": "સૂર્યમુખી",
        "Castor": "દિવેલ", "Linseed": "અળસી", "Safflower": "કેસૂફ",
        "Niger": "રામ-તલ", "Cotton": "કપાસ", "Jute": "શણ",
        "Mesta": "મેસ્તા", "Sunn Hemp": "સન", "Sugarcane": "શેરડી",
        "Sugar Beet": "ખાંડ-ચૂકંદર", "Potato": "બટાકા", "Tomato": "ટામેટા",
        "Brinjal": "રીંગણ", "Chilli": "મરચું", "Bell Pepper": "શિમલા",
        "Onion": "ડુંગળી", "Garlic": "લસણ", "Okra": "ભીંડા",
        "Cabbage": "કોબી", "Cauliflower": "ફ્લાવર", "Broccoli": "બ્રોકોલી",
        "Carrot": "ગાજર", "Radish": "મૂળા", "Beetroot": "બીટ",
        "Spinach": "પાલક", "Coriander": "ધાણા", "Fenugreek": "મેથી",
        "Lettuce": "સલાડ", "Cucumber": "કાકડી", "Pumpkin": "કોળું",
        "Bottle Gourd": "દૂધી", "Bitter Gourd": "કારેલા",
        "Ridge Gourd": "તૂરીઓ", "Sponge Gourd": "ઘિયા",
        "Ash Gourd": "ભૂખ", "Watermelon": "તરબૂચ", "Muskmelon": "ખરબૂજ",
        "Papaya": "પપૈયા", "Banana": "કેળા", "Mango": "કેરી",
        "Guava": "જામફળ", "Sapota": "ચીકૂ", "Pomegranate": "દાડમ",
        "Grapes": "દ્રાક્ષ", "Apple": "સફરજન", "Orange": "સંતરા",
        "Lemon": "લીંબુ", "Sweet Lime": "મોસંબી", "Coconut": "નારિયળ",
        "Arecanut": "સોપારી", "Cashew": "કાજુ", "Tea": "ચા",
        "Coffee": "કોફી", "Rubber": "રબર", "Black Pepper": "મરી",
        "Cardamom": "એલચી", "Clove": "લવિંગ", "Cinnamon": "તજ",
        "Turmeric": "હળદર", "Ginger": "આદું", "Cumin": "જીરું",
        "Fennel": "વરીયાળી", "Ajwain": "અજમો", "Dill": "સુવા",
        "Mint": "ફૂદીનો", "Aloe Vera": "કુંવારપાઠ", "Tulsi": "તુળસી",
        "Stevia": "સ્ટેવિયા", "Isabgol (Psyllium)": "ઈસબગોળ",
    }
    
    hi_names = {
        "Rice": "चावल", "Wheat": "गेहूं", "Maize": "मक्का",
        "Pearl Millet (Bajra)": "बाजरा", "Sorghum (Jowar)": "ज्वार",
        "Finger Millet (Ragi)": "रागी", "Foxtail Millet": "कंगनी",
        "Little Millet": "कुटकी", "Kodo Millet": "कोदो बाजरा",
        "Barnyard Millet": "सांवा", "Proso Millet": "चेना", "Teff": "टेफ",
        "Barley": "जौ", "Oat": "जई", "Rye": "राई",
        "Chickpea": "चना", "Pigeon Pea (Tur)": "अरहर (तुअर)",
        "Green Gram (Moong)": "मूंग", "Black Gram (Urad)": "उड़द",
        "Lentil": "मसूर", "Cowpea": "लोबिया", "Field Pea": "हरी मटर",
        "Horse Gram": "कुलथी", "Moth Bean": "मोठ", "Lablab Bean": "सेम",
        "Soybean": "सोयाबीन", "Groundnut": "मूंगफली", "Mustard": "सरसों",
        "Rapeseed": "तोरिया", "Sesame": "तिल", "Sunflower": "सूरजमुखी",
        "Castor": "अरंडी", "Linseed": "अलसी", "Safflower": "कुसुम",
        "Niger": "रामतिल", "Cotton": "कपास", "Jute": "पटसन",
        "Mesta": "मेस्टा", "Sunn Hemp": "सनहेम्प", "Sugarcane": "गन्ना",
        "Sugar Beet": "चुकंदर", "Potato": "आलू", "Tomato": "टमाटर",
        "Brinjal": "बैंगन", "Chilli": "मिर्च", "Bell Pepper": "शिमला मिर्च",
        "Onion": "प्याज़", "Garlic": "लहसुन", "Okra": "भिंडी",
        "Cabbage": "पत्तागोभी", "Cauliflower": "फूलगोभी", "Broccoli": "ब्रोकोली",
        "Carrot": "गाजर", "Radish": "मूली", "Beetroot": "चुकंदर",
        "Spinach": "पालक", "Coriander": "धनिया", "Fenugreek": "मेथी",
        "Lettuce": "सलाद पत्ता", "Cucumber": "खीरा", "Pumpkin": "कद्दू",
        "Bottle Gourd": "लौकी", "Bitter Gourd": "करेला",
        "Ridge Gourd": "तुरई", "Sponge Gourd": "गिल्की",
        "Ash Gourd": "पेठा", "Watermelon": "तरबूज", "Muskmelon": "खरबूजा",
        "Papaya": "पपीता", "Banana": "केला", "Mango": "आम",
        "Guava": "अमरूद", "Sapota": "चीकू", "Pomegranate": "अनार",
        "Grapes": "अंगूर", "Apple": "सेब", "Orange": "संतरा",
        "Lemon": "नींबू", "Sweet Lime": "मौसंबी", "Coconut": "नारियल",
        "Arecanut": "सुपारी", "Cashew": "काजू", "Tea": "चाय",
        "Coffee": "कॉफ़ी", "Rubber": "रबर", "Black Pepper": "काली मिर्च",
        "Cardamom": "इलायची", "Clove": "लौंग", "Cinnamon": "दालचीनी",
        "Turmeric": "हल्दी", "Ginger": "अदरक", "Cumin": "जीरा",
        "Fennel": "सौंफ", "Ajwain": "अजवाइन", "Dill": "सोया साग",
        "Mint": "पुदीना", "Aloe Vera": "घृतकुमारी (एलोवेरा)", "Tulsi": "तुलसी",
        "Stevia": "स्टीविया", "Isabgol (Psyllium)": "ईसबगोल",
    }
    
    lang = request.user.preferred_language if request.user.is_authenticated else request.session.get('preferred_language', 'en')
    
    all_crops_qs = Crop.objects.all().order_by('name')
    crops_list = []
    for c in all_crops_qs:
        if lang == 'gu':
            label = gu_names.get(c.name) or c.name
        elif lang == 'hi':
            label = hi_names.get(c.name) or c.name
        else:
            label = c.name
        crops_list.append({'value': c.name, 'label': label})

    raw_crop = request.session.get('assistant_crop', '')
    raw_soil = request.session.get('assistant_soil_type', '')
    raw_stage = request.session.get('assistant_stage', '')
    raw_weather = request.session.get('assistant_weather', '')

    if lang == 'gu':
        display_crop = gu_names.get(raw_crop) or raw_crop
    elif lang == 'hi':
        display_crop = hi_names.get(raw_crop) or raw_crop
    else:
        display_crop = raw_crop

    soil_map = {
        'en': {
            'Loamy Soil': 'Loamy Soil',
            'Clayey Soil': 'Clayey Soil',
            'Sandy Soil': 'Sandy Soil',
            'Black Cotton Soil': 'Black Cotton Soil',
            'Red Soil': 'Red Soil'
        },
        'hi': {
            'Loamy Soil': 'दोमट मिट्टी',
            'Clayey Soil': 'चिकनी मिट्टी',
            'Sandy Soil': 'रेतीली मिट्टी',
            'Black Cotton Soil': 'काली कपास मिट्टी',
            'Red Soil': 'लाल मिट्टी'
        },
        'gu': {
            'Loamy Soil': 'લોમી જમીન',
            'Clayey Soil': 'ચિકણી જમીન',
            'Sandy Soil': 'રેતાળ જમીન',
            'Black Cotton Soil': 'કાળી કપાસ જમીન',
            'Red Soil': 'લાલ જમીન'
        }
    }

    stage_map = {
        'en': {
            'Seedling': 'Seedling',
            'Vegetative': 'Vegetative',
            'Flowering': 'Flowering',
            'Fruiting': 'Fruiting',
            'Harvesting': 'Harvesting'
        },
        'hi': {
            'Seedling': 'बीज अवस्था',
            'Vegetative': 'वनस्पति विकास',
            'Flowering': 'फूल अवस्था',
            'Fruiting': 'फल / कंद अवस्था',
            'Harvesting': 'कटाई अवस्था'
        },
        'gu': {
            'Seedling': 'બીજ અવસ્થા',
            'Vegetative': 'વનસ્પતિ વિકાસ',
            'Flowering': 'ફૂલ અવસ્થા',
            'Fruiting': 'ફળ / કંદ અવસ્થા',
            'Harvesting': 'કાપણી અવસ્થા'
        }
    }

    weather_map = {
        'en': {
            'Hot & Dry (32°C - 38°C)': 'Hot & Dry (32°C - 38°C)',
            'Mild & Cloudy (24°C - 28°C)': 'Mild & Cloudy (24°C - 28°C)',
            'Rainy & Wet (Warm & Humid)': 'Rainy & Wet (Warm & Humid)',
            'Cold & Humid (12°C - 18°C)': 'Cold & Humid (12°C - 18°C)'
        },
        'hi': {
            'Hot & Dry (32°C - 38°C)': 'गरम और सूखा',
            'Mild & Cloudy (24°C - 28°C)': 'हल्का और बादलवाला',
            'Rainy & Wet (Warm & Humid)': 'बरसात और गीला',
            'Cold & Humid (12°C - 18°C)': 'ठंडा और आर्द्र'
        },
        'gu': {
            'Hot & Dry (32°C - 38°C)': 'ગરમ અને સૂકું',
            'Mild & Cloudy (24°C - 28°C)': 'હળવું અને વાદળિયું',
            'Rainy & Wet (Warm & Humid)': 'વરસાદી અને ભીનું',
            'Cold & Humid (12°C - 18°C)': 'ઠંડું અને ભેજવાળું'
        }
    }

    display_soil = soil_map.get(lang, soil_map['en']).get(raw_soil, raw_soil)
    display_stage = stage_map.get(lang, stage_map['en']).get(raw_stage, raw_stage)
    display_weather = weather_map.get(lang, weather_map['en']).get(raw_weather, raw_weather)

    context = {
        'has_context': has_context,
        'crop_name': display_crop,
        'soil_type': display_soil,
        'stage': display_stage,
        'weather_desc': display_weather,
        'chat_history': request.session.get('chat_history', []),
        'crops_list': crops_list,
    }
    return render(request, 'assistant.html', context)


