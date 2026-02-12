from flask import Flask, request, send_file, render_template, jsonify
import os
import zipfile
import json
import re
from werkzeug.utils import secure_filename
import tempfile
from deep_translator import GoogleTranslator

import logging
import time
from datetime import datetime
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='static')

# Configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    
ALLOWED_EXTENSIONS = {'docx'}
MASTER_LIBRARY = 'master_library.json'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files():
    """Delete files older than 60 seconds for privacy"""
    try:
        now = time.time()
        cutoff = 60  # 1 minute retention
        count = 0
        for f in os.listdir(UPLOAD_FOLDER):
            path = os.path.join(UPLOAD_FOLDER, f)
            if os.stat(path).st_mtime < now - cutoff:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                count += 1
        if count > 0:
            logger.info(f"Cleaned up {count} old files/dirs")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

def log_upload(filename):
    """Log upload event for audit"""
    try:
        with open('uploads.log', 'a') as f:
            f.write(f"{datetime.now().isoformat()} - UPLOAD - {filename}\n")
    except Exception as e:
        logger.error(f"Logging error: {e}")

def get_win_path(unix_path):
    """Converts a WSL path to a Windows path"""
    abs_path = os.path.abspath(unix_path)
    if abs_path.startswith("/mnt/"):
        parts = abs_path.split("/")
        drive_letter = parts[2].upper()
        win_path = f"{drive_letter}:\\" + "\\".join(parts[3:])
        return win_path
    return abs_path

def load_master_library(library_path):
    if os.path.exists(library_path):
        try:
            with open(library_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_master_library(library_path, data):
    clean_data = {k: v for k, v in data.items() if isinstance(v, str) and v.strip() != ""}
    with open(library_path, 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, indent=4, ensure_ascii=False)

def translate_docx(source_docx, translation_map_path, output_docx):
    """Translate DOCX file using the translation map"""
    try:
        with open(translation_map_path, 'r', encoding='utf-8') as f:
            translation_map = json.load(f)
    except Exception as e:
        raise Exception(f"Error loading translation map: {e}")

    # Update master library
    master_lib = load_master_library(MASTER_LIBRARY)
    for k, v in translation_map.items():
        if v and v.strip() != "":
            if k not in master_lib:
                master_lib[k] = v
    save_master_library(MASTER_LIBRARY, master_lib)

    # Translate DOCX
    def sub_xml(content, trans_map):
        xml_str = content.decode('utf-8')
        def replace_para(match):
            para_xml = match.group(0)
            t_contents = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', para_xml)
            para_text = "".join(t_contents)
            translation = trans_map.get(para_text) or trans_map.get(para_text.strip())
            
            if translation and isinstance(translation, str) and translation.strip() != "":
                state = {'first': True}
                def sub_t(t_match):
                    tag_start = t_match.group(1)
                    if state['first']:
                        state['first'] = False
                        safe = translation.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')
                        return f'<w:t{tag_start}>{safe}</w:t>'
                    return f'<w:t{tag_start}></w:t>'
                return re.sub(r'<w:t([^>]*)>([^<]*)</w:t>', sub_t, para_xml)
            return para_xml
        return re.sub(r'<w:p\b[^>]*>.*?</w:p>', replace_para, xml_str, flags=re.DOTALL).encode('utf-8')

    target_pattern = re.compile(r'word/(document|header|footer)\d*\.xml')
    with zipfile.ZipFile(source_docx, 'r') as zin, zipfile.ZipFile(output_docx, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            content = zin.read(info.filename)
            if target_pattern.match(info.filename):
                zout.writestr(info.filename, sub_xml(content, translation_map))
            else:
                zout.writestr(info, content)

def extract_strings(source_docx, output_json):
    """Extract unique text segments from DOCX for translation"""
    target_pattern = re.compile(r'word/(document|header|footer)\d*\.xml')
    unique_strings = []
    
    master_lib = load_master_library(MASTER_LIBRARY)

    with zipfile.ZipFile(source_docx, 'r') as z:
        for info in z.infolist():
            if target_pattern.match(info.filename):
                content = z.read(info.filename).decode('utf-8')
                paragraphs = re.findall(r'<w:p\b[^>]*>.*?</w:p>', content, flags=re.DOTALL)
                for para in paragraphs:
                    t_contents = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', para)
                    para_text = "".join(t_contents).strip()
                    if para_text and para_text not in unique_strings:
                        unique_strings.append(para_text)
    
    # Build map: Check Master Lib first
    mapping = {}
    missing_strings = []
    
    for s in unique_strings:
        clean_s = s.strip()
        if not clean_s:
            continue
            
        trans = master_lib.get(s) or master_lib.get(clean_s)
        if trans:
            mapping[s] = trans
        else:
            # Check if it's just a number or simple symbol
            if clean_s.replace('.', '').replace(',', '').isdigit() or len(clean_s) < 2:
                mapping[s] = s
            else:
                missing_strings.append(s)
    
    # Translate missing strings
    if missing_strings:
        print(f"Translating {len(missing_strings)} new strings...")
        try:
            translator = GoogleTranslator(source='fr', target='en')
            
            # process in chunks to show progress/avoid timeouts
            for i, s in enumerate(missing_strings):
                try:
                    # preserve leading/trailing whitespace if needed, but usually stripped for translation
                    translated = translator.translate(s.strip())
                    
                    # consistency check
                    if translated:
                        # Restore original whitespace pattern if possible? 
                        # For now, just map string to translated
                        mapping[s] = translated
                        master_lib[s] = translated
                    else:
                        mapping[s] = s
                except Exception as e:
                    print(f"Translation failed for '{s[:20]}...': {e}")
                    mapping[s] = s
            
            # Save updated master library
            save_master_library(MASTER_LIBRARY, master_lib)
            print("Master library updated with new translations.")
            
        except Exception as e:
            print(f"Translation setup failed: {e}")
            for s in missing_strings:
                mapping[s] = s

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=4, ensure_ascii=False)
    
    return mapping

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only DOCX files are allowed'}), 400
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        
        # Log and cleanup before saving
        log_upload(filename)
        cleanup_old_files()
        
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)
        logger.info(f"File saved: {upload_path}")
        
        # Extract strings and create translation map
        base_name = os.path.splitext(filename)[0]
        map_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_name}.json")
        translation_map = extract_strings(upload_path, map_path)
        
        # Generate output filename
        if re.search(r'[_.-]FR$', base_name, re.I):
            output_base = re.sub(r'([_.-])FR$', r'\1EN', base_name, flags=re.I)
        else:
            output_base = f"{base_name}_EN"
        
        output_docx = os.path.join(app.config['UPLOAD_FOLDER'], f"{output_base}.docx")
        
        # Translate DOCX
        translate_docx(upload_path, map_path, output_docx)
        
        return jsonify({
            'success': True,
            'download_url': f'/download/{os.path.basename(output_docx)}',
            'filename': os.path.basename(output_docx)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Master library: {MASTER_LIBRARY}")
    print("Starting Flask server on http://localhost:5000")
    # Debug=False for production readiness testing, though Gunicorn overrides this
    app.run(debug=False, host='0.0.0.0', port=5000)
