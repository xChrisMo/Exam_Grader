#!/bin/bash
# Install Tesseract OCR on Render.com

echo "🔧 Installing Tesseract OCR..."

# Update package list
apt-get update

# Install Tesseract OCR
apt-get install -y tesseract-ocr

# Install additional language packs (optional)
apt-get install -y tesseract-ocr-eng

# Verify installation
echo "✅ Tesseract installation complete"
tesseract --version

echo "🎉 Tesseract OCR is ready!"
