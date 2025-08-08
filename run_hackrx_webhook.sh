#!/bin/bash

# HackRX Insurance AI Webhook Setup and Run Script

echo "=================================="
echo "HackRX Insurance AI Webhook Setup"
echo "=================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✅ Python3 found: $(python3 --version)"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Please install pip"
    exit 1
fi

echo "✅ pip3 found"

# Install requirements
echo ""
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install requirements"
    exit 1
fi

echo "✅ Dependencies installed successfully"

# Check environment variables
echo ""
echo "🔧 Checking environment variables..."

if [ -f ".env" ]; then
    echo "✅ .env file found"
    source .env
else
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << EOF
# OpenAI API Key (required for embeddings)
OPENAI_API_KEY=your_openai_api_key_here

# Google API Key (required for Gemini model)
GOOGLE_API_KEY=your_google_api_key_here

# Optional: Set custom ports
WEBHOOK_PORT=8000
EOF
    echo "📝 Created .env template. Please fill in your API keys!"
    echo "You need:"
    echo "  - OPENAI_API_KEY: For text embeddings"
    echo "  - GOOGLE_API_KEY: For Gemini language model"
    exit 1
fi

# Check if API keys are set
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    echo "❌ OPENAI_API_KEY not set in .env file"
    exit 1
fi

if [ -z "$GOOGLE_API_KEY" ] || [ "$GOOGLE_API_KEY" = "your_google_api_key_here" ]; then
    echo "❌ GOOGLE_API_KEY not set in .env file"
    exit 1
fi

echo "✅ Environment variables configured"

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p database_files
mkdir -p temp_knowledge
echo "✅ Directories created"

# Start the webhook server
echo ""
echo "🚀 Starting HackRX Insurance AI Webhook..."
echo "Server will be available at: http://localhost:8000"
echo "Authentication: Bearer b37bee837667836f35b77319b6c7b1f712a2955869766b98de9400065a1c2c7f"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 hackrx_webhook.py
