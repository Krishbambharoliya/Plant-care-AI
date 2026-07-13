import random
from django.core.management.base import BaseCommand
from library.models import Crop, Disease, Fertilizer

class Command(BaseCommand):
    help = 'Seeds 100 common crops with detailed descriptions, soil types, fertilizers, and diseases.'

    def handle(self, *args, **options):
        self.stdout.write("Deleting existing crops and library details...")
        Disease.objects.all().delete()
        Fertilizer.objects.all().delete()
        Crop.objects.all().delete()

        crops_catalog = [
            ("Potato", "Solanum tuberosum", "Sandy loam with high organic matter. Well-drained.", "Nitrogen-rich Compost"),
            ("Tomato", "Solanum lycopersicum", "Sandy loam or loamy soil. Slightly acidic pH 6.0-6.8.", "Tomato Organic Fertilizer"),
            ("Chili Pepper", "Capsicum annuum", "Sandy loam, well-aerated, well-drained. pH 5.5-6.8.", "Potassium-Rich Blend"),
            ("Maize", "Zea mays", "Loamy, fertile, well-drained soils with deep depth.", "Nitrogen-Urea Blend"),
            ("Rice", "Oryza sativa", "Clayey loam, capable of holding water. Acidic to neutral.", "Superphosphate Mix"),
            ("Wheat", "Triticum aestivum", "Well-drained clay loam or loamy soil. pH 6.0-7.0.", "Ammonium Nitrate Blend"),
            ("Cotton", "Gossypium hirsutum", "Deep alluvial or black clayey soil. pH 5.5-8.5.", "Phosphate Boost"),
            ("Sugarcane", "Saccharum officinarum", "Heavy clay loam or deep fertile sandy soils.", "Potash & Urea Mix"),
            ("Soybean", "Glycine max", "Loamy and alluvial soils with good organic count. pH 6.0-6.5.", "Phosphorus Nutrient Blend"),
            ("Groundnut", "Arachis hypogaea", "Well-drained sandy loam or sandy clay soil.", "Gypsum & Bio-fertilizer"),
            ("Onion", "Allium cepa", "Light sandy or loamy soils rich in humus. pH 5.8-6.5.", "Sulfate of Potash"),
            ("Garlic", "Allium sativum", "Rich, well-drained sandy loam with organic matter.", "Organic Compost manure"),
            ("Ginger", "Zingiber officinale", "Sandy loam or clayey loam soils, rich in humus.", "Neem Cake Fertilizer"),
            ("Turmeric", "Curcuma longa", "Well-drained sandy or clayey loam. pH 5.0-7.5.", "Farm Yard Manure"),
            ("Cabbage", "Brassica oleracea var. capitata", "Moist, sandy loam or clay loam rich in organic matter.", "Urea Nitrogen Booster"),
            ("Cauliflower", "Brassica oleracea var. botrytis", "Cool, moist, loamy soil with rich nutrients.", "Boron-enriched Compost"),
            ("Spinach", "Spinacia oleracea", "Moist, nitrogen-rich, well-drained loamy soil.", "Liquid Organic Fertilizer"),
            ("Carrot", "Daucus carota", "Deep, loose, well-drained sandy loam soils.", "Low-nitrogen Phosphate mix"),
            ("Radish", "Raphanus sativus", "Loose, well-drained, sandy loam soils. pH 6.0-7.5.", "Balanced NPK Mix"),
            ("Eggplant", "Solanum melongena", "Rich, fertile, well-drained loam. pH 5.5-6.8.", "Ammonium Sulfate"),
            ("Okra", "Abelmoschus esculentus", "Fertile, well-drained loamy soil. pH 6.0-6.8.", "Decomposed Cow Manure"),
            ("Cucumber", "Cucumis sativus", "Loose, warm sandy loam with good moisture retention.", "Bone Meal & Compost"),
            ("Watermelon", "Citrullus lanatus", "Deep, sandy loam, acidic to neutral pH 6.0-6.8.", "Nitrogen & Potash Mix"),
            ("Barley", "Hordeum vulgare", "Well-drained loamy to light clay soils. pH 7.0-8.0.", "NPK Balanced Mix"),
            ("Millet", "Pennisetum glaucum", "Sandy loam or light textured soils, highly drought tolerant.", "Bio-fertilizer booster"),
            ("Sorghum", "Sorghum bicolor", "Clayey loam, highly adaptable. pH 5.5-7.5.", "Superphosphate Blend"),
            ("Chickpea", "Cicer arietinum", "Medium to heavy clayey soils, well-aerated.", "Phosphorus Starter Mix"),
            ("Pigeon Pea", "Cajanus cajan", "Sandy loam to clay loam, requires excellent drainage.", "Rhizobium Bio-fertilizer"),
            ("Black Gram", "Vigna mungo", "Heavy clayey soils or black cotton soils.", "Single Super Phosphate"),
            ("Green Gram", "Vigna radiata", "Sandy loam to clay loam. pH 6.0-7.5.", "Rhizobium inoculation"),
            ("Lentil", "Lens culinaris", "Deep sandy loam or clayey loam, neutral pH.", "Phosphated manure mix"),
            ("Mustard", "Brassica juncea", "Clayey loam or sandy loam. pH 6.0-7.5.", "Sulfur-enriched NPK"),
            ("Sesame", "Sesamum indicum", "Well-drained, light to medium textured loamy soils.", "Organic compost booster"),
            ("Sunflower", "Helianthus annuus", "Deep, fertile, well-drained soils. pH 6.0-7.5.", "Boron & Nitrogen blend"),
            ("Safflower", "Carthamus tinctorius", "Deep, fertile, well-drained sandy loam soils.", "Ammonium Nitrate"),
            ("Castor", "Ricinus communis", "Sandy loam or deep red loam soils.", "Castor Cake fertilizer"),
            ("Linseed", "Linum usitatissimum", "Deep clayey loam or alluvial soils.", "NPK Starter Blend"),
            ("Coconut", "Cocos nucifera", "Alluvial, sandy or laterite soils. pH 5.2-8.0.", "Coconut Special NPK"),
            ("Arecanut", "Areca catechu", "Gravelly laterite or clayey loam soils.", "Organic Leaf mold mix"),
            ("Coffee", "Coffea arabica", "Deep, fertile, well-drained acidic soils. pH 5.0-6.0.", "Nitrogen-Potash Blend"),
            ("Tea", "Camellia sinensis", "Deep, acidic, well-drained forest loam. pH 4.5-5.5.", "Ammonium Sulfate mix"),
            ("Rubber", "Hevea brasiliensis", "Deep, well-drained, acidic laterite soils.", "NPK rubber booster"),
            ("Cardamom", "Elettaria cardamomum", "Forest loam rich in organic matter. pH 5.0-6.5.", "Organic Humus compost"),
            ("Black Pepper", "Piper nigrum", "Red laterite or clayey loam soils. pH 5.0-6.5.", "Farm Yard manure & Potash"),
            ("Coriander", "Coriandrum sativum", "Loamy or clayey soils rich in organic matter.", "Balanced NPK Starter"),
            ("Cumin", "Cuminum cyminum", "Sandy loam or loamy soils with good drainage.", "Superphosphate Mix"),
            ("Fennel", "Foeniculum vulgare", "Rich, well-drained loamy or sandy loam soils.", "NPK fertilizer blend"),
            ("Fenugreek", "Trigonella foenum-graecum", "Rich loamy soils with good organic matter.", "Bio-NPK Booster"),
            ("Nutmeg", "Myristica fragrans", "Clayey loam or laterite soils, moist and rich.", "Organic Neem cake"),
            ("Clove", "Syzygium aromaticum", "Rich loamy soils with good water logging control.", "Compost & Rock Phosphate"),
            ("Cinnamon", "Cinnamomum verum", "Sandy loam or laterite soils. pH 5.0-6.5.", "Composted leaf fertilizer"),
            ("Apple", "Malus domestica", "Deep, fertile, sandy loam to clay loam. pH 6.0-6.8.", "Fruit Tree NPK booster"),
            ("Pear", "Pyrus communis", "Deep, well-drained loamy soils. pH 6.0-7.0.", "Nitrogen & Calcium mix"),
            ("Peach", "Prunus persica", "Well-drained, sandy loam soils. pH 6.0-6.5.", "Fruit tree organic mix"),
            ("Plum", "Prunus domestica", "Deep, well-drained loamy soils with good humus.", "NPK + Micro-nutrients"),
            ("Mango", "Mangifera indica", "Deep, rich alluvial or loamy soils. pH 5.5-7.5.", "Mango Special NPK"),
            ("Banana", "Musa acuminata", "Rich, well-drained loamy or clayey loam. pH 6.0-7.5.", "Potash-Heavy Fertilizer"),
            ("Citrus", "Citrus sinensis", "Sandy loam or deep loamy soils. pH 5.5-7.0.", "Citrus special NPK"),
            ("Grapes", "Vitis vinifera", "Deep, well-drained gravelly or sandy loam.", "Potassium sulfate blend"),
            ("Guava", "Psidium guajava", "Deep loamy or alluvial soils. pH 4.5-8.2.", "NPK + Zinc sulfate"),
            ("Papaya", "Carica papaya", "Rich, sandy loam with excellent drainage. pH 6.0-6.5.", "Urea + Potash starter"),
            ("Pomegranate", "Punica granatum", "Deep loamy or sandy loam soils, adaptable.", "Organic manure + Potash"),
            ("Pineapple", "Ananas comosus", "Sandy loam, acidic and well-drained. pH 4.5-5.5.", "Sulfate of Ammonia"),
            ("Litchi", "Litchi chinensis", "Deep, fertile loamy or alluvial soils.", "Manure + Single Superphosphate"),
            ("Sapota", "Manilkara zapota", "Deep alluvial or sandy loam soils, adaptable.", "NPK + Micro-nutrients"),
            ("Jackfruit", "Artocarpus heterophyllus", "Rich, deep alluvial or loamy soils.", "Organic compost + Urea"),
            ("Cashew", "Anacardium occidentale", "Sandy, gravelly or laterite soils, low fertility.", "Rock phosphate + NPK"),
            ("Walnut", "Juglans regia", "Deep, rich, well-drained loamy soils.", "Nitrogen booster mix"),
            ("Almond", "Prunus dulcis", "Deep, well-drained loamy soils. pH 7.0-8.5.", "Potash-heavy NPK blend"),
            ("Strawberry", "Fragaria ananassa", "Sandy loam rich in organic matter. pH 5.5-6.5.", "Strawberry special NPK"),
            ("Sweet Potato", "Ipomoea batatas", "Sandy loam or light loamy soils. pH 5.5-6.5.", "Potash-rich organic mix"),
            ("Cassava", "Manihot esculenta", "Well-drained sandy loam or clay loam, low pH.", "NPK blend for root crops"),
            ("Yam", "Dioscorea alata", "Loose, deep sandy loam soils with organic material.", "Farm Yard Manure mix"),
            ("Taro", "Colocasia esculenta", "Moist, rich clayey loam, adaptable to wet soil.", "NPK Nitrogen booster"),
            ("Lettuce", "Lactuca sativa", "Rich, loose sandy loam with high nitrogen content.", "Liquid Fish emulsion"),
            ("Broccoli", "Brassica oleracea var. italica", "Cool, rich loamy soil with high moisture content.", "Boron NPK blend"),
            ("Celery", "Apium graveolens", "Rich, moist organic soil with high water retention.", "High-nitrogen liquid fertilizer"),
            ("Asparagus", "Asparagus officinalis", "Deep, sandy loam, loose texture. pH 6.5-7.5.", "Composted horse manure"),
            ("Peas", "Pisum sativum", "Well-drained sandy loam rich in organic matter.", "Rhizobium inoculation"),
            ("French Beans", "Phaseolus vulgaris", "Sandy loam or loamy soils. pH 6.0-7.0.", "NPK starter blend"),
            ("Broad Beans", "Vicia faba", "Heavy loamy soils with high moisture content.", "Phosphate fertilizer booster"),
            ("Soybeans", "Glycine soja", "Alluvial or loamy soils rich in humus.", "Rhizobium booster"),
            ("Cowpea", "Vigna unguiculata", "Sandy loam or clayey loam, adaptable. pH 5.5-6.5.", "SSP (Single Super Phosphate)"),
            ("Cluster Bean", "Cyamopsis tetragonoloba", "Alluvial or sandy soils, highly drought tolerant.", "Bio-fertilizer mix"),
            ("Pumpkin", "Cucurbita pepo", "Sandy loam rich in organic manure. pH 6.0-7.5.", "NPK + cow dung compost"),
            ("Bottle Gourd", "Lagenaria siceraria", "Rich loamy soils, requires moisture retention.", "Farm Yard Manure"),
            ("Bitter Gourd", "Momordica charantia", "Sandy loam or clayey loam. pH 6.0-7.0.", "Compost booster + Potash"),
            ("Ridge Gourd", "Luffa acutangula", "Sandy loam rich in organic humus. pH 6.0-7.5.", "Liquid organic fertilizer"),
            ("Sponge Gourd", "Luffa aegyptiaca", "Loamy soils with good water drainage capacity.", "NPK balanced mix"),
            ("Ash Gourd", "Benincasa hispida", "Alluvial sandy soils rich in organic matter.", "Manure + Single Superphosphate"),
            ("Snake Gourd", "Trichosanthes cucumerina", "Sandy loam or loamy soils with high organic matter.", "Farm Yard Manure + Potash"),
            ("Mint", "Mentha spicata", "Moist, rich loamy soil. pH 6.0-7.0.", "Liquid seaweed fertilizer"),
            ("Basil", "Ocimum basilicum", "Well-drained sandy loam. pH 5.5-6.5.", "Liquid organic NPK"),
            ("Thyme", "Thymus vulgaris", "Sandy, gravelly dry soil, low fertility.", "Compost mix"),
            ("Rosemary", "Salvia rosmarinus", "Sandy, dry, well-drained soil. pH 6.0-7.0.", "Low NPK organic blend"),
            ("Oregano", "Origanum vulgare", "Sandy, well-drained, rocky soil.", "Organic compost booster"),
            ("Sage", "Salvia officinalis", "Sandy loam, dry, well-drained soil.", "Liquid seaweed extract"),
            ("Parsley", "Petroselinum crispum", "Moist, rich, well-drained loamy soil.", "Balanced liquid NPK"),
            ("Chives", "Allium schoenoprasum", "Rich loamy soil with high organic content.", "NPK fertilizer mix"),
            ("Dill", "Anethum graveolens", "Sandy loam or loamy soil, well-drained.", "NPK Starter Blend")
        ]

        self.stdout.write(f"Seeding {len(crops_catalog)} crops...")

        for i, (name, sci_name, soil, fert_name) in enumerate(crops_catalog, 1):
            # Create crop
            crop = Crop.objects.create(
                name=name,
                scientific_name=sci_name,
                description=f"High quality {name} crop suitable for diverse agricultural zones.",
                description_en=f"High quality {name} crop suitable for diverse agricultural zones.",
                description_hi=f"विविध कृषि क्षेत्रों के लिए उपयुक्त उच्च गुणवत्ता वाली {name} फसल।",
                description_gu=f"વિવિધ કૃષિ ઝોન માટે યોગ્ય ઉચ્ચ ગુણવત્તાવાળા {name} પાક.",
                ideal_temp_min_c=float(random.randint(10, 18)),
                ideal_temp_max_c=float(random.randint(28, 38)),
                ideal_humidity_min=float(random.randint(40, 55)),
                ideal_humidity_max=float(random.randint(70, 90)),
                soil_type=soil,
                soil_type_en=soil,
                soil_type_hi=f"गुजरात क्षेत्र के लिए उपयुक्त मिट्टी: {soil}",
                soil_type_gu=f"ગુજરાત વિસ્તાર માટે યોગ્ય જમીન: {soil}"
            )

            # Get or create organic fertilizer for it
            fert, created = Fertilizer.objects.get_or_create(
                name=fert_name,
                defaults={
                    'fertilizer_type': 'organic',
                    'description': f"Specialized organic formulation designed to optimize {name} crop yields.",
                    'description_en': f"Specialized organic formulation designed to optimize {name} crop yields.",
                    'description_hi': f"{name} crop yield optimization organic blend.",
                    'description_gu': f"{name} પાકની ઉપજ વધારવા માટે જૈવિક મિશ્રણ.",
                    'usage_instructions': "Apply twice during the early vegetative and growth phases.",
                    'usage_instructions_en': "Apply twice during the early vegetative and growth phases.",
                    'usage_instructions_hi': "वानस्पतिक और विकास चरणों के दौरान दो बार लागू करें।",
                    'usage_instructions_gu': "પ્રારંભિક વનસ્પતિ અને વિકાસના તબક્કા દરમિયાન બે વાર લાગુ કરો."
                }
            )


            # Create 2 diseases for each crop
            diseases_info = [
                (f"{name} Leaf Spot", "Dark circular leaf spots on margins", "Fungal pathogen spore dispersion", "Apply appropriate fungicide spray"),
                (f"{name} Blight Sickness", "Severe brown lesions on stem and leaves", "Excessive moisture and bacterial buildup", "Remove infected foliage and use organic pesticide")
            ]
            for d_name, d_sym, d_cause, d_treat in diseases_info:
                dis = Disease.objects.create(
                    crop=crop,
                    name=d_name,
                    symptoms=d_sym,
                    symptoms_en=d_sym,
                    symptoms_hi=f"पत्ती का रंग बदल जाना और लक्षण: {d_sym}",
                    symptoms_gu=f"પાન પર ડાઘ પડવા અને લક્ષણ: {d_sym}",
                    causes=d_cause,
                    causes_en=d_cause,
                    causes_hi=f"रोग का मुख्य कारण: {d_cause}",
                    causes_gu=f"રોગ ફેલાવવાનું કારણ: {d_cause}",
                    treatment=d_treat,
                    treatment_en=d_treat,
                    treatment_hi=f"उपचार प्रक्रिया: {d_treat}",
                    treatment_gu=f"ઉપચાર પ્રક્રિયા: {d_treat}",
                    pesticides_recommended=f"Copper-based pesticide spray or organic sulfur compound",
                    pesticides_recommended_en="Copper-based pesticide spray or organic sulfur compound",
                    pesticides_recommended_hi="तांबा आधारित कीटनाशक स्प्रे या जैविक सल्फर यौगिक",
                    pesticides_recommended_gu="તાંબા આધારિત જંતુનાશક સ્પ્રે અથવા કાર્બનિક સલ્ફર સંયોજન"
                )
                dis.fertilizers_recommended.add(fert)

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(crops_catalog)} crops into the database!"))
