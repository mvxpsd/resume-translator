import zipfile
import json
import re
import os
import subprocess
import sys
import argparse

def get_win_path(unix_path):
    """Converts a WSL path like /mnt/d/file.txt to a Windows path D:\\file.txt"""
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
        except: return {}
    return {}

def save_master_library(library_path, data):
    # Only keep non-empty strings
    clean_data = {k: v for k, v in data.items() if isinstance(v, str) and v.strip() != ""}
    with open(library_path, 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, indent=4, ensure_ascii=False)

def extract_strings(source_docx, output_json, library_path):
    """Extracts unique text segments and pre-fills from the Master Library."""
    print(f"Extracting strings from {os.path.basename(source_docx)}...")
    target_pattern = re.compile(r'word/(document|header|footer)\d*\.xml')
    unique_strings = []
    
    master_lib = load_master_library(library_path)

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
        
        # Build map: Use Master Lib if available, else empty
        mapping = {}
        found_count = 0
        for s in unique_strings:
            trans = master_lib.get(s) or master_lib.get(s.strip())
            if trans:
                mapping[s] = trans
                found_count += 1
            else:
                mapping[s] = ""
        
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=4, ensure_ascii=False)
        print(f"Extraction complete. {len(unique_strings)} strings saved to {output_json}")
        print(f"Pre-filled {found_count} strings from Master Library.")
    except Exception as e:
        print(f"Extraction Error: {e}")

def translate_resume(source_docx, translation_map_path, library_path):
    """Applies translation map to the DOCX and UPDATES the Master Library."""
    base_name, _ = os.path.splitext(source_docx)
    if re.search(r'[_.-]FR$', base_name, re.I):
        output_base = re.sub(r'([_.-])FR$', r'\1EN', base_name, flags=re.I)
    else:
        output_base = f"{base_name}_EN"
        
    output_docx = f"{output_base}.docx"
    output_pdf = f"{output_base}.pdf"

    try:
        with open(translation_map_path, 'r', encoding='utf-8') as f:
            translation_map = json.load(f)
    except Exception as e:
        print(f"Error loading map: {e}")
        return

    # UPDATING MASTER LIBRARY
    master_lib = load_master_library(library_path)
    new_knowledge = 0
    for k, v in translation_map.items():
        if v and v.strip() != "":
            if k not in master_lib:
                master_lib[k] = v
                new_knowledge += 1
    if new_knowledge > 0:
        save_master_library(library_path, master_lib)
        print(f"Master Library updated with {new_knowledge} new translations.")

    # 1. Translate DOCX
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
                        safe = translation.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\"', '&quot;').replace('\'', '&apos;')
                        return f'<w:t{tag_start}>{safe}</w:t>'
                    return f'<w:t{tag_start}></w:t>'
                return re.sub(r'<w:t([^>]*)>([^<]*)</w:t>', sub_t, para_xml)
            return para_xml
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
        print(f"Translated Word doc created: {os.path.basename(output_docx)}")
    except Exception as e:
        print(f"DOCX Error: {e}"); return

    # 2. PDF Conversion
    print("Converting to PDF (PowerShell Native)...")
    temp_docx = os.path.join(os.path.dirname(output_docx), "temp_job.docx")
    temp_pdf = os.path.join(os.path.dirname(output_docx), "temp_job.pdf")
    import shutil
    shutil.copy2(output_docx, temp_docx)
    
    ps_script = f"""
$word = New-Object -ComObject Word.Application
try {{
    $doc = $word.Documents.Open('{get_win_path(temp_docx)}')
    $doc.SaveAs([ref]'{get_win_path(temp_pdf)}', [ref]17)
    $doc.Close()
    Write-Host "SUCCESS"
}} catch {{ Write-Host "ERROR: $($_.Exception.Message)" }}
finally {{ $word.Quit() }}
"""
    ps_file = os.path.join(os.path.dirname(output_docx), "convert.ps1")
    with open(ps_file, "w", encoding='utf-8') as f: f.write(ps_script)

    try:
        res = subprocess.run(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", get_win_path(ps_file)], capture_output=True, text=True)
        if "SUCCESS" in res.stdout:
            if os.path.exists(output_pdf): os.remove(output_pdf)
            os.rename(temp_pdf, output_pdf); print(f"PDF created: {os.path.basename(output_pdf)}")
        else: print(f"PDF Error: {res.stdout.strip()}")
    finally:
        for f in [ps_file, temp_docx, temp_pdf]:
            if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    lib_path = os.path.join(script_dir, "master_library.json")

    parser = argparse.ArgumentParser(description="Professional Resume Translator")
    parser.add_argument("source", help="Path to French DOCX")
    parser.add_argument("--extract", action="store_true", help="Extract strings to JSON (auto-prefills from Library)")
    parser.add_argument("--map", help="Path to translation JSON (defaults to [filename].json)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.source):
        print(f"Error: Source document not found: {args.source}")
        sys.exit(1)

    # 1. Resolve Map Path
    map_path = args.map if args.map else os.path.splitext(args.source)[0] + ".json"

    # 2. Extraction Mode
    if args.extract:
        extract_strings(args.source, map_path, lib_path)
        sys.exit(0)

    # 3. Translation Mode
    if not os.path.exists(map_path):
        print(f"\n--- NEW RESUME DETECTED ---")
        print(f"No specific translation map found: {map_path}")
        print(f"Run this command first to extract strings (will auto-fill known translations):")
        print(f"python3 run_translation_pipeline.py \"{args.source}\" --extract")
        sys.exit(1)

    translate_resume(args.source, map_path, lib_path)
