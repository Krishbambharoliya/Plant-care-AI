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
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email address is already registered. Please use a different email.")
        return email

    def clean_location_city(self):
        city = self.cleaned_data.get('location_city') or ''
        city = city.strip()
        if city:
            from accounts.constants import GUJARAT_CITIES
            matched = [c for c in GUJARAT_CITIES if c.lower() == city.lower()]
            if not matched:
                raise forms.ValidationError("Location City must be a city within Gujarat state.")
            return matched[0]
        return city



    def save(self, commit=True):
        user = super().save(commit=False)
        city = self.cleaned_data.get('location_city')
        lat = self.cleaned_data.get('latitude')
        lon = self.cleaned_data.get('longitude')
        
        # If city name is filled but coords are blank, resolve coords automatically via geocoding
        if city and (lat is None or lon is None):
            from weather.services import OpenWeatherClient
            res_lat, res_lon = OpenWeatherClient.geocode_city(city)
            if res_lat is not None and res_lon is not None:
                user.latitude = res_lat
                user.longitude = res_lon
                
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
            # Exclude the current user from the uniqueness check
            qs = User.objects.filter(email__iexact=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This email address is already used by another account.")
        return email

    def clean_location_city(self):
        city = self.cleaned_data.get('location_city') or ''
        city = city.strip()
        if city:
            from accounts.constants import GUJARAT_CITIES
            matched = [c for c in GUJARAT_CITIES if c.lower() == city.lower()]
            if not matched:
                raise forms.ValidationError("Location City must be a city within Gujarat state.")
            return matched[0]
        return city



    def save(self, commit=True):
        user = super().save(commit=False)
        city = self.cleaned_data.get('location_city')
        lat = self.cleaned_data.get('latitude')
        lon = self.cleaned_data.get('longitude')

        # Check if coordinates need to be auto-resolved
        if city and (lat is None or lon is None):
            from weather.services import OpenWeatherClient
            res_lat, res_lon = OpenWeatherClient.geocode_city(city)
            if res_lat is not None and res_lon is not None:
                user.latitude = res_lat
                user.longitude = res_lon

        if commit:
            user.save()
        return user
