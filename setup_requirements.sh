#!/bin/bash

# Setup requirements for Resume Translation Web App
echo "🚀 Setting up environment for Resume Translator..."

# 1. Check Python 3
if command -v python3 &>/dev/null; then
    echo "[OK] Python 3 is installed."
else
    echo "[ERROR] Python 3 is not found. Please install it: sudo apt update && sudo apt install python3"
    exit 1
fi

# 2. Check Pip
if ! command -v pip3 &>/dev/null; then
    echo "Pip is missing. Installing pip..."
    sudo apt update && sudo apt install -y python3-pip
fi

# 3. Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# 4. Install Dependencies
echo "⬇️ Installing dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    ./venv/bin/pip install -r requirements.txt
    echo "[OK] Dependencies installed successfully."
else
    echo "[ERROR] requirements.txt not found!"
    echo "Creating a default requirements.txt..."
    cat > requirements.txt << EOF
flask
werkzeug
deep-translator
gunicorn
EOF
    ./venv/bin/pip install -r requirements.txt
fi

echo ""
echo "✅ Setup complete!"
echo "You can now start the server with: ./start_server.sh"
