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

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if username:
            active_exists = User.objects.filter(username__iexact=username, is_active=True).exists()
            if active_exists:
                raise forms.ValidationError("This username is already taken.")
            # Delete inactive user with this username to prevent registration blocking
            User.objects.filter(username__iexact=username, is_active=False).delete()
        return username

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if not first_name:
            raise forms.ValidationError("First name is required.")
        if len(first_name) < 2:
            raise forms.ValidationError("First name must be at least 2 characters long.")
        import re
        if not re.match(r'^[a-zA-Z]+$', first_name):
            raise forms.ValidationError("First name must contain only letters.")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if not last_name:
            raise forms.ValidationError("Last name is required.")
        if len(last_name) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters long.")
        import re
        if not re.match(r'^[a-zA-Z]+$', last_name):
            raise forms.ValidationError("Last name must contain only letters.")
        return last_name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip().lower()
            active_exists = User.objects.filter(email__iexact=email, is_active=True).exists()
            if active_exists:
                raise forms.ValidationError("This email address is already registered. Please use a different email.")
            # Delete inactive user with this email to prevent registration blocking
            User.objects.filter(email__iexact=email, is_active=False).delete()
        return email

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get('phone_number') or '').strip()
        if phone_number:
            if not phone_number.isdigit():
                raise forms.ValidationError("Phone number must contain only digits.")
            if len(phone_number) != 10:
                raise forms.ValidationError("Phone number must be exactly 10 digits long.")
        return phone_number or None

    def clean_location_city(self):
        city = (self.cleaned_data.get('location_city') or '').strip()
        if not city:
            raise forms.ValidationError("Location is required. Please select State, District, Taluka, and Village.")
        parts = [p.strip() for p in city.split(',') if p.strip()]
        if len(parts) < 4:
            raise forms.ValidationError("Location is incomplete. Please select State, District, Taluka, and Village.")
        
        from weather.services import OpenWeatherClient
        lat, lon = OpenWeatherClient.geocode_city(city)
        if lat is None or lon is None:
            raise forms.ValidationError("The location could not be geocoded. Please enter a valid location.")
        return city

    def clean_farm_size_acres(self):
        size = self.cleaned_data.get('farm_size_acres')
        if size is not None and size < 0:
            raise forms.ValidationError("Farm size cannot be negative.")
        return size

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
    first_name = forms.CharField(max_length=30, required=True, label="First Name")
    last_name = forms.CharField(max_length=30, required=True, label="Last Name")

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

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if not first_name:
            raise forms.ValidationError("First name is required.")
        if len(first_name) < 2:
            raise forms.ValidationError("First name must be at least 2 characters long.")
        import re
        if not re.match(r'^[a-zA-Z]+$', first_name):
            raise forms.ValidationError("First name must contain only letters.")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if not last_name:
            raise forms.ValidationError("Last name is required.")
        if len(last_name) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters long.")
        import re
        if not re.match(r'^[a-zA-Z]+$', last_name):
            raise forms.ValidationError("Last name must contain only letters.")
        return last_name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip().lower()
            qs = User.objects.filter(email__iexact=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            # Only check active users or others (exclude self)
            if qs.filter(is_active=True).exists():
                raise forms.ValidationError("This email address is already used by another account.")
        return email

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get('phone_number') or '').strip()
        if phone_number:
            if not phone_number.isdigit():
                raise forms.ValidationError("Phone number must contain only digits.")
            if len(phone_number) != 10:
                raise forms.ValidationError("Phone number must be exactly 10 digits long.")
        return phone_number or None

    def clean_location_city(self):
        city = (self.cleaned_data.get('location_city') or '').strip()
        if not city:
            raise forms.ValidationError("Location is required. Please select State, District, Taluka, and Village.")
        parts = [p.strip() for p in city.split(',') if p.strip()]
        if len(parts) < 4:
            raise forms.ValidationError("Location is incomplete. Please select State, District, Taluka, and Village.")
        
        from weather.services import OpenWeatherClient
        lat, lon = OpenWeatherClient.geocode_city(city)
        if lat is None or lon is None:
            raise forms.ValidationError("The location could not be geocoded. Please enter a valid location.")
        return city

    def clean_farm_size_acres(self):
        size = self.cleaned_data.get('farm_size_acres')
        if size is not None and size < 0:
            raise forms.ValidationError("Farm size cannot be negative.")
        return size


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
        # Pass full location string to allow fallback geocoding
        res_lat, res_lon = OpenWeatherClient.geocode_city(city)
        if res_lat is not None and res_lon is not None:
            user.latitude, user.longitude = res_lat, res_lon
