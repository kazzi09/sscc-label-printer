
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
import os

app = Flask(__name__)

class SimpleBarcode:
    @staticmethod
    def generate(data, width=500, height=100):
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)

        bar_width = width // (len(data) * 10 + 20)
        if bar_width < 2:
            bar_width = 2

        x = 20
        for i, char in enumerate(data):
            pattern = [1, 0, 1, 1, 0, 1, 0, 0, 1, 0]
            for bit in pattern:
                if bit == 1:
                    draw.rectangle([x, 10, x + bar_width, height - 30], fill='black')
                x += bar_width + 1

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), data, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, height - 25), data, fill='black', font=font)

        return img

class SSCCBarcodeGenerator:
    def create_gs1_barcode(self, data, height=100):
        gs1_data = data.replace('(', '').replace(')', '')
        return SimpleBarcode.generate(gs1_data, width=500, height=height)

    def create_label(self, data, output_path="sscc_label.png"):
        label_width = 600
        label_height = 950

        label = Image.new('RGB', (label_width, label_height), 'white')
        draw = ImageDraw.Draw(label)

        try:
            font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        except:
            font_normal = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Üst bilgiler
        y_pos = 20
        draw.text((30, y_pos), f"Artikelnr: {data['artikel_no']}", fill='black', font=font_normal)
        y_pos += 25
        draw.text((30, y_pos), f"Omschrijving: {data['artikel_ad']}", fill='black', font=font_normal)
        y_pos += 25
        draw.text((30, y_pos), f"Lotnummer: {data['lot_no']}", fill='black', font=font_normal)
        y_pos += 25
        draw.text((30, y_pos), f"THT: {data['tht']}", fill='black', font=font_normal)
        y_pos += 25
        draw.text((30, y_pos), f"GTIN: {data['gtin']}", fill='black', font=font_small)
        y_pos += 35

        draw.line([(30, y_pos), (label_width-30, y_pos)], fill='black', width=2)
        y_pos += 25

        # Barkod 1
        sscc_37_1 = f"(00){data['sscc']}(37)1"
        barcode1 = self.create_gs1_barcode(sscc_37_1, height=100)
        label.paste(barcode1, (50, y_pos))
        y_pos += 110
        draw.text((50, y_pos), f"SSCC + Aantal colli: 1 stuk", fill='black', font=font_normal)
        y_pos += 20
        draw.text((50, y_pos), sscc_37_1, fill='black', font=font_small)
        y_pos += 50

        draw.line([(50, y_pos), (label_width-50, y_pos)], fill='gray', width=1)
        y_pos += 30

        # Barkod 2
        sscc_only = f"(00){data['sscc']}"
        barcode2 = self.create_gs1_barcode(sscc_only, height=100)
        label.paste(barcode2, (50, y_pos))
        y_pos += 110
        draw.text((50, y_pos), f"SSCC (alleen)", fill='black', font=font_normal)
        y_pos += 20
        draw.text((50, y_pos), sscc_only, fill='black', font=font_small)
        y_pos += 50

        draw.line([(50, y_pos), (label_width-50, y_pos)], fill='gray', width=1)
        y_pos += 30

        # Barkod 3
        sscc_37_12 = f"(00){data['sscc']}(37)12"
        barcode3 = self.create_gs1_barcode(sscc_37_12, height=100)
        label.paste(barcode3, (50, y_pos))
        y_pos += 110
        draw.text((50, y_pos), f"SSCC + Aantal colli: 12 stuks", fill='black', font=font_normal)
        y_pos += 20
        draw.text((50, y_pos), sscc_37_12, fill='black', font=font_small)
        y_pos += 40

        draw.line([(30, y_pos), (label_width-30, y_pos)], fill='black', width=2)
        y_pos += 20
        draw.text((50, y_pos), f"SSCC: {data['sscc']}", fill='black', font=font_normal)

        label.save(output_path, dpi=(300, 300))
        return output_path

generator = SSCCBarcodeGenerator()

@app.route('/print-sscc', methods=['POST'])
def print_sscc():
    """BC'den gelen veriyi al ve etiket oluştur"""
    data = request.json

    required_fields = ['artikel_no', 'artikel_ad', 'lot_no', 'gtin', 'tht', 'sscc']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    try:
        filename = f"label_{data['sscc']}.png"
        output_path = generator.create_label(data, filename)

        # Buraya yazdırma komutu eklenebilir
        # os.system(f"lp {output_path}")  # Linux yazdırma

        return jsonify({
            "status": "success",
            "message": "Etiket oluşturuldu",
            "file": output_path,
            "data": {
                "sscc": data['sscc'],
                "barcodes": [
                    f"(00){data['sscc']}(37)1",
                    f"(00){data['sscc']}",
                    f"(00){data['sscc']}(37)12"
                ]
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "OK"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
