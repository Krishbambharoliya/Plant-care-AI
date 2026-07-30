from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class FarmerRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, label="First Name")
    last_name = forms.CharField(max_length=30, required=True, label="Last Name")
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=False)
    location_city = forms.CharField(max_length=100, required=False)
    latitude = forms.FloatField(required=False)
    longitude = forms.FloatField(required=False)
    farm_name = forms.CharField(max_length=150, required=False)
    farm_size_acres = forms.FloatField(required=False)
    preferred_language = forms.ChoiceField(
        choices=User.LANGUAGE_CHOICES,
        required=True,
        initial='en',
        label="Preferred Language / पसंदीदा भाषा / મનપસંદ ભાષા"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + (
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'location_city',
            'latitude',
            'longitude',
            'farm_name',
            'farm_size_acres',
            'preferred_language'
        )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip().lower()
            if User.objects.filter(email__iexact=email).exists():
                raise forms.ValidationError("This email address is already registered. Please use a different email.")
        return email

    def clean_location_city(self):
        # Retrieve the location city value from the form
        city = (self.cleaned_data.get('location_city') or '').strip()
        if city:
            from weather.services import OpenWeatherClient
            # If the location is formatted as "City, State", extract just the city name for API verification
            city_name = city.split(',')[0].strip()
            lat, lon = OpenWeatherClient.geocode_city(city_name)
            if lat is None or lon is None:
                raise forms.ValidationError("The city name does not match. Please enter a valid city name.")
        return city

    def save(self, commit=True):
        user = super().save(commit=False)
        # Ensure email is saved in lowercase/clean form
        if user.email:
            user.email = user.email.strip().lower()
        _resolve_user_coordinates(
            user,
            self.cleaned_data.get('location_city'),
            self.cleaned_data.get('latitude'),
            self.cleaned_data.get('longitude')
        )
        if commit:
            user.save()
        return user

class FarmerProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'location_city',
            'latitude',
            'longitude',
            'farm_name',
            'farm_size_acres'
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip().lower()
            qs = User.objects.filter(email__iexact=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This email address is already used by another account.")
        return email

    def clean_location_city(self):
        # Retrieve location city value from the form
        city = (self.cleaned_data.get('location_city') or '').strip()
        if city:
            from weather.services import OpenWeatherClient
            # If the location is formatted as "City, State", extract just the city name for API verification
            city_name = city.split(',')[0].strip()
            lat, lon = OpenWeatherClient.geocode_city(city_name)
            if lat is None or lon is None:
                raise forms.ValidationError("The city name does not match. Please enter a valid city name.")
        return city


    def save(self, commit=True):
        user = super().save(commit=False)
        _resolve_user_coordinates(
            user,
            self.cleaned_data.get('location_city'),
            self.cleaned_data.get('latitude'),
            self.cleaned_data.get('longitude')
        )
        if commit:
            user.save()
        return user



def _resolve_user_coordinates(user, city, lat, lon):
    """
    Resolves city name into latitude/longitude coordinates if they are missing.
    Supports 'City, State' formatted inputs by splitting the string.
    """
    if city and (lat is None or lon is None):
        from weather.services import OpenWeatherClient
        # Extract just the city name for OpenWeather geocoding
        city_name = city.split(',')[0].strip()
        res_lat, res_lon = OpenWeatherClient.geocode_city(city_name)
        if res_lat is not None and res_lon is not None:
            user.latitude, user.longitude = res_lat, res_lon
