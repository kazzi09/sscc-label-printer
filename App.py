from flask import Flask, request, jsonify, render_template_string
from PIL import Image, ImageDraw, ImageFont
import os
import socket

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SSCC Label Printer</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: 0 auto; }
        h1 { color: #333; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], input[type="number"] { 
            width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; 
        }
        button { 
            background: #007bff; color: white; padding: 15px 30px; 
            border: none; border-radius: 4px; cursor: pointer; font-size: 16px; 
        }
        button:hover { background: #0056b3; }
        .result { margin-top: 20px; padding: 15px; background: #f0f0f0; border-radius: 4px; }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <h1>SSCC Etiket Printer</h1>
    <form id="labelForm">
        <div class="form-group">
            <label>Artikelnr:</label>
            <input type="text" name="artikel_no" value="1100" required>
        </div>
        <div class="form-group">
            <label>Omschrijving:</label>
            <input type="text" name="artikel_ad" value="Don Caffe" required>
        </div>
        <div class="form-group">
            <label>Lotnummer:</label>
            <input type="text" name="lot_no" value="12323" required>
        </div>
        <div class="form-group">
            <label>GTIN (14 cijfers):</label>
            <input type="text" name="gtin" value="05304000433598" maxlength="14" required>
        </div>
        <div class="form-group">
            <label>THT (YYMMDD):</label>
            <input type="text" name="tht" value="271227" maxlength="6" required>
        </div>
        <div class="form-group">
            <label>SSCC (18 cijfers):</label>
            <input type="text" name="sscc" value="387171541001429753" maxlength="18" required>
        </div>
        <div class="form-group">
            <label>Zebra Printer IP:</label>
            <input type="text" name="printer_ip" placeholder="192.168.1.100" value="192.168.1.100">
        </div>
        <div class="form-group">
            <label>Printer Poort:</label>
            <input type="number" name="printer_port" value="9100">
        </div>
        <button type="submit">Print Etiketten</button>
    </form>
    <div id="result"></div>
    
    <script>
        document.getElementById('labelForm').onsubmit = async function(e) {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            
            document.getElementById('result').innerHTML = 'Bezig met printen...';
            
            try {
                const response = await fetch('/print', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                document.getElementById('result').innerHTML = 
                    '<div class="' + (result.success ? 'success' : 'error') + '">' + 
                    result.message + '</div>';
            } catch (err) {
                document.getElementById('result').innerHTML = 
                    '<div class="error">Fout: ' + err.message + '</div>';
            }
        };
    </script>
</body>
</html>
"""

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
            font = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()
            
        bbox = draw.textbbox((0, 0), data, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, height - 25), data, fill='black', font=font)
        
        return img

class SSCCGenerator:
    def create_label(self, data):
        label_width = 600
        label_height = 950
        
        label = Image.new('RGB', (label_width, label_height), 'white')
        draw = ImageDraw.Draw(label)
        
        try:
            font_normal = ImageFont.truetype("arial.ttf", 14)
            font_small = ImageFont.truetype("arial.ttf", 11)
        except:
            font_normal = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Header
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
        
        # Barkod 1: SSCC + 37 (1 stuk)
        sscc_37_1 = f"(00){data['sscc']}(37)1"
        barcode1 = SimpleBarcode.generate(sscc_37_1.replace('(', '').replace(')', ''), width=500, height=100)
        label.paste(barcode1, (50, y_pos))
        y_pos += 110
        draw.text((50, y_pos), "SSCC + Aantal colli: 1 stuk", fill='black', font=font_normal)
        y_pos += 20
        draw.text((50, y_pos), sscc_37_1, fill='black', font=font_small)
        y_pos += 50
        
        draw.line([(50, y_pos), (label_width-50, y_pos)], fill='gray', width=1)
        y_pos += 30
        
        # Barkod 2: Sadece SSCC
        sscc_only = f"(00){data['sscc']}"
        barcode2 = SimpleBarcode.generate(sscc_only.replace('(', '').replace(')', ''), width=500, height=100)
        label.paste(barcode2, (50, y_pos))
        y_pos += 110
        draw.text((50, y_pos), "SSCC (alleen)", fill='black', font=font_normal)
        y_pos += 20
        draw.text((50, y_pos), sscc_only, fill='black', font=font_small)
        y_pos += 50
        
        draw.line([(50, y_pos), (label_width-50, y_pos)], fill='gray', width=1)
        y_pos += 30
        
        # Barkod 3: SSCC + 37 (12 colli)
        sscc_37_12 = f"(00){data['sscc']}(37)12"
        barcode3 = SimpleBarcode.generate(sscc_37_12.replace('(', '').replace(')', ''), width=500, height=100)
        label.paste(barcode3, (50, y_pos))
        y_pos += 110
        draw.text((50, y_pos), "SSCC + Aantal colli: 12 stuks", fill='black', font=font_normal)
        y_pos += 20
        draw.text((50, y_pos), sscc_37_12, fill='black', font=font_small)
        y_pos += 40
        
        draw.line([(30, y_pos), (label_width-30, y_pos)], fill='black', width=2)
        y_pos += 20
        draw.text((50, y_pos), f"SSCC: {data['sscc']}", fill='black', font=font_normal)
        
        return label
    
    def generate_zpl(self, data):
        """Zebra ZPL kodu oluştur"""
        zpl = []
        zpl.append('^XA')
        zpl.append('^MMT')
        zpl.append('^PW812')
        zpl.append('^LL1218')
        zpl.append('^LS0')
        zpl.append('^CI28')
        
        # Header
        zpl.append(f'^FO30,30^A0N,28,28^FDArtikelnr: {data["artikel_no"]}^FS')
        zpl.append(f'^FO30,70^A0N,22,22^FDOmschrijving: {data["artikel_ad"]}^FS')
        zpl.append(f'^FO30,105^A0N,22,22^FDLotnummer: {data["lot_no"]}^FS')
        zpl.append(f'^FO30,140^A0N,22,22^FDTHT: {data["tht"]}^FS')
        zpl.append('^FO30,210^GB752,3,3^FS')
        
        # Barkod 1
        zpl.append(f'^FO50,230^BY3,3,120^BCN,120,Y,N,N^FD>;>800{data["sscc"]}371^FS')
        zpl.append('^FO50,370^A0N,20,20^FDSSCC + Aantal colli: 1 stuk^FS')
        zpl.append(f'^FO50,400^A0N,14,14^FD(00){data["sscc"]}(37)1^FS')
        zpl.append('^FO30,440^GB752,1,1^FS')
        zpl.append('^XZ')
        
        # Barkod 2
        zpl.append('^XA')
        zpl.append('^MMT^PW812^LL1218^LS0^CI28')
        zpl.append(f'^FO30,30^A0N,28,28^FDArtikelnr: {data["artikel_no"]}^FS')
        zpl.append(f'^FO30,70^A0N,22,22^FDOmschrijving: {data["artikel_ad"]}^FS')
        zpl.append(f'^FO30,210^GB752,3,3^FS')
        zpl.append(f'^FO50,230^BY3,3,120^BCN,120,Y,N,N^FD>;>800{data["sscc"]}^FS')
        zpl.append('^FO50,370^A0N,20,20^FDSSCC (alleen)^FS')
        zpl.append('^XZ')
        
        # Barkod 3
        zpl.append('^XA')
        zpl.append('^MMT^PW812^LL1218^LS0^CI28')
        zpl.append(f'^FO30,30^A0N,28,28^FDArtikelnr: {data["artikel_no"]}^FS')
        zpl.append(f'^FO30,70^A0N,22,22^FDOmschrijving: {data["artikel_ad"]}^FS')
        zpl.append(f'^FO30,210^GB752,3,3^FS')
        zpl.append(f'^FO50,230^BY3,3,120^BCN,120,Y,N,N^FD>;>800{data["sscc"]}3712^FS')
        zpl.append('^FO50,370^A0N,20,20^FDSSCC + Aantal colli: 12 stuks^FS')
        zpl.append('^FO30,440^GB752,3,3^FS')
        zpl.append(f'^FO50,470^A0N,24,24^FDSSCC: {data["sscc"]}^FS')
        zpl.append('^XZ')
        
        return '\n'.join(zpl)

generator = SSCCGenerator()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/print', methods=['POST'])
def print_label():
    try:
        data = request.json
        
        # ZPL oluştur
        zpl_code = generator.generate_zpl(data)
        
        # Yazıcıya gönder
        printer_ip = data.get('printer_ip', '192.168.1.100')
        printer_port = int(data.get('printer_port', 9100))
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((printer_ip, printer_port))
            sock.send(zpl_code.encode('utf-8'))
            sock.close()
            
            return jsonify({
                'success': True,
                'message': f'3 etiketten verzonden naar {printer_ip}:{printer_port}'
            })
        except Exception as e:
            # Yazıcıya bağlanamazsa ZPL dosyası olarak kaydet
            filename = f"SSCC_{data['sscc']}.zpl"
            with open(filename, 'w') as f:
                f.write(zpl_code)
            
            return jsonify({
                'success': True,
                'message': f'Printer niet bereikbaar. ZPL opgeslagen als: {filename}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fout: {str(e)}'
        })

if __name__ == '__main__':
    print("SSCC Label Printer başlatılıyor...")
    print("Tarayıcıda aç: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
