#!/bin/bash
# Install Tesseract OCR on Render.com

echo "🔧 Installing Tesseract OCR..."

# Check if we're on Render.com
if [ -n "$RENDER" ]; then
    echo "✅ Running on Render.com - installing Tesseract..."
    
    # Update package list
    apt-get update -y
    
    # Install Tesseract OCR
    apt-get install -y tesseract-ocr
    
    # Install English language pack
    apt-get install -y tesseract-ocr-eng
    
    # Verify installation
    echo "✅ Tesseract installation complete"
    tesseract --version
    
    echo "🎉 Tesseract OCR is ready on Render.com!"
else
    echo "ℹ️  Not on Render.com - Tesseract installation skipped"
    echo "ℹ️  Please install Tesseract manually on your system"
fi
