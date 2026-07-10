import os
import sys
import django

# Add project root to path so we can import Django modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plantcare.settings')
django.setup()

from library.models import Crop, Disease, Fertilizer

def seed_all_diseases():
    print("Initializing fertilizers...")
    # Get or create standard fertilizers
    npk, _ = Fertilizer.objects.get_or_create(
        name="NPK 19-19-19 Fertilizer",
        defaults={
            'fertilizer_type': 'chemical',
            'description': 'Balanced chemical fertilizer containing 19% Nitrogen, 19% Phosphorus, and 19% Potassium.',
            'description_en': 'Balanced chemical fertilizer containing 19% Nitrogen, 19% Phosphorus, and 19% Potassium.',
            'description_hi': '19% नाइट्रोजन, 19% फास्फोरस और 19% पोटेशियम युक्त संतुलित रासायनिक उर्वरक।',
            'description_gu': '૧૯% નાઇટ્રોજન, ૧૯% ફોસ્ફરસ અને ૧૯% પોટેશિયમ ધરાવતું સંતુલિત રાસાયણિક ખાતર.',
            'usage_instructions': 'Apply 50g per plant once a month during active growth. Water immediately after application.',
            'usage_instructions_en': 'Apply 50g per plant once a month during active growth. Water immediately after application.',
            'usage_instructions_hi': 'सक्रिय वृद्धि के दौरान महीने में एक बार प्रति पौधा 50 ग्राम डालें। डालने के तुरंत बाद पानी दें।',
            'usage_instructions_gu': 'સક્રિય વૃદ્ધિ દરમિયાન મહિનામાં એકવાર છોડ દીઠ ૫૦ ગ્રામ આપો. આપ્યા પછી તરત જ પાણી આપો.'
        }
    )
    
    neem, _ = Fertilizer.objects.get_or_create(
        name="Neem Cake Organic Fertilizer",
        defaults={
            'fertilizer_type': 'organic',
            'description': 'Organic fertilizer derived from neem kernels, acting as a nutrient enhancer and soil pest repellant.',
            'description_en': 'Organic fertilizer derived from neem kernels, acting as a nutrient enhancer and soil pest repellant.',
            'description_hi': 'नीम की गुठली से प्राप्त जैविक उर्वरक, जो पोषक तत्व बढ़ाने और मिट्टी के कीड़ों को दूर भगाने का काम करता है।',
            'description_gu': 'લીમડાના મીંજમાંથી મેળવેલ સેન્દ્રિય ખાતર, જે પોષક તત્ત્વો વધારનાર અને જમીનના જંતુઓને દૂર રાખનાર તરીકે કામ કરે છે.',
            'usage_instructions': 'Mix 100g with topsoil per square meter during bed preparation or root zone dressing.',
            'usage_instructions_en': 'Mix 100g with topsoil per square meter during bed preparation or root zone dressing.',
            'usage_instructions_hi': 'क्यारी तैयार करते समय या जड़ क्षेत्र में प्रति वर्ग मीटर 100 ग्राम ऊपरी मिट्टी में मिलाएं।',
            'usage_instructions_gu': 'ક્યારી તૈયાર કરતી વખતે અથવા મૂળના ભાગમાં ચોરસ મીટર દીઠ ૧૦૦ ગ્રામ માટી સાથે મિશ્રિત કરો.'
        }
    )
    
    tricho, _ = Fertilizer.objects.get_or_create(
        name="Trichoderma Bio-fungicide",
        defaults={
            'fertilizer_type': 'bio',
            'description': 'Ecofriendly bio-fungicide that prevents root rot and wilt diseases while promoting growth.',
            'description_en': 'Ecofriendly bio-fungicide that prevents root rot and wilt diseases while promoting growth.',
            'description_hi': 'पर्यावरण अनुकूल जैव-कवकनाशी जो जड़ सड़न और विल्ट रोगों को रोकता है और विकास को बढ़ावा देता है।',
            'description_gu': 'પર્યાવરણને અનુકૂળ જૈવ-ફૂગનાશક જે મૂળ સડવા અને સુકારાના રોગોને અટકાવે છે અને છોડના વિકાસને વેગ આપે છે.',
            'usage_instructions': 'Mix 5-10g per liter of water and drench the soil around the root zone.',
            'usage_instructions_en': 'Mix 5-10g per liter of water and drench the soil around the root zone.',
            'usage_instructions_hi': '5-10 ग्राम प्रति लीटर पानी में मिलाएं और जड़ क्षेत्र के आसपास की मिट्टी को भिगो दें।',
            'usage_instructions_gu': 'લીટર પાણી દીઠ ૫-૧૦ ગ્રામ મિક્સ કરી મૂળના ભાગની આસપાસ જમીનમાં છાંટવું.'
        }
    )
    
    crops = Crop.objects.all()
    print(f"Generating diseases for {crops.count()} crops...")
    
    diseases_created = 0
    for crop in crops:
        # 1. Leaf Spot
        ls, created_ls = Disease.objects.update_or_create(
            crop=crop,
            name=f"{crop.name} Leaf Spot",
            defaults={
                'symptoms': 'Circular brown spots with yellow halos appearing on mature leaves.',
                'symptoms_en': 'Circular brown spots with yellow halos appearing on mature leaves.',
                'symptoms_hi': 'परिपक्व पत्तियों पर पीले प्रभामंडल के साथ गोलाकार भूरे रंग के धब्बे दिखाई देते हैं।',
                'symptoms_gu': 'પરિપક્વ પાંદડા પર પીળા કુંડાળા સાથે ગોળાકાર કથ્થઈ રંગના ડાઘ દેખાય છે.',
                
                'causes': 'Fungal pathogens spreading via water splashes and high humidity.',
                'causes_en': 'Fungal pathogens spreading via water splashes and high humidity.',
                'causes_hi': 'पानी के छीटों और उच्च आर्द्रता के माध्यम से फैलने वाले कवक रोगजनक।',
                'causes_gu': 'પાણીના છંટકાવ અને ઊંચા ભેજને કારણે ફેલાતી ફૂગ.',
                
                'treatment': 'Prune affected leaves, avoid overhead watering, and ensure adequate spacing.',
                'treatment_en': 'Prune affected leaves, avoid overhead watering, and ensure adequate spacing.',
                'treatment_hi': 'प्रभावित पत्तियों की छंटाई करें, ऊपर से पानी देने से बचें और पर्याप्त दूरी सुनिश्चित करें।',
                'treatment_gu': 'રોગગ્રસ્ત પાંદડા કાપી નાખો, ઉપરથી પાણી આપવાનું ટાળો અને યોગ્ય અંતર જાળવો.',
                
                'pesticides_recommended': 'Apply Chlorothalonil or Mancozeb fungicide spray once every 10-14 days.',
                'pesticides_recommended_en': 'Apply Chlorothalonil or Mancozeb fungicide spray once every 10-14 days.',
                'pesticides_recommended_hi': 'हर 10-14 दिनों में एक बार क्लोरोथैलोनिल या मैनकोजेब कवकनाशी का छिड़काव करें।',
                'pesticides_recommended_gu': 'દર ૧૦-૧૪ દિવસે એકવાર ક્લોરોથેલોનિલ અથવા મેન્કોઝેબ ફૂગનાશક દવાનો છંટકાવ કરો.'
            }
        )
        ls.fertilizers_recommended.add(neem, tricho)
        if created_ls:
            diseases_created += 1
            
        # 2. Powdery Mildew
        pm, created_pm = Disease.objects.update_or_create(
            crop=crop,
            name=f"{crop.name} Powdery Mildew",
            defaults={
                'symptoms': 'White powdery coating covering leaf surfaces, causing curling and premature drop.',
                'symptoms_en': 'White powdery coating covering leaf surfaces, causing curling and premature drop.',
                'symptoms_hi': 'पत्तियों की सतह पर सफेद पाउडर जैसा लेप आ जाता है, जिससे पत्तियां मुड़ जाती हैं और समय से पहले गिर जाती हैं।',
                'symptoms_gu': 'પાંદડાની સપાટી પર સફેદ પાવડર જેવું પડ જામી જાય છે, જેથી પાંદડા વળી જાય છે અને ખરી પડે છે.',
                
                'causes': 'Airborne fungal spores thriving in warm days and cool nights.',
                'causes_en': 'Airborne fungal spores thriving in warm days and cool nights.',
                'causes_hi': 'गर्म दिनों और ठंडी रातों में पनपने वाले हवा के कवक बीजाणु।',
                'causes_gu': 'ગરમ દિવસો અને ઠંડી રાતોમાં હવામાંથી ફેલાતી ફૂગના કણો.',
                
                'treatment': 'Enhance air circulation, expose to direct sunlight, and remove heavily infected branches.',
                'treatment_en': 'Enhance air circulation, expose to direct sunlight, and remove heavily infected branches.',
                'treatment_hi': 'हवा का संचार बढ़ाएं, सीधी धूप में रखें और अत्यधिक संक्रमित शाखाओं को हटा दें।',
                'treatment_gu': 'હવાની અવરજવર વધારો, સીધો સૂર્યપ્રકાશ આપો અને વધુ પ્રભાવિત ડાળીઓ દૂર કરો.',
                
                'pesticides_recommended': 'Spray sulfur-based fungicides or systemic Metalaxyl sprays.',
                'pesticides_recommended_en': 'Spray sulfur-based fungicides or systemic Metalaxyl sprays.',
                'pesticides_recommended_hi': 'सल्फर-आधारित कवकनाशी या प्रणालीगत मेटलैक्सिल का छिड़काव करें।',
                'pesticides_recommended_gu': 'સલ્ફર આધારિત ફૂગનાશક અથવા મેટલેક્સિલ પ્રણાલીગત દવાનો છંટકાવ કરો.'
            }
        )
        pm.fertilizers_recommended.add(npk, tricho)
        if created_pm:
            diseases_created += 1
            
    print(f"Completed seeding: Created {diseases_created} new disease-crop entries successfully.")

if __name__ == '__main__':
    seed_all_diseases()
