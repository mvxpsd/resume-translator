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
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
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
        cutoff = 60  # 60 seconds retention (strict privacy)
        count = 0
        for f in os.listdir(UPLOAD_FOLDER):
            path = os.path.join(UPLOAD_FOLDER, f)
            try:
                if os.stat(path).st_mtime < now - cutoff:
                    if os.path.isfile(path):
                        os.remove(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                    count += 1
            except FileNotFoundError:
                pass 
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
    try:
        with open(library_path, 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save library: {e}")

def detect_language(text_segments):
    """
    Heuristic language detection based on keyword frequency.
    Returns: 'fr' or 'en'
    """
    if not text_segments: return 'fr'
    
    # Join first ~2000 chars to analyze
    sample_text = " ".join(text_segments)[:2000].lower()
    
    fr_signals = ["expérience", "formation", "compétences", "langues", "résumé", "janvier", "février", "août", "juillet", "décembre", "mars", "avril", "mai", "juin", "septembre", "octobre", "novembre", "actuel", "aujourd'hui"]
    en_signals = ["experience", "education", "skills", "languages", "summary", "january", "february", "august", "july", "december", "march", "april", "may", "june", "september", "october", "november", "current", "present"]
    
    fr_score = sum(sample_text.count(s) for s in fr_signals)
    en_score = sum(sample_text.count(s) for s in en_signals)
    
    # Check simple words if scores are tied or zero
    if fr_score == 0 and en_score == 0:
        if " et " in sample_text or " le " in sample_text or " la " in sample_text:
            return 'fr'
        if " and " in sample_text or " the " in sample_text:
            return 'en'
            
    if en_score > fr_score:
        return 'en'
    return 'fr'

def is_safe_to_save(text):
    """
    Sanitization filter: Returns True if the text is generic enough to be saved in the library.
    Returns False for PII, specific dates, or long sentences.
    """
    text = text.strip()
    if not text: return False
    
    # 1. Exclude too long strings (Sentences)
    if len(text.split()) > 5:
        return False
        
    # 2. Exclude PII patterns
    # Email
    if re.search(r'\S+@\S+', text): return False
    # URL
    if re.search(r'http[s]?://', text) or re.search(r'www\.', text): return False
    # Phone numbers (loose check for digits)
    if sum(c.isdigit() for c in text) > 3: return False
    
    # 3. Exclude Specific Entities usually containing many numbers
    # Dates often contain digits (2024, 12/02), Addresses (123 St)
    if any(char.isdigit() for char in text):
        return False
        
    return True

def translate_docx(source_docx, translation_map_path, output_docx):
    """Translate DOCX file using the translation map"""
    try:
        with open(translation_map_path, 'r', encoding='utf-8') as f:
            translation_map = json.load(f)
    except Exception as e:
        raise Exception(f"Error loading translation map: {e}")

    # No library update here anymore, it's done during extraction/translation phase
    
    # Translate DOCX
    def sub_xml(content, trans_map):
        xml_str = content.decode('utf-8')
        def replace_para(match):
            para_xml = match.group(0)
            t_contents = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', para_xml)
            para_text = "".join(t_contents)
            
            # Lookup with strip
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

def process_file_logic(source_docx, output_json):
    """
    Main logic for Web App:
    1. Extract
    2. Detect Lang
    3. Translate (Bidirectional)
    4. Save Map
    """
    target_pattern = re.compile(r'word/(document|header|footer)\d*\.xml')
    unique_strings = []
    
    # 1. Extract
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

    # 2. Detect Language
    detected_lang = detect_language(unique_strings)
    if detected_lang == 'fr':
        target_lang = 'en'
        logger.info("🇫🇷 Detected language: French -> Target: English")
    else:
        target_lang = 'fr'
        logger.info("🇬🇧 Detected language: English -> Target: French")

    # 3. Load Library & Prepare Reverse Lookup if needed
    master_lib = load_master_library(MASTER_LIBRARY)
    current_library = {} 
    
    if detected_lang == 'fr':
        current_library = master_lib
    else:
        # Reverse Library for EN -> FR
        current_library = {v: k for k, v in master_lib.items() if v and isinstance(v, str)}

    # 4. Map existing translations
    mapping = {}
    missing_strings = []
    
    for s in unique_strings:
        clean_s = s.strip()
        if not clean_s: continue
        
        trans = current_library.get(s) or current_library.get(clean_s)
        if trans:
            mapping[s] = trans
        else:
            if clean_s.replace('.', '').replace(',', '').isdigit() or len(clean_s) < 2:
                mapping[s] = s
            else:
                missing_strings.append(s)

    # 5. Translate missing strings
    if missing_strings:
        logger.info(f"Translating {len(missing_strings)} new strings...")
        try:
            translator = GoogleTranslator(source=detected_lang, target=target_lang)
            batch_size = 10
            new_knowledge = {}

            for i in range(0, len(missing_strings), batch_size):
                batch = missing_strings[i:i + batch_size]
                try:
                    logger.info(f"Translating batch {i//batch_size + 1}")
                    translations = translator.translate_batch(batch)
                    
                    for original, translated in zip(batch, translations):
                        if translated:
                            mapping[original] = translated
                            
                            # SAFETY CHECK BEFORE SAVING
                            if is_safe_to_save(original):
                                if detected_lang == 'fr':
                                    master_lib[original] = translated
                                    new_knowledge[original] = translated
                                else:
                                    # Store as {FR: EN}
                                    master_lib[translated] = original
                                    new_knowledge[translated] = original
                        else:
                            mapping[original] = original
                            
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Batch translation failed: {e}")
                    for s in batch:
                        mapping[s] = s
            
            if new_knowledge:
                save_master_library(MASTER_LIBRARY, master_lib)
                logger.info("Master library updated.")
            
        except Exception as e:
            logger.error(f"Translation setup failed: {e}")
            for s in missing_strings:
                mapping[s] = s

    # Save translation map
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
        filename = secure_filename(file.filename)
        log_upload(filename)
        cleanup_old_files()
        
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)
        logger.info(f"File saved: {upload_path}")
        
        # Determine unique base name
        base_name = os.path.splitext(filename)[0]
        map_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_name}.json")
        
        # --- NEW LOGIC CALL ---
        translation_map = process_file_logic(upload_path, map_path)
        
        # Decide output filename based on detection logic (heuristic check)
        # We can re-check detection or pass it out from logic.
        # For simplicity, let's peek at the file again or assume from filename.
        # But `process_file_logic` knows best. 
        # Refactoring to detect lang inside logic is cleaner, but let's assume FR->EN unless detected otherwise.
        
        # To get the real detected lang, we could re-run detect on keys, but `process_file_logic` already did the heavy lifting.
        # Let's inspect the map. If keys are French indicators, it was FR->EN.
        
        # Quick check:
        sample_keys = list(translation_map.keys())[:50]
        detected_lang = detect_language(sample_keys)
        
        if detected_lang == 'fr':
            # FR -> EN
            if re.search(r'[_.-]FR$', base_name, re.I):
                output_base = re.sub(r'([_.-])FR$', r'\1EN', base_name, flags=re.I)
            else:
                output_base = f"{base_name}_EN"
        else:
             # EN -> FR
            if re.search(r'[_.-]EN$', base_name, re.I):
                output_base = re.sub(r'([_.-])EN$', r'\1FR', base_name, flags=re.I)
            else:
                output_base = f"{base_name}_FR"
        
        output_docx = os.path.join(app.config['UPLOAD_FOLDER'], f"{output_base}.docx")
        
        translate_docx(upload_path, map_path, output_docx)
        
        return jsonify({
            'success': True,
            'download_url': f'/download/{os.path.basename(output_docx)}',
            'filename': os.path.basename(output_docx)
        })
    
    except Exception as e:
        logger.error(f"Processing error: {e}")
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
    app.run(debug=False, host='0.0.0.0', port=5000)
