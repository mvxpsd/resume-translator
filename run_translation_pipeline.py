#!/usr/bin/env python3
import zipfile
import json
import re
import os
import sys
import argparse
import time
import logging
from deep_translator import GoogleTranslator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MASTER_LIBRARY = 'master_library.json'

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

def translate_docx(source_docx, translation_map, output_docx):
    """Translate DOCX file using the translation map"""
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
                        # Basic XML escaping
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

def process_translation(source_docx):
    """Main process: Extract -> AI Translate -> Generate DOCX"""
    if not os.path.exists(source_docx):
        print(f"Error: File not found: {source_docx}")
        return

    # 1. Extract strings
    target_pattern = re.compile(r'word/(document|header|footer)\d*\.xml')
    unique_strings = []
    master_lib = load_master_library(MASTER_LIBRARY)

    print(f"Reading {source_docx}...")
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
    
    # 2. Map existing and find missing
    mapping = {}
    missing_strings = []
    for s in unique_strings:
        clean_s = s.strip()
        if not clean_s: continue
        trans = master_lib.get(s) or master_lib.get(clean_s)
        if trans:
            mapping[s] = trans
        else:
            if clean_s.replace('.', '').replace(',', '').isdigit() or len(clean_s) < 2:
                mapping[s] = s
            else:
                missing_strings.append(s)

    # 3. AI Translation for missing
    if missing_strings:
        print(f"Translating {len(missing_strings)} new strings via AI...")
        try:
            translator = GoogleTranslator(source='fr', target='en')
            batch_size = 10
            for i in range(0, len(missing_strings), batch_size):
                batch = missing_strings[i:i + batch_size]
                print(f"  Processing batch {i//batch_size + 1}/{(len(missing_strings)-1)//batch_size + 1}")
                try:
                    translations = translator.translate_batch(batch)
                    for original, translated in zip(batch, translations):
                        if translated:
                            mapping[original] = translated
                            master_lib[original] = translated
                        else:
                            mapping[original] = original
                    time.sleep(2) # Delay to avoid rate limits
                except Exception as e:
                    print(f"  Batch failed: {e}")
                    for s in batch: mapping[s] = s
            
            save_master_library(MASTER_LIBRARY, master_lib)
            print("Master library updated.")
        except Exception as e:
            print(f"Translation error: {e}")
            for s in missing_strings: mapping[s] = s

    # 4. Generate Output DOCX
    base_name = os.path.splitext(source_docx)[0]
    output_docx = f"{base_name}_EN.docx"
    print(f"Generating translated document: {output_docx}...")
    translate_docx(source_docx, mapping, output_docx)
    print("Success! Translation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Professional Resume Translator CLI")
    parser.add_argument("source", help="Path to French DOCX file")
    args = parser.parse_args()
    
    # Ensure we are in the directory of the script to find master_library.json
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    process_translation(args.source)
