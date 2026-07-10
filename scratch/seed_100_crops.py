import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plantcare.settings')
django.setup()

from library.models import Crop

crops_data = [
    ("Rice", "Oryza sativa", "Cereal"),
    ("Wheat", "Triticum aestivum", "Cereal"),
    ("Maize", "Zea mays", "Cereal"),
    ("Pearl Millet (Bajra)", "Pennisetum glaucum", "Millet"),
    ("Sorghum (Jowar)", "Sorghum bicolor", "Millet"),
    ("Finger Millet (Ragi)", "Eleusine coracana", "Millet"),
    ("Foxtail Millet", "Setaria italica", "Millet"),
    ("Little Millet", "Panicum sumatrense", "Millet"),
    ("Kodo Millet", "Paspalum scrobiculatum", "Millet"),
    ("Barnyard Millet", "Echinochloa frumentacea", "Millet"),
    ("Proso Millet", "Panicum miliaceum", "Millet"),
    ("Teff", "Eragrostis tef", "Millet"),
    ("Barley", "Hordeum vulgare", "Cereal"),
    ("Oat", "Avena sativa", "Cereal"),
    ("Rye", "Secale cereale", "Cereal"),
    ("Chickpea", "Cicer arietinum", "Pulse"),
    ("Pigeon Pea (Tur)", "Cajanus cajan", "Pulse"),
    ("Green Gram (Moong)", "Vigna radiata", "Pulse"),
    ("Black Gram (Urad)", "Vigna mungo", "Pulse"),
    ("Lentil", "Lens culinaris", "Pulse"),
    ("Cowpea", "Vigna unguiculata", "Pulse"),
    ("Field Pea", "Pisum sativum", "Pulse"),
    ("Horse Gram", "Macrotyloma uniflorum", "Pulse"),
    ("Moth Bean", "Vigna aconitifolia", "Pulse"),
    ("Lablab Bean", "Lablab purpureus", "Pulse"),
    ("Soybean", "Glycine max", "Oilseed"),
    ("Groundnut", "Arachis hypogaea", "Oilseed"),
    ("Mustard", "Brassica juncea", "Oilseed"),
    ("Rapeseed", "Brassica napus", "Oilseed"),
    ("Sesame", "Sesamum indicum", "Oilseed"),
    ("Sunflower", "Helianthus annuus", "Oilseed"),
    ("Castor", "Ricinus communis", "Oilseed"),
    ("Linseed", "Linum usitatissimum", "Oilseed"),
    ("Safflower", "Carthamus tinctorius", "Oilseed"),
    ("Niger", "Guizotia abyssinica", "Oilseed"),
    ("Cotton", "Gossypium hirsutum", "Fiber"),
    ("Jute", "Corchorus olitorius", "Fiber"),
    ("Mesta", "Hibiscus cannabinus", "Fiber"),
    ("Sunn Hemp", "Crotalaria juncea", "Fiber"),
    ("Sugarcane", "Saccharum officinarum", "Cash Crop"),
    ("Sugar Beet", "Beta vulgaris", "Cash Crop"),
    ("Potato", "Solanum tuberosum", "Vegetable"),
    ("Tomato", "Solanum lycopersicum", "Vegetable"),
    ("Brinjal", "Solanum melongena", "Vegetable"),
    ("Chilli", "Capsicum annuum", "Vegetable"),
    ("Bell Pepper", "Capsicum annuum", "Vegetable"),
    ("Onion", "Allium cepa", "Vegetable"),
    ("Garlic", "Allium sativum", "Vegetable"),
    ("Okra", "Abelmoschus esculentus", "Vegetable"),
    ("Cabbage", "Brassica oleracea var. capitata", "Vegetable"),
    ("Cauliflower", "Brassica oleracea var. botrytis", "Vegetable"),
    ("Broccoli", "Brassica oleracea var. italica", "Vegetable"),
    ("Carrot", "Daucus carota", "Vegetable"),
    ("Radish", "Raphanus sativus", "Vegetable"),
    ("Beetroot", "Beta vulgaris", "Vegetable"),
    ("Spinach", "Spinacia oleracea", "Leafy Vegetable"),
    ("Coriander", "Coriandrum sativum", "Leafy Vegetable"),
    ("Fenugreek", "Trigonella foenum-graecum", "Leafy Vegetable"),
    ("Lettuce", "Lactuca sativa", "Vegetable"),
    ("Cucumber", "Cucumis sativus", "Vegetable"),
    ("Pumpkin", "Cucurbita maxima", "Vegetable"),
    ("Bottle Gourd", "Lagenaria siceraria", "Vegetable"),
    ("Bitter Gourd", "Momordica charantia", "Vegetable"),
    ("Ridge Gourd", "Luffa acutangula", "Vegetable"),
    ("Sponge Gourd", "Luffa cylindrica", "Vegetable"),
    ("Ash Gourd", "Benincasa hispida", "Vegetable"),
    ("Watermelon", "Citrullus lanatus", "Fruit"),
    ("Muskmelon", "Cucumis melo", "Fruit"),
    ("Papaya", "Carica papaya", "Fruit"),
    ("Banana", "Musa paradisiaca", "Fruit"),
    ("Mango", "Mangifera indica", "Fruit"),
    ("Guava", "Psidium guajava", "Fruit"),
    ("Sapota", "Manilkara zapota", "Fruit"),
    ("Pomegranate", "Punica granatum", "Fruit"),
    ("Grapes", "Vitis vinifera", "Fruit"),
    ("Apple", "Malus domestica", "Fruit"),
    ("Orange", "Citrus sinensis", "Fruit"),
    ("Lemon", "Citrus limon", "Fruit"),
    ("Sweet Lime", "Citrus limetta", "Fruit"),
    ("Coconut", "Cocos nucifera", "Plantation"),
    ("Arecanut", "Areca catechu", "Plantation"),
    ("Cashew", "Anacardium occidentale", "Plantation"),
    ("Tea", "Camellia sinensis", "Plantation"),
    ("Coffee", "Coffea arabica", "Plantation"),
    ("Rubber", "Hevea brasiliensis", "Plantation"),
    ("Black Pepper", "Piper nigrum", "Spice"),
    ("Cardamom", "Elettaria cardamomum", "Spice"),
    ("Clove", "Syzygium aromaticum", "Spice"),
    ("Cinnamon", "Cinnamomum verum", "Spice"),
    ("Turmeric", "Curcuma longa", "Spice"),
    ("Ginger", "Zingiber officinale", "Spice"),
    ("Cumin", "Cuminum cyminum", "Spice"),
    ("Fennel", "Foeniculum vulgare", "Spice"),
    ("Ajwain", "Trachyspermum ammi", "Spice"),
    ("Dill", "Anethum graveolens", "Spice"),
    ("Mint", "Mentha arvensis", "Herb"),
    ("Aloe Vera", "Aloe vera", "Medicinal"),
    ("Tulsi", "Ocimum tenuiflorum", "Medicinal"),
    ("Stevia", "Stevia rebaudiana", "Medicinal"),
    ("Isabgol (Psyllium)", "Plantago ovata", "Medicinal")
]

