from rest_framework import status, generics, mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db import models
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404
from django.http import Http404

from library.models import Disease, Crop
from .models import ScanHistory
from .serializers import ScanHistorySerializer
from .services import PlantNetClient, PlantNetError

class ScanUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # We need image and optionally organ, latitude, longitude
        image = request.FILES.get('image')
        organ = request.data.get('organ', 'leaf')
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        if not image:
            return Response({"image": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if organ not in [choice[0] for choice in ScanHistory.ORGAN_CHOICES]:
            return Response({"organ": "Invalid choice."}, status=status.HTTP_400_BAD_REQUEST)

        # Parse coordinates if given
        lat = float(latitude) if latitude is not None and latitude != '' else None
        lon = float(longitude) if longitude is not None and longitude != '' else None

        # 1. Save scan row
        scan = ScanHistory.objects.create(
            user=request.user,
            image=image,
            organ=organ,
            latitude=lat,
            longitude=lon,
            identified_species='Pending',
            confidence_score=0.0,
            plantnet_raw_response={},
            is_healthy=True
        )

        # 2. Call PlantNet
        try:
            result = PlantNetClient.identify(scan.image, scan.organ)
        except PlantNetError as e:
            # 3. If PlantNet fails -> delete the saved scan row and return 502
            scan.delete()
            err_str = str(e)
            lang = getattr(request.user, 'preferred_language', 'en')
            if "404" in err_str:
                organ_names = {
                    'leaf': {'en': 'leaf', 'hi': '\u092a\u0924\u094d\u0924\u0940', 'gu': '\u0aaa\u0abe\u0a82\u0aa6\u0aa1\u0ac1\u0a82'},
                    'flower': {'en': 'flower', 'hi': '\u092b\u0942\u0932', 'gu': '\u0aab\u0ac2\u0ab2'},
                    'fruit': {'en': 'fruit', 'hi': '\u092b\u0932', 'gu': '\u0aab\u0ab3'},
                    'bark': {'en': 'bark', 'hi': '\u091b\u093e\u0932', 'gu': '\u0a9b\u0abe\u0ab2'},
                }
                org_name_hi = organ_names.get(scan.organ, {}).get('hi', scan.organ)
                org_name_gu = organ_names.get(scan.organ, {}).get('gu', scan.organ)
                org_name_en = organ_names.get(scan.organ, {}).get('en', scan.organ)
                if lang == 'hi':
                    msg = f"\u0915\u094d\u0930\u092a\u092f\u093e \u0915\u0947\u0935\u0932 \u092a\u094c\u0927\u0947 \u0915\u0947 {org_name_hi} \u0915\u0940 \u090f\u0915 \u092e\u093e\u0928\u094d\u092f \u0914\u0930 \u0938\u094d\u092a\u0937\u094d\u091f \u091b\u0935\u093f \u0905\u092a\u0932\u094b\u0921 \u0915\u0930\u0947\u0902\u0964"
                elif lang == 'gu':
                    msg = f"\u0a95\u0ac3\u0aaa\u0abe \u0a95\u0ab0\u0ac0\u0aa8\u0ac5 \u0aae\u0abe\u0aa4\u0acd\u0ab0 \u0a9b\u0acb\u0aa1\u0aa8\u0abe {org_name_gu} \u0aa8\u0ac0 \u0a8f\u0a95 \u0aae\u0abe\u0aa8\u0acd\u0aaf \u0a85\u0aa8\u0ac7 \u0ab8\u0acd\u0aaa\u0ab7\u0acd\u0a9f \u0a9b\u0aac\u0ac0 \u0a85\u0aaa\u0ab2\u0acb\u0aa1 \u0a95\u0ab0\u0acb."
                else:
                    msg = f"Please upload a valid and clear image of a plant {org_name_en} only."
            else:
                if lang == 'hi':
                    msg = "पहचान सेवा अभी उपलब्ध नहीं है। कृपया बाद में प्रयास करें।"
                elif lang == 'gu':
                    msg = "ઓળખ સેવા હાલમાં ઉપલબ્ધ નથી. કૃપા કરીને પછીથી પ્રયાસ કરો।"
                else:
                    msg = "PlantNet identification service is currently unavailable. Please try again later."
            return Response({"error": msg}, status=status.HTTP_502_BAD_GATEWAY)

        # Update identification details
        scan.identified_species = result['species']
        scan.identified_common_name = result['common_name']
        scan.confidence_score = result['confidence_score']
        scan.plantnet_raw_response = result['raw']

        # 4. Determine matched crop name (common_name fallback to species)
        matched_crop_name = result['common_name'] if result['common_name'] else result['species']
        scan.matched_crop_name = matched_crop_name

        # Dynamic Crop lookup or creation
        crop = Crop.objects.filter(
            models.Q(name__iexact=matched_crop_name) | models.Q(scientific_name__iexact=result['species'])
        ).first()
        if not crop:
            crop = Crop.objects.create(
                name=matched_crop_name.capitalize(),
                scientific_name=result['species'],
                description=f"Auto-registered crop via PlantNet scan identification.",
                ideal_temp_min_c=15.0,
                ideal_temp_max_c=35.0,
                ideal_humidity_min=30.0,
                ideal_humidity_max=80.0
            )

        from plantcare.utils import check_image_health
        is_healthy_leaf = check_image_health(scan.image, organ=scan.organ)

        disease = Disease.objects.filter(crop=crop).first()

        # 6. If disease matches and leaf is not healthy -> mark unhealthy, fill details
        if disease and not is_healthy_leaf:
            scan.is_healthy = False
            scan.disease_identified = disease.name
            
            # Join recommended fertilizers or fallback to treatment text
            fertilizers = disease.fertilizers_recommended.all()
            if fertilizers.exists():
                scan.fertilizer_recommendation = ", ".join([f.name for f in fertilizers])
            else:
                scan.fertilizer_recommendation = disease.treatment
        else:
            # 7. Otherwise -> healthy
            scan.is_healthy = True
            scan.disease_identified = None
            scan.fertilizer_recommendation = None

        # 8. Save and return the full row
        scan.save()

        # Log scan record to FUTUREDATASET database for future model training
        try:
            from scans.models import FutureDataset
            FutureDataset.objects.using('FUTUREDATASET').create(
                username=request.user.username if request.user.is_authenticated else None,
                image_name=scan.image.name,
                organ=scan.organ,
                identified_species=scan.identified_species,
                identified_common_name=scan.identified_common_name,
                confidence_score=scan.confidence_score,
                is_healthy=scan.is_healthy,
                disease_identified=scan.disease_identified,
                fertilizer_recommendation=scan.fertilizer_recommendation,
                latitude=scan.latitude,
                longitude=scan.longitude
            )
        except Exception:
            pass

        serializer = ScanHistorySerializer(scan)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

from rest_framework.pagination import PageNumberPagination

class ScanHistoryPagination(PageNumberPagination):
    page_size = 5

class ScanHistoryView(mixins.ListModelMixin, generics.GenericAPIView):
    serializer_class = ScanHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ScanHistoryPagination

    def get_queryset(self):
        # Return only the current user's scans
        return ScanHistory.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

class ScanDetailView(mixins.RetrieveModelMixin, generics.GenericAPIView):
    serializer_class = ScanHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Retrieve scan, ensuring user isolation (return 404 if accessed by another user)
        scan_id = self.kwargs.get('pk')
        scan = get_object_or_404(ScanHistory, pk=scan_id)
        if scan.user != self.request.user:
            raise Http404("No ScanHistory matches the given query.")
        return scan

    def post(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

class ScanStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        scans = ScanHistory.objects.filter(user=request.user)
        total = scans.count()
        healthy_count = scans.filter(is_healthy=True).count()
        diseased_count = scans.filter(is_healthy=False).count()

        # Group by crop
        crop_counts = scans.values('matched_crop_name').annotate(count=Count('id'))
        scans_by_crop = {item['matched_crop_name'] or 'Unknown': item['count'] for item in crop_counts}

        # Group by month
        month_counts = scans.annotate(month=TruncMonth('created_at')).values('month').annotate(count=Count('id')).order_by('month')
        scans_by_month = {}
        for item in month_counts:
            if item['month']:
                month_str = item['month'].strftime('%Y-%m')
                scans_by_month[month_str] = item['count']

        return Response({
            'total': total,
            'healthy_count': healthy_count,
            'diseased_count': diseased_count,
            'scans_by_crop': scans_by_crop,
            'scans_by_month': scans_by_month
        }, status=status.HTTP_200_OK)
