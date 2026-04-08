from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import os

app = Flask(__name__)

class SSCCBarcodeGenerator:
    
    def create_gs1_barcode_image(self, gs1_data, width=600, height=100):
        """
        GS1-128 formatında barkod oluşturur.
        gs1_data: Parantezsiz, FNC1 ayracı ile formatlanmış ham veri
        Örnek: '001293293293293933F13714' 
        (FNC1 yerine özel karakter '\xf1' kullanılır)
        """
        # GS1-128 için: AI'lar arasında FNC1 (\xf1) ayracı olmalı
        # Örnek: (00)123... + (37)14  →  "00123...\xf13714"
        
        options = {
            'module_width': 0.3,
            'module_height': height - 20,
            'font_size': 10,
            'text_distance': 5,
            'quiet_zone': 6,
            'write_text': False  # Biz manuel ekleyeceğiz
        }
        
        code128 = barcode.get_barcode_class('code128')
        barcode_img = code128(gs1_data, writer=ImageWriter())
        
        from io import BytesIO
        buffered = BytesIO()
        barcode_img.write(buffered, options=options)
        buffered.seek(0)
        
        return Image.open(buffered)

    def format_gs1_data(self, sscc, quantity=None):
        """
        GS1 verisini doğru formatta hazırlar.
        SSCC 18 haneli olmalı, eksikse uyarı ver.
        """
        # SSCC'yi temizle ve 18 haneye tamamla (örnek mantık)
        sscc_clean = ''.join(filter(str.isdigit, sscc))
        if len(sscc_clean) < 18:
            print(f"⚠️ UYARI: SSCC 18 haneli olmalı! Mevcut: {len(sscc_clean)} hane")
            # Eksikse başına 0 ekle (gerçek uygulamada check digit hesaplanmalı)
            sscc_clean = sscc_clean.zfill(18)
        
        # GS1-128 format: AI + veri + FNC1 (\xf1) + AI + veri
        if quantity:
            return f"00{sscc_clean}\xf137{quantity}"
        return f"00{sscc_clean}"

    def create_label(self, data, output_path="sscc_label.png"):
        label_width = 600
        label_height = 950
        label = Image.new('RGB', (label_width, label_height), 'white')
        draw = ImageDraw.Draw(label)

        # Font ayarları
        try:
            font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        except:
            font_normal = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Üst bilgiler
        y_pos = 20
        for key, label_text in [('artikel_no', 'Artikelnr'), ('artikel_ad', 'Omschrijving'), 
                               ('lot_no', 'Lotnummer'), ('tht', 'THT'), ('gtin', 'GTIN')]:
            draw.text((30, y_pos), f"{label_text}: {data.get(key, '')}", fill='black', font=font_normal if key != 'gtin' else font_small)
            y_pos += 25
        
        draw.line([(30, y_pos), (label_width-30, y_pos)], fill='black', width=2)
        y_pos += 25

        # Barkod 1: SSCC + (37)1
        gs1_data_1 = self.format_gs1_data(data['sscc'], quantity='1')
        barcode1 = self.create_gs1_barcode_image(gs1_data_1, height=100)
        # Barkodu ortala
        bx = (label_width - barcode1.width) // 2
        label.paste(barcode1, (bx, y_pos))
        y_pos += 110
        draw.text((30, y_pos), f"SSCC + Aantal colli: 1 stuk", fill='black', font=font_normal)
        draw.text((30, y_pos+20), f"(00){data['sscc']}(37)1", fill='black', font=font_small)
        y_pos += 50

        draw.line([(30, y_pos), (label_width-30, y_pos)], fill='gray', width=1)
        y_pos += 30

        # Barkod 2: Sadece SSCC
        gs1_data_2 = self.format_gs1_data(data['sscc'])
        barcode2 = self.create_gs1_barcode_image(gs1_data_2, height=100)
        bx = (label_width - barcode2.width) // 2
        label.paste(barcode2, (bx, y_pos))
        y_pos += 110
        draw.text((30, y_pos), f"SSCC (alleen)", fill='black', font=font_normal)
        draw.text((30, y_pos+20), f"(00){data['sscc']}", fill='black', font=font_small)
        y_pos += 50

        draw.line([(30, y_pos), (label_width-30, y_pos)], fill='gray', width=1)
        y_pos += 30

        # Barkod 3: SSCC + (37)12
        gs1_data_3 = self.format_gs1_data(data['sscc'], quantity='12')
        barcode3 = self.create_gs1_barcode_image(gs1_data_3, height=100)
        bx = (label_width - barcode3.width) // 2
        label.paste(barcode3, (bx, y_pos))
        y_pos += 110
        draw.text((30, y_pos), f"SSCC + Aantal colli: 12 stuks", fill='black', font=font_normal)
        draw.text((30, y_pos+20), f"(00){data['sscc']}(37)12", fill='black', font=font_small)
        y_pos += 40

        draw.line([(30, y_pos), (label_width-30, y_pos)], fill='black', width=2)
        
        label.save(output_path, dpi=(300, 300))
        return output_path

generator = SSCCBarcodeGenerator()

@app.route('/print-sscc', methods=['POST'])
def print_sscc():
    data = request.json
    required_fields = ['artikel_no', 'artikel_ad', 'lot_no', 'gtin', 'tht', 'sscc']
    
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    try:
        filename = f"label_{data['sscc']}.png"
        output_path = generator.create_label(data, filename)
        
        return jsonify({
            "status": "success",
            "message": "Etiket oluşturuldu",
            "file": output_path,
            "gs1_encoded": [
                generator.format_gs1_data(data['sscc'], '1'),
                generator.format_gs1_data(data['sscc']),
                generator.format_gs1_data(data['sscc'], '12')
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "OK"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
