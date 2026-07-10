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
        
    return render(request, 'login.html', {'form': form, 'error': error})

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

                return render(request, 'login.html', {
                    'success_message': 'Password reset successful! Please log in with your new password.',
                })
            except User.DoesNotExist:
                error = "User not found."
        else:
            error = "Invalid OTP or email. Please check your details and try again."

    return render(request, 'password_reset_verify.html', {'email': session_email, 'error': error})


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
        
        if request.user.is_authenticated:
            user = request.user
            if lang in ['en', 'hi', 'gu']:
                user.preferred_language = lang
            if theme in ['light', 'dark']:
                user.theme_preference = theme
            user.save()
        else:
            if lang in ['en', 'hi', 'gu']:
                request.session['preferred_language'] = lang
            if theme in ['light', 'dark']:
                request.session['theme_preference'] = theme
                
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
    }
    return render(request, 'dashboard.html', context)

# ==========================================
# CROP LIBRARY
# ==========================================
@login_required
def crop_library_view(request):
    search_query = request.GET.get('q', '')
    disease_query = request.GET.get('disease_q', '')
    
    # Main crops list
    crops = Crop.objects.all().order_by('name')
    if search_query:
        crops = crops.filter(name__icontains=search_query)
        
    # Standalone disease search
    disease_results = []
    if disease_query:
        from django.db.models import Q
        disease_results = Disease.objects.filter(
            Q(name__icontains=disease_query) |
            Q(symptoms__icontains=disease_query) |
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
        'selected_crop': selected_crop
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
        resolved_lat, resolved_lon = OpenWeatherClient.geocode_city(city)
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
        new_email = request.POST.get('email', '').strip()
        current_email = request.user.email
        email_changed = new_email and new_email.lower() != current_email.lower()

        form = FarmerProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            if email_changed:
                # Save everything EXCEPT email first
                user = form.save(commit=False)
                user.email = current_email  # keep old email for now
                user.save()

                # Generate OTP for the new email
                otp_code = str(random.randint(100000, 999999))
                EmailOTP.objects.create(email=new_email, otp=otp_code, purpose='email_change')

                # Send OTP to the NEW email address
                try:
                    send_mail(
                        subject='PlantCare - Verify Your New Email Address',
                        message=(
                            f'Hello {user.username},\n\n'
                            f'You requested to change your PlantCare email to this address.\n'
                            f'Your One-Time Password (OTP) to confirm this change is:\n\n'
                            f'   {otp_code}\n\n'
                            f'If you did not request this change, please ignore this email.\n\n'
                            f'- PlantCare Team'
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[new_email],
                        fail_silently=False,
                    )
                except Exception:
                    pass

                # Store new email in session for the verify step
                request.session['pending_email'] = new_email
                return redirect('verify_email_change')
            else:
                form.save()
                success = True
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
def verify_email_change_view(request):
    """Verify the new email address with a 6-digit OTP before committing the change."""
    pending_email = request.session.get('pending_email')
    if not pending_email:
        return redirect('profile_settings')

    error = ""
    if request.method == "POST":
        otp_entered = request.POST.get('otp', '').strip()
        otp_record = EmailOTP.objects.filter(
            email=pending_email, purpose='email_change', is_verified=False
        ).first()

        if otp_record and otp_record.otp == otp_entered:
            # Mark OTP used and update email
            otp_record.is_verified = True
            otp_record.save()

            request.user.email = pending_email
            request.user.save(update_fields=['email'])
            request.session.pop('pending_email', None)

            return render(request, 'profile_settings.html', {
                'form': FarmerProfileForm(instance=request.user),
                'success': True,
                'success_message': f'Email successfully updated to {pending_email}.',
                'error': ''
            })
        else:
            error = "Invalid OTP. Please check and try again."

    return render(request, 'verify_email_change.html', {
        'pending_email': pending_email,
        'error': error
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

