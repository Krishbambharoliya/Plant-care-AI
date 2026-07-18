import os
import sys
import django

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plantcare.settings')
django.setup()

from library.models import Crop
from fpdf import FPDF

class CropsCatalogPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(17, 24, 39)
        self.cell(0, 10, "PlantCare AI - Complete Crops Catalog Reference Manual", new_x='LMARGIN', new_y='NEXT')
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, "Detailed botanical names list of all crops in the database library", new_x='LMARGIN', new_y='NEXT')
        self.set_draw_color(17, 24, 39)
        self.line(10, 22, 200, 22)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align='C')

pdf = CropsCatalogPDF()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

crops = Crop.objects.all().order_by('name')
for i, crop in enumerate(crops, start=1):
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(16, 124, 65) # Green
    pdf.cell(0, 8, f"{i}. {crop.name}", new_x='LMARGIN', new_y='NEXT')
    pdf.ln(1)

output_dir = r"D:\Project SEM-4\ana"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

output_path = os.path.join(output_dir, 'Crops_List.pdf')
pdf.output(output_path)
print(f"Successfully generated complete crops list PDF at: {output_path}")
