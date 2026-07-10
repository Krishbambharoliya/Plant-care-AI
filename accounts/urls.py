from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView, ProfileView, PreferencesView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='api-register'),
    path('login/', LoginView.as_view(), name='api-login'),
    path('login/refresh/', TokenRefreshView.as_view(), name='api-token_refresh'),
    path('profile/', ProfileView.as_view(), name='api-profile'),
    path('preferences/', PreferencesView.as_view(), name='api-preferences'),
]
