# Resume Translator Web App

A web application that translates French resumes to English while preserving all formatting, fonts, and styles.

## Features

- 📁 **Drag & Drop Upload** - Easy file upload interface
- 🎨 **Format Preservation** - Maintains all fonts, tables, and layouts
- 📄 **Word Output** - Get professionally formatted DOCX
- 🚀 **Fast Translation** - Uses AI-powered incremental learning
- 🔒 **Secure** - All processing happens locally

## Setup

### Prerequisites

- Python 3.x

### Installation

**Option 1: System Package (Recommended for Ubuntu 24.04)**
```bash
sudo apt update
sudo apt install python3-flask
```

**Option 2: Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate
pip install flask
```

**Verify the master library exists**:
```bash
ls /mnt/d/master_library.json
```
If it doesn't exist, the app will create it automatically.

## Running the Application

1. **Start the Flask server**:
   ```bash
   cd /mnt/d
   python3 app.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

3. **Upload your French resume** (DOCX format)

4. **Download** your translated file (automatically downloads as DOCX)

## File Structure

```
/mnt/d/
├── app.py                      # Flask backend
├── static/
│   ├── index.html             # Frontend UI
│   └── style.css              # Styling
├── master_library.json        # Translation knowledge base
├── run_translation_pipeline.py # CLI translation tool
└── requirements.txt           # Python dependencies
```

## How It Works

1. **Upload**: User uploads a French DOCX resume
2. **Extract**: System extracts all text from the document
3. **Translate**: Applies translations from the master library
4. **Generate**: Creates English DOCX
5. **Download**: Returns translated file

## Troubleshooting

### Flask not installed
```bash
sudo apt install python3-pip
pip3 install flask
```



### Port 5000 already in use
Change the port in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=8080)
```

## CLI Alternative

You can also use the command-line tool:
```bash
python3 run_translation_pipeline.py your_resume_FR.docx
```

## Notes

- Maximum file size: 16MB
- Supported format: DOCX only
- The master library grows with each translation
- Temporary files are automatically cleaned up
