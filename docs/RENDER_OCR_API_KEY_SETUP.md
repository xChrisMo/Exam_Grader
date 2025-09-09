# Render.com OCR API Key Setup Guide

## 🚨 **Issue: Placeholder OCR API Key Detected**

If you're seeing this error on Render.com:
```
ERROR - ❌ PLACEHOLDER OCR API KEY DETECTED: your_handwriting_ocr_api_key_here
ERROR - ❌ This means the HANDWRITING_OCR_API_KEY environment variable is not set correctly on Render.com!
```

## 🔧 **Solution: Set the Environment Variable**

### **Step 1: Get Your HandwritingOCR API Key**
1. Go to [HandwritingOCR.com](https://www.handwritingocr.com)
2. Sign up for an account
3. Get your API key from the dashboard

### **Step 2: Set Environment Variable on Render.com**
1. Go to your Render.com dashboard
2. Navigate to your service
3. Go to **Environment** tab
4. Add/update the environment variable:
   ```
   HANDWRITING_OCR_API_KEY=your_actual_api_key_here
   ```
   Replace `your_actual_api_key_here` with your real API key

### **Step 3: Verify the Setup**
The API key should:
- ✅ NOT contain "your_" or "here" in it
- ✅ Be a real API key from HandwritingOCR.com
- ✅ Start with something like `1072|` or similar

### **Step 4: Redeploy**
1. Save the environment variable
2. Trigger a new deployment
3. Check the logs to ensure the error is gone

## 🔍 **Debugging**

If you're still having issues, check the deployment logs for:
```
🔍 OCR API Key Loading Debug:
   HANDWRITING_OCR_API_KEY env: [your_key_here]
   Final OCR API key: [your_key_here]
```

If you see placeholder values, the environment variable is not set correctly.

## 🆘 **Fallback Options**

If you don't have a HandwritingOCR API key, the application will automatically use fallback OCR methods:
1. **Tesseract OCR** (installed automatically)
2. **EasyOCR** (Python library)
3. **Basic image processing**

The application will still work, but with reduced OCR accuracy.

## 📞 **Support**

If you continue to have issues:
1. Check the deployment logs
2. Verify the environment variable is set correctly
3. Ensure the API key is valid and active
