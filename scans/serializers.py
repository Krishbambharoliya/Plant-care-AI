from rest_framework import serializers
from .models import ScanHistory

class ScanHistorySerializer(serializers.ModelSerializer):
    localized_crop_name = serializers.SerializerMethodField()
    localized_disease_name = serializers.SerializerMethodField()

    class Meta:
        model = ScanHistory
        fields = [
            'id', 'user', 'image', 'organ', 'identified_species',
            'identified_common_name', 'confidence_score', 'plantnet_raw_response',
            'matched_crop_name', 'disease_identified', 'is_healthy',
            'fertilizer_recommendation', 'latitude', 'longitude', 'created_at',
            'localized_crop_name', 'localized_disease_name'
        ]
        read_only_fields = [
            'id', 'user', 'identified_species', 'identified_common_name',
            'confidence_score', 'plantnet_raw_response', 'matched_crop_name',
            'disease_identified', 'is_healthy', 'fertilizer_recommendation', 'created_at',
            'localized_crop_name', 'localized_disease_name'
        ]

    def get_localized_crop_name(self, obj):
        request = self.context.get('request')
        lang = 'en'
        if request and request.user and request.user.is_authenticated:
            lang = getattr(request.user, 'preferred_language', 'en')
        from plantcare.utils import get_localized_crop_name
        return get_localized_crop_name(obj.matched_crop_name, lang)

    def get_localized_disease_name(self, obj):
        if obj.is_healthy or not obj.disease_identified:
            return None
        request = self.context.get('request')
        lang = 'en'
        if request and request.user and request.user.is_authenticated:
            lang = getattr(request.user, 'preferred_language', 'en')
        from plantcare.utils import get_localized_crop_name
        crop_name = get_localized_crop_name(obj.matched_crop_name, lang)
        
        disease_title = obj.disease_identified
        if "Leaf Spot" in obj.disease_identified:
            if lang == 'hi':
                disease_title = f"{crop_name} \u092a\u0924\u094d\u0924\u0940 \u0915\u093e \u0927\u092c\u094d\u092c\u093e \u0930\u094b\u0917"
            elif lang == 'gu':
                disease_title = f"{crop_name} \u0aba\u0abe\u0a82\u0aa6\u0aa1\u0abe \u0aaa\u0ab0 \u0aa1\u0abe\u0a98\u0aa8\u0acb \u0ab0\u0acb\u0a97"
            else:
                disease_title = f"{crop_name} Leaf Spot"
        elif "Powdery Mildew" in obj.disease_identified:
            if lang == 'hi':
                disease_title = f"{crop_name} \u092a\u093e\u0913\u0921\u0930\u0940 \u092e\u093f\u0932\u094d\u0921\u094d\u092f\u0942 \u0930\u094b\u0917"
            elif lang == 'gu':
                disease_title = f"{crop_name} \u0aaa\u0abe\u0ab5\u0aa1\u0ab0\u0ac0 \u0aae\u0abf\u0ab2\u0acd\u0aa1\u0acd\u0aaf\u0ac1 \u0ab0\u0acb\u0a97"
            else:
                disease_title = f"{crop_name} Powdery Mildew"
        elif obj.disease_identified == 'Early Blight':
            if lang == 'hi':
                disease_title = f"{crop_name} \u0905\u0917\u0947\u0924\u0940 \u091d\u0941\u0932\u0938\u093e"
            elif lang == 'gu':
                disease_title = f"{crop_name} \u0a85\u0a97\u0ac7\u0aa4\u0ac0 \u0ab8\u0ac1\u0a95\u0abe\u0ab0\u0acb"
            else:
                disease_title = f"{crop_name} Early Blight"
        elif obj.disease_identified == 'Late Blight':
            if lang == 'hi':
                disease_title = f"{crop_name} \u092a\u091b\u0947\u0924\u0940 \u091d\u0941\u0932\u0938\u093e"
            elif lang == 'gu':
                disease_title = f"{crop_name} \u0aae\u0acb\u0aa1\u0acb \u0ab8\u0ac1\u0a95\u0abe\u0ab0\u0acb"
            else:
                disease_title = f"{crop_name} Late Blight"
        return disease_title
