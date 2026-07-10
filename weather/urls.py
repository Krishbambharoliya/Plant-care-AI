from django.urls import path
from .views import CurrentWeatherView, ForecastWeatherView, HistoricalWeatherView, GrowthChanceView

urlpatterns = [
    path('current/', CurrentWeatherView.as_view(), name='api-weather-current'),
    path('forecast/', ForecastWeatherView.as_view(), name='api-weather-forecast'),
    path('past/', HistoricalWeatherView.as_view(), name='api-weather-past'),
    path('growth-chance/', GrowthChanceView.as_view(), name='api-weather-growth-chance'),
]
