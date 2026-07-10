from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    dashboard_view, login_view, register_view, logout_view,
    verify_email_view, verify_email_change_view,
    password_reset_request_view, password_reset_verify_view,
    crop_library_view, scan_upload_view, weather_advisor_view,
    profile_settings_view, toggle_preference_view, download_scan_pdf
)

urlpatterns = [
    # Admin Portal
    path('admin/', admin.site.urls),
    
    # MVT Frontend Views
    path('', dashboard_view, name='dashboard'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    # Email verification & password reset
    path('verify-email/', verify_email_view, name='verify_email'),
    path('verify-email-change/', verify_email_change_view, name='verify_email_change'),
    path('password-reset/', password_reset_request_view, name='password_reset_request'),
    path('password-reset/verify/', password_reset_verify_view, name='password_reset_verify'),
    path('library/', crop_library_view, name='crop_library'),
    path('scan/', scan_upload_view, name='scan_upload'),
    path('scan/download-pdf/<int:result_id>/', download_scan_pdf, name='download_scan_pdf'),
    path('weather/', weather_advisor_view, name='weather_advisor'),
    path('profile/', profile_settings_view, name='profile_settings'),
    path('preferences/toggle/', toggle_preference_view, name='toggle_preference'),


    
    # REST API endpoints (Active for testing and headless access)
    path('api/accounts/', include('accounts.urls')),
    path('api/library/', include('library.urls')),
    path('api/scans/', include('scans.urls')),
    path('api/weather/', include('weather.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
