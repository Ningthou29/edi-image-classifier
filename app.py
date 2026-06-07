from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import cv2
import numpy as np
import tempfile
import traceback

app = Flask(__name__)
CORS(app)

class ImageForensicsDetector:
    """Detects image manipulation using forensic techniques"""
    
    def error_level_analysis(self, image_path):
        """Error Level Analysis - higher score = more likely edited"""
        try:
            original = cv2.imread(image_path)
            if original is None:
                print(f"❌ Failed to read image at: {image_path}")
                return 0.5
            
            temp_path = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False).name
            cv2.imwrite(temp_path, original, [cv2.IMWRITE_JPEG_QUALITY, 85])
            recompressed = cv2.imread(temp_path)
            diff = cv2.absdiff(original.astype(np.float32), recompressed.astype(np.float32))
            ela_score = float(np.mean(diff) / 255.0)  # Convert to float
            
            os.unlink(temp_path)
            print(f"📊 ELA Score: {ela_score:.3f}")
            return ela_score
        except Exception as e:
            print(f"❌ ELA Error: {str(e)}")
            return 0.5
    
    def noise_inconsistency(self, image_path):
        """Detect inconsistent noise patterns - higher score = more likely edited"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return 0.5
                
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            
            h = h - (h % 2)
            w = w - (w % 2)
            gray = gray[:h, :w]
            
            quadrants = [
                gray[:h//2, :w//2],
                gray[:h//2, w//2:],
                gray[h//2:, :w//2],
                gray[h//2:, w//2:]
            ]
            
            variances = []
            for quad in quadrants:
                if quad.size > 0:
                    denoised = cv2.medianBlur(quad, 5)
                    noise = quad.astype(np.float32) - denoised.astype(np.float32)
                    variances.append(float(np.var(noise)))  # Convert to float
            
            if len(variances) < 2:
                return 0.5
                
            inconsistency = float(np.std(variances) / (np.mean(variances) + 0.001))  # Convert to float
            noise_score = min(inconsistency / 2, 1.0)
            
            print(f"🎲 Noise Score: {noise_score:.3f}")
            return noise_score
        except Exception as e:
            print(f"❌ Noise Error: {str(e)}")
            return 0.5
    
    def edge_artifacts(self, image_path):
        """Detect blurry edges - higher score = more likely edited"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return 0.5
                
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            kernel = np.ones((10, 10), np.float32) / 100
            smoothed = cv2.filter2D(edges.astype(np.float32), -1, kernel)
            edge_score = float(np.mean(smoothed) / 255.0)  # Convert to float
            edge_score = min(edge_score, 1.0)
            
            print(f"🔍 Edge Score: {edge_score:.3f}")
            return edge_score
        except Exception as e:
            print(f"❌ Edge Error: {str(e)}")
            return 0.5
    
    def color_inconsistency(self, image_path):
        """Detect color histogram anomalies - higher score = more likely edited"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return 0.5
                
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            
            hist_l = cv2.calcHist([l_channel], [0], None, [256], [0, 256])
            hist_a = cv2.calcHist([a_channel], [0], None, [256], [0, 256])
            hist_b = cv2.calcHist([b_channel], [0], None, [256], [0, 256])
            
            empty_bins = float(np.sum(hist_l < 10) + np.sum(hist_a < 10) + np.sum(hist_b < 10))  # Convert to float
            color_score = empty_bins / (3 * 256)
            color_score = min(color_score, 1.0)
            
            print(f"🎨 Color Score: {color_score:.3f}")
            return color_score
        except Exception as e:
            print(f"❌ Color Error: {str(e)}")
            return 0.5
    
    def analyze(self, image_path):
        """Run all forensic tests and return combined result"""
        print("\n" + "="*50)
        print("🔍 Starting Analysis...")
        print("="*50)
        
        ela_score = self.error_level_analysis(image_path)
        noise_score = self.noise_inconsistency(image_path)
        edge_score = self.edge_artifacts(image_path)
        color_score = self.color_inconsistency(image_path)
        
        manipulation_score = (
            ela_score * 0.40 + 
            noise_score * 0.25 + 
            edge_score * 0.20 + 
            color_score * 0.15
        )
        
        print("-"*50)
        print(f"📈 Final Manipulation Score: {manipulation_score:.3f}")
        print(f"🎯 Threshold: 0.55")
        
        if manipulation_score > 0.55:
            label = "EDITED"
            confidence = min(manipulation_score * 100, 99)
            explanation = "Image shows signs of digital manipulation"
            print(f"⚠️ VERDICT: EDITED with {confidence:.1f}% confidence")
        else:
            label = "AUTHENTIC"
            confidence = (1 - manipulation_score) * 100
            explanation = "No significant manipulation detected"
            print(f"✅ VERDICT: AUTHENTIC with {confidence:.1f}% confidence")
        
        print("="*50 + "\n")
        
        # Convert all numpy types to Python native types for JSON serialization
        return {
            'label': label,
            'confidence': f"{float(confidence):.1f}%",
            'raw_score': float(round(manipulation_score, 3)),
            'explanation': explanation,
            'details': {
                'ela': float(round(ela_score * 100, 1)),
                'noise': float(round(noise_score * 100, 1)),
                'edge': float(round(edge_score * 100, 1)),
                'color': float(round(color_score * 100, 1))
            }
        }

detector = ImageForensicsDetector()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_image():
    print("\n" + "🚀"*20)
    print("NEW ANALYSIS REQUEST RECEIVED")
    print("🚀"*20)
    
    if 'image' not in request.files:
        print("❌ No image file in request")
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    print(f"📁 Received file: {file.filename}")
    
    if file.filename == '':
        print("❌ Empty filename")
        return jsonify({'error': 'No file selected'}), 400
    
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        print(f"❌ Unsupported file type: {file_ext}")
        return jsonify({'error': 'Unsupported file type. Use JPG, PNG, or WEBP'}), 400
    
    temp_file = tempfile.NamedTemporaryFile(suffix=file_ext, delete=False)
    file.save(temp_file.name)
    temp_file.close()
    
    print(f"💾 Saved to temp file: {temp_file.name}")
    
    try:
        result = detector.analyze(temp_file.name)
        print(f"📤 Sending response: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500
        
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
            print(f"🗑️ Cleaned up temp file")

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🔍 IMAGE FORENSICS DETECTOR")
    print("="*60)
    print(f"📍 Local URL:    http://127.0.0.1:5000")
    print(f"💻 Running on:   CPU only (no GPU required)")
    print(f"📊 Detection:    ELA | Noise | Edge | Color")
    print("="*60)
    print("📝 Debug mode: ON - Check terminal for detailed output")
    print("Press CTRL+C to stop\n")
    
    app.run(
        debug=True,
        host='127.0.0.1',
        port=5000,
        threaded=True
    )