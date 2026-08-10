from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .serializers import UserSerializer, RegisterSerializer, PreferencesSerializer

User = get_user_model()

class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        # Add user details to response
        data['user'] = UserSerializer(self.user).data
        return data

class LoginView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenObtainPairSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

from rest_framework import mixins

class ProfileView(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, generics.GenericAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def post(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

class PreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        serializer = PreferencesSerializer(instance=request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


from django.db import connection
from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from deep_translator import GoogleTranslator
import logging
logger = logging.getLogger(__name__)

_translation_cache = {}
_to_english_cache = {}

def translate_list(items, target_lang):
    if not items or not target_lang or target_lang == 'en':
        return items
    
    cache_key = (tuple(items), target_lang)
    if cache_key in _translation_cache:
        translated_items = _translation_cache[cache_key]
        # Populate reverse cache
        for eng_item, trans_item in zip(items, translated_items):
            _to_english_cache[(trans_item, target_lang)] = eng_item
        return translated_items
        
    try:
        joined = "\n".join(items)
        translated_str = GoogleTranslator(source='en', target=target_lang).translate(joined)
        translated_items = [t.strip() for t in translated_str.split("\n")]
        if len(translated_items) == len(items):
            _translation_cache[cache_key] = translated_items
            for eng_item, trans_item in zip(items, translated_items):
                _to_english_cache[(trans_item, target_lang)] = eng_item
            return translated_items
    except Exception as e:
        logger.error(f"List translation failed: {e}")
        
    try:
        res = []
        translator = GoogleTranslator(source='en', target=target_lang)
        for item in items:
            res.append(translator.translate(item))
        _translation_cache[cache_key] = res
        for eng_item, trans_item in zip(items, res):
            _to_english_cache[(trans_item, target_lang)] = eng_item
        return res
    except Exception:
        return items

def translate_to_english(text, source_lang):
    if not text or not source_lang or source_lang == 'en':
        return text
    cache_key = (text, source_lang)
    if cache_key in _to_english_cache:
        return _to_english_cache[cache_key]
    try:
        translated = GoogleTranslator(source=source_lang, target='en').translate(text)
        cleaned = translated.strip()
        _to_english_cache[cache_key] = cleaned
        return cleaned
    except Exception:
        return text


class StatesListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        lang = request.GET.get('lang', 'en').strip()
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT state FROM accounts_indianlocation ORDER BY state ASC")
            states = [row[0] for row in cursor.fetchall() if row[0]]
        translated = translate_list(states, lang)
        result = [{"en": eng, "trans": trans} for eng, trans in zip(states, translated)]
        return JsonResponse({'states': result})

class DistrictsListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        state = request.GET.get('state', '').strip()
        lang = request.GET.get('lang', 'en').strip()
        if not state:
            return JsonResponse({'error': 'State is required'}, status=400)
        
        state_en = translate_to_english(state, lang)
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT district FROM accounts_indianlocation WHERE state = %s ORDER BY district ASC", [state_en])
            districts = [row[0] for row in cursor.fetchall() if row[0]]
        translated = translate_list(districts, lang)
        result = [{"en": eng, "trans": trans} for eng, trans in zip(districts, translated)]
        return JsonResponse({'districts': result})

class SubdistrictsListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        state = request.GET.get('state', '').strip()
        district = request.GET.get('district', '').strip()
        lang = request.GET.get('lang', 'en').strip()
        if not state or not district:
            return JsonResponse({'error': 'State and District are required'}, status=400)
            
        state_en = translate_to_english(state, lang)
        district_en = translate_to_english(district, lang)
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT subdistrict FROM accounts_indianlocation WHERE state = %s AND district = %s ORDER BY subdistrict ASC", [state_en, district_en])
            subdistricts = [row[0] for row in cursor.fetchall() if row[0]]
        translated = translate_list(subdistricts, lang)
        result = [{"en": eng, "trans": trans} for eng, trans in zip(subdistricts, translated)]
        return JsonResponse({'subdistricts': result})

class VillagesListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        state = request.GET.get('state', '').strip()
        district = request.GET.get('district', '').strip()
        subdistrict = request.GET.get('subdistrict', '').strip()
        lang = request.GET.get('lang', 'en').strip()
        if not state or not district or not subdistrict:
            return JsonResponse({'error': 'State, District, and Subdistrict are required'}, status=400)
            
        state_en = translate_to_english(state, lang)
        district_en = translate_to_english(district, lang)
        subdistrict_en = translate_to_english(subdistrict, lang)
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT village FROM accounts_indianlocation WHERE state = %s AND district = %s AND subdistrict = %s ORDER BY village ASC", [state_en, district_en, subdistrict_en])
            villages = [row[0] for row in cursor.fetchall() if row[0]]
        translated = translate_list(villages, lang)
        result = [{"en": eng, "trans": trans} for eng, trans in zip(villages, translated)]
        return JsonResponse({'villages': result})


