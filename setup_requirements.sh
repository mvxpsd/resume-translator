#!/bin/bash

# Setup requirements for Resume Translation Pipeline

echo "Checking system requirements..."

# 1. Check Python 3
if command -v python3 &>/dev/null; then
    echo "[OK] Python 3 is installed."
else
    echo "[ERROR] Python 3 is not found. Please install it using: sudo apt update && sudo apt install python3"
    exit 1
fi

# 2. Check PowerShell (needed for Word-to-PDF conversion on Windows/WSL)
if command -v powershell.exe &>/dev/null; then
    echo "[OK] PowerShell (Windows) is available via WSL."
else
    echo "[WARNING] powershell.exe not found. PDF conversion will not work, though DOCX translation will still function."
fi

# 3. Handle Python Pip (not strictly needed for my custom script, but good to have)
if command -v pip3 &>/dev/null; then
    echo "[OK] Pip is installed."
else
    echo "Pip is missing. Attempting to install pip..."
    sudo apt update && sudo apt install -y python3-pip
fi

# 4. Final verification of the translation script dependencies
# Note: The current pipeline script uses ONLY built-in Python libraries 
# (zipfile, json, re, os, subprocess, xml.etree.ElementTree)
echo ""
echo "Setup complete! No external Python libraries are required."
echo "You can run the translator using:"
echo "  python3 /mnt/d/run_translation_pipeline.py"
echo ""
echo "Or specify a different file:"
echo "  python3 /mnt/d/run_translation_pipeline.py /path/to/resume_FR.docx"

