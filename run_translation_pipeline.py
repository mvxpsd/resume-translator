#!/usr/bin/env python3
import zipfile
import json
import re
import os
import sys
import argparse
import time
import logging

# Check for dependencies and provide friendly error
try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("❌ Error: 'deep-translator' library not found.")
    print("Please run 'setup_requirements.sh' (Linux) or 'setup_windows.bat' (Windows) first.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MASTER_LIBRARY = 'master_library.json'

def load_master_library(library_path):
    if os.path.exists(library_path):
        try:
            with open(library_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load library: {e}")
            return {}
    return {}

def save_master_library(library_path, data):
    """Saves non-empty translations back to the master library"""
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
    # Join first ~1000 chars to analyze
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

def translate_docx(source_docx, translation_map, output_docx):
    """Translate DOCX file using the translation map while preserving XML structure"""
    def sub_xml(content, trans_map):
        xml_str = content.decode('utf-8')
        def replace_para(match):
            para_xml = match.group(0)
            # Find all text content within the paragraph
            t_contents = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', para_xml)
            para_text = "".join(t_contents)
            
            # Look for translation (exact match or stripped)
            translation = trans_map.get(para_text) or trans_map.get(para_text.strip())
            
            if translation and isinstance(translation, str) and translation.strip() != "":
                state = {'first': True}
                def sub_t(t_match):
                    tag_start = t_match.group(1)
                    if state['first']:
                        state['first'] = False
                        # Basic XML escaping for special characters
                        safe = translation.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')
                        return f'<w:t{tag_start}>{safe}</w:t>'
                    # Clear subsequent text tags in the same paragraph to avoid duplicates
                    return f'<w:t{tag_start}></w:t>'
                return re.sub(r'<w:t([^>]*)>([^<]*)</w:t>', sub_t, para_xml)
            return para_xml
        
        # Process each paragraph
        return re.sub(r'<w:p\b[^>]*>.*?</w:p>', replace_para, xml_str, flags=re.DOTALL).encode('utf-8')

    target_pattern = re.compile(r'word/(document|header|footer)\d*\.xml')
    try:
        with zipfile.ZipFile(source_docx, 'r') as zin, zipfile.ZipFile(output_docx, 'w', zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                content = zin.read(info.filename)
                if target_pattern.match(info.filename):
                    zout.writestr(info.filename, sub_xml(content, translation_map))
                else:
                    zout.writestr(info, content)
    except Exception as e:
        logger.error(f"DOCX translation failed: {e}")

def process_translation(source_docx):
    """Main process: Extract -> Detect Lang -> Translate (Bidirectional) -> Generate DOCX"""
    # Ensure absolute path for source because we might change CWD
    source_docx = os.path.abspath(source_docx)
    
    if not os.path.exists(source_docx):
        print(f"❌ Error: File not found: {source_docx}")
        return

    # Set working directory to script location to find master_library.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 1. Extract strings from DOCX
    target_pattern = re.compile(r'word/(document|header|footer)\d*\.xml')
    unique_strings = []
    
    print(f"📖 Reading {os.path.basename(source_docx)}...")
    try:
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
    except Exception as e:
        print(f"❌ Error reading DOCX: {e}")
        return
    
    # 2. Detect Language
    detected_lang = detect_language(unique_strings)
    if detected_lang == 'fr':
        target_lang = 'en'
        print("🇫🇷 Detected language: French -> Target: English")
    else:
        target_lang = 'fr'
        print("🇬🇧 Detected language: English -> Target: French")

    # 3. Load Library & Prepare Reverse Lookup if needed
    master_lib = load_master_library(MASTER_LIBRARY)
    
    # If translating EN -> FR, we need to reverse the library (Value matches Key)
    # Master Lib Structure: { "French": "English" }
    current_library = {} 
    
    if detected_lang == 'fr':
        # FR -> EN: Use library as is
        current_library = master_lib
    else:
        # EN -> FR: Create reverse map { "English": "French" }
        current_library = {v: k for k, v in master_lib.items() if v and isinstance(v, str)}

    # Build normalized lookup for fuzzy matching (ignore trailing :;. and spaces)
    norm_lookup = {}
    for k, v in current_library.items():
        nk = k.strip().rstrip(':;\u00a0. ').replace('\u00a0', ' ').strip()
        if nk and nk not in norm_lookup:
            norm_lookup[nk] = v

    def fuzzy_lookup(text):
        """Try exact match first, then normalized (strip trailing :;. and spaces)"""
        result = current_library.get(text) or current_library.get(text.strip())
        if result:
            return result
        norm = text.strip().rstrip(':;\u00a0. ').replace('\u00a0', ' ').strip()
        return norm_lookup.get(norm)

    # 4. Map existing translations and identify missing ones
    mapping = {}
    missing_strings = []
    found_in_lib = 0
    
    for s in unique_strings:
        clean_s = s.strip()
        if not clean_s: continue
        
        # Check library (exact then fuzzy)
        trans = fuzzy_lookup(s)
        
        if trans:
            mapping[s] = trans
            found_in_lib += 1
        else:
            # Skip numbers/symbols from translation
            if clean_s.replace('.', '').replace(',', '').isdigit() or len(clean_s) < 2:
                mapping[s] = s
            else:
                missing_strings.append(s)

    print(f"📚 Found {found_in_lib} terms in Master Library.")

    # 5. AI Translation for missing strings
    if missing_strings:
        print(f"🤖 Translating {len(missing_strings)} new strings via AI...")
        try:
            translator = GoogleTranslator(source=detected_lang, target=target_lang)
            batch_size = 30
            
            # Identify new knowledge to save (only safe terms)
            new_knowledge = {}
            
            for i in range(0, len(missing_strings), batch_size):
                batch = missing_strings[i:i + batch_size]
                print(f"  ⏳ Processing batch {i//batch_size + 1}/{(len(missing_strings)-1)//batch_size + 1}")
                try:
                    translations = translator.translate_batch(batch)
                    for original, translated in zip(batch, translations):
                        if translated:
                            mapping[original] = translated
                            
                            # SAFETY CHECK BEFORE SAVING
                            if is_safe_to_save(original):
                                if detected_lang == 'fr':
                                    # Forward: original=FR, translated=EN
                                    master_lib[original] = translated
                                    new_knowledge[original] = translated
                                else:
                                    # Reverse: original=EN, translated=FR
                                    # Store as {FR: EN} to maintain library consistency
                                    master_lib[translated] = original
                                    new_knowledge[translated] = original
                        else:
                            mapping[original] = original
                    time.sleep(0.5)
                except Exception as e:
                    print(f"  ⚠️ Batch failed: {e}")
                    for s in batch: mapping[s] = s
            
            # Save only if we learned something new and safe
            if new_knowledge:
                save_master_library(MASTER_LIBRARY, master_lib)
                print(f"✨ Master library updated with {len(new_knowledge)} new generic terms.")
            else:
                print("🔒 No new verifiable terms saved to library (Sanitization active).")
                
        except Exception as e:
            print(f"❌ Translation service error: {e}")
            for s in missing_strings: mapping[s] = s

    # 6. Generate Output DOCX
    base_name, _ = os.path.splitext(source_docx)
    
    # Handle suffix swapping
    if detected_lang == 'fr':
        # ..._FR -> ..._EN
        if re.search(r'[_.-]FR$', base_name, re.I):
            output_base = re.sub(r'([_.-])FR$', r'\1EN', base_name, flags=re.I)
        else:
            output_base = f"{base_name}_EN"
    else:
        # ..._EN -> ..._FR
        if re.search(r'[_.-]EN$', base_name, re.I):
            output_base = re.sub(r'([_.-])EN$', r'\1FR', base_name, flags=re.I)
        else:
            output_base = f"{base_name}_FR"
        
    output_docx = f"{output_base}.docx"
    print(f"💾 Generating output: {os.path.basename(output_docx)}...")
    translate_docx(source_docx, mapping, output_docx)
    print("✅ Success! Translation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Professional Resume Translator CLI")
    parser.add_argument("source", help="Path to DOCX file")
    args = parser.parse_args()
    
    process_translation(args.source)
