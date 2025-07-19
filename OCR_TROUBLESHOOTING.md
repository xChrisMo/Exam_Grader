# OCR Troubleshooting Guide

## Current Issue
The OCR service is configured but not reachable, causing PDF processing failures.

## Quick Fixes

### 1. Check OCR Service Status
Run the diagnostic script:
```bash
python test_ocr_config.py
```

### 2. Verify API Configuration
Check these environment variables:
- `HANDWRITING_OCR_API_KEY`: Your OCR API key
- `HANDWRITING_OCR_API_URL`: API endpoint (default: https://www.handwritingocr.com/api/v3)

### 3. Test Network Connectivity
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" https://www.handwritingocr.com/api/v3/documents
```

### 4. Common Solutions

#### API Key Issues
- Verify your API key is valid and active
- Check if you have sufficient API credits
- Ensure the key has proper permissions

#### Network Issues
- Check firewall settings
- Verify internet connectivity
- Try accessing the API from a different network

#### Service Unavailability
- The OCR service may be temporarily down
- Check the service status page
- Try again later

### 5. Temporary Workarounds

#### For Text-Based PDFs
- Ensure PDFs contain selectable text (not scanned images)
- Try converting scanned PDFs to text-based PDFs using other tools

#### For Image-Based Documents
- Convert images to text using local OCR tools
- Use online OCR services as a temporary solution
- Process documents in smaller batches

### 6. Alternative OCR Services
If the current service remains unavailable, consider:
- Google Cloud Vision API
- AWS Textract
- Azure Computer Vision
- Local OCR solutions (Tesseract)

## Error Messages and Solutions

### "OCR service not available"
- Check API key configuration
- Verify network connectivity
- Test API endpoint accessibility

### "No text content could be extracted"
- Document may be image-based and require OCR
- Try with a text-based PDF first
- Check document quality and format

### "Network error during OCR processing"
- Check internet connection
- Verify firewall settings
- Try again after a few minutes

## Getting Help
1. Run the diagnostic script: `python test_ocr_config.py`
2. Check the application logs in `logs/app.log`
3. Test with a simple text-based PDF first
4. Contact support with diagnostic results
