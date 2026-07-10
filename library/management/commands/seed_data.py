from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from library.models import Crop, Fertilizer, Disease

class Command(BaseCommand):
    help = 'Seeds database with admin user and reference catalog'

    def handle(self, *args, **options):
        User = get_user_model()
        # 1. Create superuser if it doesn't exist
        if not User.objects.filter(username='krish').exists():
            User.objects.create_superuser(
                username='krish',
                email='krish@example.com',
                password='krish@2007',
                phone_number='9876543210',
                location_city='Ahmedabad',
                latitude=23.0225,
                longitude=72.5714,
                farm_name='Krish Farm',
                farm_size_acres=8.5,
                preferred_language='en',
                theme_preference='dark'
            )
            self.stdout.write(self.style.SUCCESS("Superuser 'krish' created successfully."))
        else:
            self.stdout.write("Superuser 'krish' already exists.")

        # 2. Seed Fertilizers
        fert_compost, _ = Fertilizer.objects.get_or_create(
            name='Organic Compost',
            defaults={
                'fertilizer_type': 'organic',
                'description': 'Rich organic humus providing a slow release of nutrients.',
                'description_en': 'Rich organic humus providing a slow release of nutrients.',
                'description_hi': 'पोषक तत्वों की धीमी गति प्रदान करने वाला समृद्ध जैविक ह्यूमस।',
                'description_gu': 'પોષક તત્વોનો ધીમો પ્રવાહ પ્રદાન કરતી સમૃદ્ધ ઓર્ગેનિક સેન્દ્રિય માટી.',
                'usage_instructions': 'Apply 2-3 inches deep to the soil surface before planting, or mix with topsoil.',
                'usage_instructions_en': 'Apply 2-3 inches deep to the soil surface before planting, or mix with topsoil.',
                'usage_instructions_hi': 'रोपण से पहले मिट्टी की सतह पर 2-3 इंच गहरा लगाएं, या ऊपरी मिट्टी के साथ मिलाएं।',
                'usage_instructions_gu': 'વાવણી પહેલાં જમીનની સપાટી પર ૨ થી ૩ ઇંચ ઊંડે સુધી ઉમેરો, અથવા ઉપરની માટી સાથે ભેળવો.'
            }
        )
        # Update details in case it was already created
        fert_compost.description_en = 'Rich organic humus providing a slow release of nutrients.'
        fert_compost.description_hi = 'पोषक तत्वों की धीमी गति प्रदान करने वाला समृद्ध जैविक ह्यूमस।'
        fert_compost.description_gu = 'પોષક તત્વોનો ધીમો પ્રવાહ પ્રદાન કરતી સમૃદ્ધ ઓર્ગેનિક સેન્દ્રિય માટી.'
        fert_compost.usage_instructions_en = 'Apply 2-3 inches deep to the soil surface before planting, or mix with topsoil.'
        fert_compost.usage_instructions_hi = 'रोपण से पहले मिट्टी की सतह पर 2-3 इंच गहरा लगाएं, या ऊपरी मिट्टी के साथ मिलाएं।'
        fert_compost.usage_instructions_gu = 'વાવણી પહેલાં જમીનની સપાટી પર ૨ થી ૩ ઇંચ ઊંડે સુધી ઉમેરો, અથવા ઉપરની માટી સાથે ભેળવો.'
        fert_compost.save()

        fert_urea, _ = Fertilizer.objects.get_or_create(
            name='Urea',
            defaults={
                'fertilizer_type': 'chemical',
                'description': 'High nitrogen synthetic fertilizer for fast foliage growth.',
                'description_en': 'High nitrogen synthetic fertilizer for fast foliage growth.',
                'description_hi': 'तेजी से पत्तियों के विकास के लिए उच्च नाइट्रोजन कृत्रिम उर्वरक।',
                'description_gu': 'પાંદડાઓના ઝડપી વિકાસ માટે ઉચ્ચ નાઇટ્રોજનયુક્ત કૃત્રિમ ખાતર.',
                'usage_instructions': 'Dissolve 1 tablespoon per gallon of water and apply to wet soil around plants.',
                'usage_instructions_en': 'Dissolve 1 tablespoon per gallon of water and apply to wet soil around plants.',
                'usage_instructions_hi': '1 गैलन पानी में 1 बड़ा चम्मच घोलें और पौधों के आसपास गीली मिट्टी पर लगाएं।',
                'usage_instructions_gu': '૧ ગેલન પાણીમાં ૧ મોટી ચમચી ઓગાળો અને છોડની આસપાસની ભીની માટીમાં ઉમેરો.'
            }
        )
        fert_urea.description_en = 'High nitrogen synthetic fertilizer for fast foliage growth.'
        fert_urea.description_hi = 'तेजी से पत्तियों के विकास के लिए उच्च नाइट्रोजन कृत्रिम उर्वरक।'
        fert_urea.description_gu = 'પાંદડાઓના ઝડપી વિકાસ માટે ઉચ્ચ નાઇટ્રોજનયુક્ત કૃત્રિમ ખાતર.'
        fert_urea.usage_instructions_en = 'Dissolve 1 tablespoon per gallon of water and apply to wet soil around plants.'
        fert_urea.usage_instructions_hi = '1 गैलन पानी में 1 बड़ा चम्मच घोलें और पौधों के आसपास गीली मिट्टी पर लगाएं।'
        fert_urea.usage_instructions_gu = '૧ ગેલન પાણીમાં ૧ મોટી ચમચી ઓગાળો અને છોડની આસપાસની ભીની માટીમાં ઉમેરો.'
        fert_urea.save()

        fert_npk, _ = Fertilizer.objects.get_or_create(
            name='NPK 19-19-19',
            defaults={
                'fertilizer_type': 'chemical',
                'description': 'Balanced fertilizer with equal parts nitrogen, phosphorus, and potassium.',
                'description_en': 'Balanced fertilizer with equal parts nitrogen, phosphorus, and potassium.',
                'description_hi': 'समान मात्रा में नाइट्रोजन, फास्फोरस और पोटेशियम के साथ संतुलित उर्वरक।',
                'description_gu': 'નાઇટ્રોજન, ફોસ્ફરસ અને પોટેશિયમ સરખા પ્રમાણમાં ધરાવતું સંતુલિત ખાતર.',
                'usage_instructions': 'Spray at 15-day intervals at a concentration of 2g per liter of water.',
                'usage_instructions_en': 'Spray at 15-day intervals at a concentration of 2g per liter of water.',
                'usage_instructions_hi': 'पानी में 2 ग्राम प्रति लीटर की सांद्रता पर 15 दिनों के अंतराल पर छिड़काव करें।',
                'usage_instructions_gu': 'પાણીમાં ૨ ગ્રામ પ્રતિ લિટરના પ્રમાણ સાથે ૧૫ દિવસના અંતરે છંટકાવ કરો.'
            }
        )
        fert_npk.description_en = 'Balanced fertilizer with equal parts nitrogen, phosphorus, and potassium.'
        fert_npk.description_hi = 'समान मात्रा में नाइट्रोजन, फास्फोरस और पोटेशियम के साथ संतुलित उर्वरक।'
        fert_npk.description_gu = 'નાઇટ્રોજન, ફોસ્ફરસ અને પોટેશિયમ સરખા પ્રમાણમાં ધરાવતું સંતુલિત ખાતર.'
        fert_npk.usage_instructions_en = 'Spray at 15-day intervals at a concentration of 2g per liter of water.'
        fert_npk.usage_instructions_hi = 'पानी में 2 ग्राम प्रति लीटर की सांद्रता पर 15 दिनों के अंतराल पर छिड़काव करें।'
        fert_npk.usage_instructions_gu = 'પાણીમાં ૨ ગ્રામ પ્રતિ લિટરના પ્રમાણ સાથે ૧૫ દિવસના અંતરે છંટકાવ કરો.'
        fert_npk.save()

        fert_neem, _ = Fertilizer.objects.get_or_create(
            name='Neem Cake Powder',
            defaults={
                'fertilizer_type': 'bio',
                'description': 'Organic fertilizer and nematicide from neem seeds.',
                'description_en': 'Organic fertilizer and nematicide from neem seeds.',
                'description_hi': 'नीम के बीजों से बना जैविक उर्वरक और नेमाटीसाइड।',
                'description_gu': 'લીમડાના બીજમાંથી બનાવેલ ઓર્ગેનિક ખાતર અને કીટનાશક.',
                'usage_instructions': 'Add 50-100g to the soil mix per plant pot.',
                'usage_instructions_en': 'Add 50-100g to the soil mix per plant pot.',
                'usage_instructions_hi': 'प्रति पौधे के गमले की मिट्टी के मिश्रण में 50-100 ग्राम मिलाएं।',
                'usage_instructions_gu': 'દરેક કુંડાની માટીના મિશ્રણમાં ૫૦ થી ૧૦૦ ગ્રામ ઉમેરો.'
            }
        )
        fert_neem.description_en = 'Organic fertilizer and nematicide from neem seeds.'
        fert_neem.description_hi = 'नीम के बीजों से बना जैविक उर्वरक और नेमाटीसाइड।'
        fert_neem.description_gu = 'લીમડાના બીજમાંથી બનાવેલ ઓર્ગેનિક ખાતર અને કીટનાશક.'
        fert_neem.usage_instructions_en = 'Add 50-100g to the soil mix per plant pot.'
        fert_neem.usage_instructions_hi = 'प्रति पौधे के गमले की मिट्टी के मिश्रण में 50-100 ग्राम मिलाएं।'
        fert_neem.usage_instructions_gu = 'દરેક કુંડાની માટીના મિશ્રણમાં ૫૦ થી ૧૦૦ ગ્રામ ઉમેરો.'
        fert_neem.save()

        # 3. Seed Crops
        crop_tomato, _ = Crop.objects.get_or_create(
            name='Tomato',
            defaults={
                'scientific_name': 'Solanum lycopersicum',
                'description': 'Nutrient-rich red fruit widely used in cooking.',
                'description_en': 'Nutrient-rich red fruit widely used in cooking.',
                'description_hi': 'पोषक तत्वों से भरपूर लाल फल जो खाना पकाने में व्यापक रूप से उपयोग किया जाता है।',
                'description_gu': 'રસોઈમાં વ્યાપકપણે ઉપયોગમાં લેવાતું પોષક તત્વોથી ભરપૂર લાલ ફળ.',
                'ideal_temp_min_c': 18.0,
                'ideal_temp_max_c': 32.0,
                'ideal_humidity_min': 55.0,
                'ideal_humidity_max': 80.0
            }
        )
        crop_tomato.description_en = 'Nutrient-rich red fruit widely used in cooking.'
        crop_tomato.description_hi = 'पोषक तत्वों से भरपूर लाल फल जो खाना पकाने में व्यापक रूप से उपयोग किया जाता है।'
        crop_tomato.description_gu = 'રસોઈમાં વ્યાપકપણે ઉપયોગમાં લેવાતું પોષક તત્વોથી ભરપૂર લાલ ફળ.'
        crop_tomato.save()

        crop_potato, _ = Crop.objects.get_or_create(
            name='Potato',
            defaults={
                'scientific_name': 'Solanum tuberosum',
                'description': 'Starchy tuber crop, essential staple globally.',
                'description_en': 'Starchy tuber crop, essential staple globally.',
                'description_hi': 'स्टार्चयुक्त कंद फसल, विश्व स्तर पर आवश्यक प्रधान भोजन।',
                'description_gu': 'સ્ટાર્ચયુક્ત કંદ પાક, વૈશ્વિક સ્તરે આવશ્યક મુખ્ય ખોરાક.',
                'ideal_temp_min_c': 15.0,
                'ideal_temp_max_c': 24.0,
                'ideal_humidity_min': 60.0,
                'ideal_humidity_max': 75.0
            }
        )
        crop_potato.description_en = 'Starchy tuber crop, essential staple globally.'
        crop_potato.description_hi = 'स्टार्चयुक्त कंद फसल, विश्व स्तर पर आवश्यक प्रधान भोजन।'
        crop_potato.description_gu = 'સ્ટાર્ચયુક્ત કંદ પાક, વૈષવિક સ્તરે આવશ્યક મુખ્ય ખોરાક.'
        crop_potato.save()

        crop_pepper, _ = Crop.objects.get_or_create(
            name='Chili Pepper',
            defaults={
                'scientific_name': 'Capsicum annuum',
                'description': 'Hot spicy peppers that thrive in warm climates.',
                'description_en': 'Hot spicy peppers that thrive in warm climates.',
                'description_hi': 'तीखी मसालेदार मिर्च जो गर्म जलवायु में पनपती है।',
                'description_gu': 'તીખી મસાલેદાર મરચી જે ગરમ આબોહવામાં સારી રીતે વધે છે.',
                'ideal_temp_min_c': 20.0,
                'ideal_temp_max_c': 35.0,
                'ideal_humidity_min': 50.0,
                'ideal_humidity_max': 70.0
            }
        )
        crop_pepper.description_en = 'Hot spicy peppers that thrive in warm climates.'
        crop_pepper.description_hi = 'तीखी मसालेदार मिर्च जो गर्म जलवायु में पनपती है।'
        crop_pepper.description_gu = 'તીખી મસાલેદાર મરચી જે ગરમ આબોહવામાં સારી રીતે વધે છે.'
        crop_pepper.save()

        # 4. Seed Diseases
        d_early_blight, _ = Disease.objects.get_or_create(
            crop=crop_tomato,
            name='Early Blight',
            defaults={
                'symptoms': 'Concentric black rings on older leaves, yellowing halos.',
                'symptoms_en': 'Concentric black rings on older leaves, yellowing halos.',
                'symptoms_hi': 'पुरानी पत्तियों पर संकेंद्रित काले घेरे, पीले रंग का प्रभामंडल।',
                'symptoms_gu': 'જૂના પાંદડા પર કેન્દ્રિત કાળા વલયો, પીળા પ્રભામંડળ.',
                'causes': 'Alternaria solani fungus, favored by warm temperatures and frequent rains.',
                'causes_en': 'Alternaria solani fungus, favored by warm temperatures and frequent rains.',
                'causes_hi': 'अल्टरनेरिया सोलेनी कवक, गर्म तापमान और लगातार बारिश से अनुकूल।',
                'causes_gu': 'અલ્ટરનેરિયા સોલાની ફૂગ, ગરમ તાપમાન અને વારંવાર વરસાદ દ્વારા અનુકૂળ.',
                'treatment': 'Apply copper fungicides, prune lower leaves, and water the soil rather than leaves.',
                'treatment_en': 'Apply copper fungicides, prune lower leaves, and water the soil rather than leaves.',
                'treatment_hi': 'तांबे के कवकनाशी लगाएं, निचली पत्तियों की छंटाई करें, और पत्तियों के बजाय मिट्टी को पानी दें।',
                'treatment_gu': 'તાંબાની ફૂગનાશક દવાઓ લગાવો, નીચેના પાંદડા કાપો અને પાંદડાને બદલે માટીને પાણી આપો.'
            }
        )
        d_early_blight.symptoms_en = 'Concentric black rings on older leaves, yellowing halos.'
        d_early_blight.symptoms_hi = 'पुरानी पत्तियों पर संकेंद्रित काले घेरे, पीले रंग का प्रभामंडल।'
        d_early_blight.symptoms_gu = 'જૂના પાંદડા પર કેન્દ્રિત કાળા વલયો, પીળા પ્રભામંડળ.'
        d_early_blight.causes_en = 'Alternaria solani fungus, favored by warm temperatures and frequent rains.'
        d_early_blight.causes_hi = 'अल्टरनेरिया सोलेनी कवक, गर्म तापमान और लगातार बारिश से अनुकूल।'
        d_early_blight.causes_gu = 'અલ્ટરનેરિયા સોલાની ફૂગ, ગરમ તાપમાન અને વારંવાર વરસાદ દ્વારા અનુકૂળ.'
        d_early_blight.treatment_en = 'Apply copper fungicides, prune lower leaves, and water the soil rather than leaves.'
        d_early_blight.treatment_hi = 'तांबे के कवकनाशी लगाएं, निचली पत्तियों की छंटाई करें, और पत्तियों के बजाय मिट्टी को पानी दें।'
        d_early_blight.treatment_gu = 'તાંબાની ફૂગનાશક દવાઓ લગાવો, નીચેના પાંદડા કાપો અને પાંદડાને બદલે માટીને પાણી આપો.'
        d_early_blight.save()
        d_early_blight.fertilizers_recommended.add(fert_compost, fert_neem)

        d_late_blight, _ = Disease.objects.get_or_create(
            crop=crop_tomato,
            name='Late Blight',
            defaults={
                'symptoms': 'Dark, water-soaked spots on leaves that turn brown/black, white mold underneath.',
                'symptoms_en': 'Dark, water-soaked spots on leaves that turn brown/black, white mold underneath.',
                'symptoms_hi': 'पत्तियों पर काले, पानी से भीगे धब्बे जो भूरे/काले हो जाते हैं, नीचे सफेद फफूंद लग जाती है।',
                'symptoms_gu': 'પાંદડા પર ઘેરા, પાણીથી લથબથ ડાઘ જે બ્રાઉન/કાળા થઈ જાય છે, નીચે સફેદ ફૂગ.',
                'causes': 'Phytophthora infestans oomycete, thriving in cool, wet conditions.',
                'causes_en': 'Phytophthora infestans oomycete, thriving in cool, wet conditions.',
                'causes_hi': 'फाइटोफ्थोरा इन्फेस्टन्स ओमीसीट, ठंडी, गीली परिस्थितियों में पनपता है।',
                'causes_gu': 'ફાયટોપ્થોરા ઇન્ફેસ્ટન્સ ઓમીસીટી, ઠંડી અને ભીની સ્થિતિમાં વધે છે.',
                'treatment': 'Prune affected sections, apply systemic fungicides, and avoid overhead irrigation.',
                'treatment_en': 'Prune affected sections, apply systemic fungicides, and avoid overhead irrigation.',
                'treatment_hi': 'प्रभावित हिस्सों की छंटाई करें, प्रणालीगत कवकनाशी लगाएं, और ऊपर से सिंचाई करने से बचें।',
                'treatment_gu': 'અસરગ્રસ્ત ભાગો કાપી નાખો, ફૂગનાશકો લગાવો અને ઉપરથી પાણી છાંટવાનું ટાળો.'
            }
        )
        d_late_blight.symptoms_en = 'Dark, water-soaked spots on leaves that turn brown/black, white mold underneath.'
        d_late_blight.symptoms_hi = 'पत्तियों पर काले, पानी से भीगे धब्बे जो भूरे/काले हो जाते हैं, नीचे सफेद फफूंद लग जाती है।'
        d_late_blight.symptoms_gu = 'પાંદડા પર ઘેરા, પાણીથી લથબથ ડાઘ જે બ્રાઉન/કાળા થઈ જાય છે, નીચે સફેદ ફૂગ.'
        d_late_blight.causes_en = 'Phytophthora infestans oomycete, thriving in cool, wet conditions.'
        d_late_blight.causes_hi = 'फाइटोफ्थोरा इन्फेस्टन्स ओमीसीट, ठंडी, गीली परिस्थितियों में पनपता है।'
        d_late_blight.causes_gu = 'ફાયટોપ્થોરા ઇન્ફેસ્ટન્સ ઓમીસીટી, ઠંડી અને ભીની સ્થિતિમાં વધે છે.'
        d_late_blight.treatment_en = 'Prune affected sections, apply systemic fungicides, and avoid overhead irrigation.'
        d_late_blight.treatment_hi = 'प्रभावित हिस्सों की छंटाई करें, प्रणालीगत कवकनाशी लगाएं, और ऊपर से सिंचाई करने से बचें।'
        d_late_blight.treatment_gu = 'અસરગ્રસ્ત ભાગો કાપી નાખો, ફૂગનાશકો લગાવો અને ઉપરથી પાણી છાંટવાનું ટાળો.'
        d_late_blight.save()
        d_late_blight.fertilizers_recommended.add(fert_npk)

        d_potato_blight, _ = Disease.objects.get_or_create(
            crop=crop_potato,
            name='Late Blight',
            defaults={
                'symptoms': 'Large dark lesions on leaves, rotting tubers with reddish-brown dry rot.',
                'symptoms_en': 'Large dark lesions on leaves, rotting tubers with reddish-brown dry rot.',
                'symptoms_hi': 'पत्तियों पर बड़े काले घाव, लाल-भूरे रंग के सूखे सड़न वाले सड़ते हुए कंद।',
                'symptoms_gu': 'પાંદડા પર મોટા ઘેરા ઘા, લાલ-બ્રાઉન સૂકા સડા સાથે સડતા બટાકા.',
                'causes': 'Phytophthora infestans oomycete, highly destructive in wet seasons.',
                'causes_en': 'Phytophthora infestans oomycete, highly destructive in wet seasons.',
                'causes_hi': 'फाइटोफ्थोरा इन्फेस्टन्स ओमीसीट, गीले मौसम में अत्यधिक विनाशकारी।',
                'causes_gu': 'ફાયટોપ્થોરા ઇન્ફેસ્ટન્સ ઓમીસીટી, ભીની ઋતુમાં અત્યંત વિનાશક.',
                'treatment': 'Plant certified disease-free tubers, harvest in dry conditions, spray fungicides.',
                'treatment_en': 'Plant certified disease-free tubers, harvest in dry conditions, spray fungicides.',
                'treatment_hi': 'प्रमाणित रोग-मुक्त कंद बोएं, सूखी परिस्थितियों में कटाई करें, कवकनाशी का छिड़काव करें।',
                'treatment_gu': 'પ્રમાણિત રોગમુક્ત બટાકા વાવો, સૂકી સ્થિતિમાં લણણી કરો, ફૂગનાશક દવાઓ છાંટો.'
            }
        )
        d_potato_blight.symptoms_en = 'Large dark lesions on leaves, rotting tubers with reddish-brown dry rot.'
        d_potato_blight.symptoms_hi = 'पत्तियों पर बड़े काले घाव, लाल-भूरे रंग के सूखे सड़न वाले सड़ते हुए कंद।'
        d_potato_blight.symptoms_gu = 'પાંદડા પર મોટા ઘેરા ઘા, લાલ-બ્રાઉન સૂકા સડા સાથે સડતા બટાકા.'
        d_potato_blight.causes_en = 'Phytophthora infestans oomycete, highly destructive in wet seasons.'
        d_potato_blight.causes_hi = 'फाइटोफ्थोरा इन्फेस्टन्स ओमीसीट, गीले मौसम में अत्यधिक विनाशकारी।'
        d_potato_blight.causes_gu = 'ફાયટોપ્થોરા ઇન્ફેસ્ટન્સ ઓમીસીટી, ભીની ઋતુમાં અત્યંત વિનાશક.'
        d_potato_blight.treatment_en = 'Plant certified disease-free tubers, harvest in dry conditions, spray fungicides.'
        d_potato_blight.treatment_hi = 'प्रमाणित रोग-मुक्त कंद बोएं, सूखी परिस्थितियों में कटाई करें, कवकनाशी का छिड़काव करें।'
        d_potato_blight.treatment_gu = 'પ્રમાણિત રોગમુક્ત બટાકા વાવો, સૂકી સ્થિતિમાં લણણી કરો, ફૂગનાશક દવાઓ છાંટો.'
        d_potato_blight.save()
        d_potato_blight.fertilizers_recommended.add(fert_urea, fert_npk)

        self.stdout.write(self.style.SUCCESS("Database seeded with Crops, Fertilizers, and Diseases."))