def seed_crops():
    print(f"Starting seeding of {len(crops_data)} crops...")
    created_count = 0
    updated_count = 0
    
    for name, scientific_name, category in crops_data:
        # Determine some specific temperature/humidity ranges based on category
        temp_min = 15.0
        temp_max = 35.0
        hum_min = 40.0
        hum_max = 80.0
        
        if category in ["Fruit", "Plantation", "Spice"]:
            temp_min = 20.0
            temp_max = 38.0
            hum_min = 50.0
            hum_max = 90.0
        elif category in ["Medicinal", "Herb", "Cereal"]:
            temp_min = 12.0
            temp_max = 32.0
            
        desc_en = f"A prominent Indian crop variety categorized under {category}. It is widely cultivated for agricultural utility."
        desc_hi = f"{category} के अंतर्गत वर्गीकृत एक प्रमुख भारतीय फसल किस्म। यह कृषि उपयोग के लिए व्यापक रूप से उगाई जाती है।"
        desc_gu = f"{category} હેઠળ વર્ગીકૃત થયેલ એક પ્રમુખ ભારતીય પાકની જાત. કૃષિ ઉપયોગિતા માટે તેની વ્યાપક ખેતી કરવામાં આવે છે."
        
        crop, created = Crop.objects.update_or_create(
            name=name,
            defaults={
                'scientific_name': scientific_name,
                'description': desc_en,
                'description_en': desc_en,
                'description_hi': desc_hi,
                'description_gu': desc_gu,
                'ideal_temp_min_c': temp_min,
                'ideal_temp_max_c': temp_max,
                'ideal_humidity_min': hum_min,
                'ideal_humidity_max': hum_max,
                'image': 'crops/default.png'
            }
        )
        if created:
            created_count += 1
        else:
            updated_count += 1
            
    print(f"Completed seeding: Created {created_count}, Updated {updated_count} crops.")

if __name__ == '__main__':
    seed_crops()
