# Resume Translation Web App - Walkthrough 🚀

## Overview

I have created a production-ready ecosystem for translating French resumes to English. This system perfectly preserves all formatting (tables, fonts, layouts) and is available as a **Web App**, a **Linux CLI**, and a **Windows Native tool**.

---

## 🏗️ What Was Built

### 1. The Core Engine (`app.py` & `run_translation_pipeline.py`)
Both systems share the same industrial-grade translation logic:
- **Batch Processing**: Translates 10 lines at a time via AI to prevent timeouts and IP bans.
- **Master Library**: A knowledge base of 500+ professional terms that speeds up translation and ensures accuracy for technical job titles.
- **XML Injection**: Modifies the internal structure of DOCX files to replace text while keeping styles intact.

### 2. The Web Interface (`static/index.html` & `style.css`)
A "Next-Gen" UI featuring:
- **Glassmorphism Design**: Frosted glass effects and smooth gradients.
- **Drag & Drop**: Modern file handling.
- **Progress Tracking**: Real-time feedback during translation.
- **Production Server**: Uses **Gunicorn** for high concurrency (4 workers) and stability.

---

## 🚀 How to Use

### A. Web App (Linux/WSL)
1.  **Setup**: `./setup_requirements.sh`
2.  **Start**: `./start_server.sh`
3.  **Access**: `http://localhost:5000`

### B. CLI Tool (Linux/WSL)
Translate files directly from your terminal:
```bash
./venv/bin/python3 run_translation_pipeline.py "/path/to/resume.docx"
```

### C. Windows Integration (Native)
No terminal or WSL needed!
1.  **Setup**: Double-click `setup_windows.bat` (first time only).
2.  **Translate**: Drag your French DOCX file and drop it onto `run_cli_windows.bat`.

---

## 🛡️ Production & Performance

- **Timeout Management**: Configured for 300s (5 minutes) to handle massive CVs.
- **Auto-Cleanup**: All uploaded and processed files are deleted within 60 seconds to ensure privacy and disk space.
- **Secure Handling**: No debug mode; safe file paths used throughout.
- **Logging**: All activity is tracked in `uploads.log`.

---

## 📚 The Master Library
The file `master_library.json` has been pre-populated with **500+ professional mappings**:
- **Job Titles**: "Chef de projet" -> "Project Manager", "Ingénieur de données" -> "Data Engineer".
- **Skills**: "Capacité d'adaptation" -> "Adaptability", "Esprit d'équipe" -> "Teamwork".
- **Cleaned version**: All personal names and company-specific data have been removed to make it a generic template.

---

## 🌍 External Access
If you want to access your local server from the internet (e.g., from your phone):
1.  Install **ngrok**.
2.  Run: `ngrok http 5000`.

---
*Developed for a professional, high-performance experience.*
