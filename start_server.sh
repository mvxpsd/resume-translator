#!/bin/bash

# Resume Translation Web App - Quick Start Script

echo "🚀 Starting Resume Translation Web App..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    
    # Check if pip is installed in venv
    if [ ! -f "venv/bin/pip" ]; then
        echo "🔧 Installing pip..."
        curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        venv/bin/python3 get-pip.py
        rm get-pip.py
    fi
fi

# Install dependencies
echo "⬇️  Installing/Updating dependencies..."
if [ -f "requirements.txt" ]; then
    venv/bin/pip install -r requirements.txt
else
    venv/bin/pip install flask deep-translator werkzeug
fi

# Start the server
echo ""
echo "✅ Starting Flask server..."
# Start the server (Production Mode)
echo ""
echo "✅ Starting Gunicorn server..."
echo "📍 Web app will be available at: http://localhost:5000"
echo "   - 2 concurrent workers"
echo "   - 300s timeout"
echo "Press CTRL+C to stop the server"
echo ""

# Use exec to replace the shell process
exec venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 --timeout 300 --access-logfile - --error-logfile - app:app
