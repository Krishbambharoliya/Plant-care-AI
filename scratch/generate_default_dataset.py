import csv
import random
import os

def generate_dataset():
    os.makedirs('media/datasets', exist_ok=True)
    file_path = 'media/datasets/crop_yield_data.csv'
    
    crops = ["Rice", "Wheat", "Tomato", "Brinjal", "Potato", "Banana", "Cotton", "Sugarcane", "Mango", "Coffee"]
    
    headers = [
        "Year", "Crop_Type", "Average_Temperature_C", "Average_Humidity", 
        "Rainfall_mm", "Pesticide_Usage_kg", "Soil_pH", "Yield_Tons", "Market_Price_INR"
    ]
    
    with open(file_path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        # Generate 150 data points
        for i in range(150):
            year = random.randint(2015, 2026)
            crop = random.choice(crops)
            temp = round(random.uniform(18.0, 36.0), 2)
            humidity = round(random.uniform(40.0, 85.0), 2)
            rainfall = round(random.uniform(100.0, 1200.0), 2)
            pesticide = round(random.uniform(1.0, 15.0), 2)
            ph = round(random.uniform(5.5, 7.8), 2)
            
            # Formulate yield based on climate/pH features
            base_yield = 2.0
            if temp > 22 and temp < 30:
                base_yield += 1.5
            if 6.0 <= ph <= 7.2:
                base_yield += 0.8
            if humidity > 60:
                base_yield += 0.7
            
            yield_tons = round(base_yield + random.uniform(-0.5, 0.5), 2)
            price = int(yield_tons * random.uniform(8000, 12000))
            
            writer.writerow([year, crop, temp, humidity, rainfall, pesticide, ph, yield_tons, price])
            
    print(f"Generated mock dataset at {file_path}")

if __name__ == '__main__':
    generate_dataset()
