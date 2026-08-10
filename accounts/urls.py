from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, ProfileView, PreferencesView,
    StatesListView, DistrictsListView, SubdistrictsListView, VillagesListView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='api-register'),
    path('login/', LoginView.as_view(), name='api-login'),
    path('login/refresh/', TokenRefreshView.as_view(), name='api-token_refresh'),
    path('profile/', ProfileView.as_view(), name='api-profile'),
    path('preferences/', PreferencesView.as_view(), name='api-preferences'),
    path('locations/states/', StatesListView.as_view(), name='api-locations-states'),
    path('locations/districts/', DistrictsListView.as_view(), name='api-locations-districts'),
    path('locations/subdistricts/', SubdistrictsListView.as_view(), name='api-locations-subdistricts'),
    path('locations/villages/', VillagesListView.as_view(), name='api-locations-villages'),
]
