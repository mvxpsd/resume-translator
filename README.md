# Professional Resume Translator 🚀

A robust, production-ready tool to translate French resumes to English while perfectly preserving formatting, styles, and layouts.

## ✨ Key Features

- 📁 **Seamless DOCX Translation**: Maintains all fonts, tables, and complex layouts.
- ⚡ **AI-Powered Batching**: Efficiently translates large documents using batch processing to avoid API limits.
- 📚 **Smart Library System**: 500+ pre-filled technical terms (Data Engineering, Management, IT) for instant, accurate mapping.
- 🌐 **Web & CLI Interfaces**: Choose between a premium web app or a powerful command-line tool.
- 🪟 **Windows Native Support**: Includes dedicated `.bat` files for easy use on Windows without a terminal.
- 🔒 **Privacy Focused**: Automatic file cleanup and secure processing logic.

---

## 🛠️ Setup & Installation

### For Linux / WSL (Ubuntu)
1. **Prepare the environment**:
   ```bash
   chmod +x setup_requirements.sh
   ./setup_requirements.sh
   ```
2. **Start the server**:
   ```bash
   ./start_server.sh
   ```

### For Windows
1. **Initialize**: Double-click on `setup_windows.bat`.
2. **Translate**: Drag and drop any `.docx` file onto `run_cli_windows.bat`.

---

## 🚀 Usage Guide

### 1. Web Application
- **URL**: [http://localhost:5000](http://localhost:5000)
- Simply drag and drop your French resume.
- The app will automatically handle extraction, batch translation via Google Translate AI, and document generation.
- Click **Download** to get your professionally formatted English CV.

### 2. Command Line (CLI)
For fast, automatic translation from your terminal:
```bash
./venv/bin/python3 run_translation_pipeline.py "path/to/resume.docx"
```

### 3. Windows Native (No terminal)
- Drag your French CV and drop it directly onto the **`run_cli_windows.bat`** file in your explorer.

---

## 📂 Project Structure

- `app.py`: Flask production server with automatic cleanup and logging.
- `master_library.json`: The "brain" of the app containing 500+ professional mappings.
- `run_translation_pipeline.py`: Pure Python engine for CLI translation.
- `start_server.sh`: Production startup script using **Gunicorn** (4 workers, 300s timeout).
- `static/`: Frontend assets (modern UI with glassmorphism).
- `setup_windows.bat` & `run_cli_windows.bat`: Windows integration scripts.

---

## 🛡️ Production Hardening
- **Server**: Uses Gunicorn for concurrency and stability.
- **Timeout**: Increased to 300s to handle massive AI translation tasks.
- **Cleanup**: Uploaded files and maps are automatically deleted after 60 seconds.
- **Audit**: All actions are logged in `uploads.log`.

## 🗺️ Future Roadmap
- [ ] **Local AI Translation**: Move from Google Translate API to offline Hugging Face Transformers.
- [ ] **Multi-language Support**: Add French to German, Spanish, etc.
- [ ] **PDF Direct Extraction**: Improve support for non-selectable PDF layers.

---
*Created by Papa Samba Diop - Optimized for Professional Engineering & Management Resumes.*
