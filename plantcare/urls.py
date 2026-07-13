from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    dashboard_view, login_view, register_view, logout_view,
    verify_email_view, verify_profile_update_view, find_username_view,
    password_reset_request_view, password_reset_verify_view,
    crop_library_view, scan_upload_view, weather_advisor_view,
    profile_settings_view, toggle_preference_view, download_scan_pdf,
    support_view, recovery_list_view, recovery_start_view,
    recovery_detail_view, recovery_checkin_view, recovery_pdf_export_view,
    recovery_ask_view, history_view
)

urlpatterns = [
    # Admin Portal
    path('admin/', admin.site.urls),
    
    # MVT Frontend Views
    path('', dashboard_view, name='dashboard'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    # Email verification, password reset & username recovery
    path('verify-email/', verify_email_view, name='verify_email'),
    path('verify-profile-update/', verify_profile_update_view, name='verify_profile_update'),
    path('find-username/', find_username_view, name='find_username'),
    path('password-reset/', password_reset_request_view, name='password_reset_request'),
    path('password-reset/verify/', password_reset_verify_view, name='password_reset_verify'),
    path('library/', crop_library_view, name='crop_library'),
    path('scan/', scan_upload_view, name='scan_upload'),
    path('scan/download-pdf/<int:result_id>/', download_scan_pdf, name='download_scan_pdf'),
    path('weather/', weather_advisor_view, name='weather_advisor'),
    path('profile/', profile_settings_view, name='profile_settings'),
    path('preferences/toggle/', toggle_preference_view, name='toggle_preference'),
    path('support/', support_view, name='support'),
    path('history/', history_view, name='history'),
    path('recovery/', recovery_list_view, name='recovery_list'),
    path('recovery/start/', recovery_start_view, name='recovery_start'),
    path('recovery/<int:journey_id>/', recovery_detail_view, name='recovery_detail'),
    path('recovery/<int:journey_id>/checkin/', recovery_checkin_view, name='recovery_checkin'),
    path('recovery/<int:journey_id>/pdf/', recovery_pdf_export_view, name='recovery_pdf'),
    path('recovery/<int:journey_id>/ask/', recovery_ask_view, name='recovery_ask'),



    
    # REST API endpoints (Active for testing and headless access)
    path('api/accounts/', include('accounts.urls')),
    path('api/library/', include('library.urls')),
    path('api/scans/', include('scans.urls')),
    path('api/weather/', include('weather.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
