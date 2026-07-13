from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone_number', 'profile_image',
            'location_city', 'latitude', 'longitude', 'farm_name',
            'farm_size_acres', 'preferred_language', 'theme_preference',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_email(self, value):
        """Ensure email is unique across all users, excluding the current user."""
        request = self.context.get('request')
        qs = User.objects.filter(email__iexact=value)
        if request and request.user and request.user.pk:
            qs = qs.exclude(pk=request.user.pk)
        if qs.exists():
            raise serializers.ValidationError("This email address is already used by another account.")
        return value

    def validate_location_city(self, value):
        if value:
            from accounts.constants import GUJARAT_CITIES
            matched = [c for c in GUJARAT_CITIES if c.lower() == value.strip().lower()]
            if not matched:
                raise serializers.ValidationError("Location City must be a city within Gujarat state.")
            return matched[0]
        return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2', 'phone_number',
            'profile_image', 'location_city', 'latitude', 'longitude',
            'farm_name', 'farm_size_acres', 'preferred_language', 'theme_preference'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        return attrs

    def validate_email(self, value):
        """Ensure email is unique — one email per account."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email address is already registered. Please use a different email.")
        return value

    def validate_location_city(self, value):
        if value:
            from accounts.constants import GUJARAT_CITIES
            matched = [c for c in GUJARAT_CITIES if c.lower() == value.strip().lower()]
            if not matched:
                raise serializers.ValidationError("Location City must be a city within Gujarat state.")
            return matched[0]
        return value


    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class PreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['preferred_language', 'theme_preference']

    def validate_preferred_language(self, value):
        valid_languages = [choice[0] for choice in User.LANGUAGE_CHOICES]
        if value not in valid_languages:
            raise serializers.ValidationError("Invalid language choice.")
        return value

    def validate_theme_preference(self, value):
        valid_themes = [choice[0] for choice in User.THEME_CHOICES]
        if value not in valid_themes:
            raise serializers.ValidationError("Invalid theme choice.")
        return value
