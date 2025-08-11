# WeasyPrint Windows Setup Guide

## Problem
WeasyPrint requires GTK libraries on Windows, which causes the error:
```
cannot load library 'libgobject-2.0-0': error 0x7e
```

## Solution Options

### Option 1: Install GTK via MSYS2 (Recommended)

1. **Install MSYS2**
   - Download from: https://www.msys2.org/
   - Run the installer and follow the setup instructions

2. **Install GTK libraries**
   ```bash
   # Open MSYS2 terminal and run:
   pacman -S mingw-w64-x86_64-gtk3 mingw-w64-x86_64-cairo mingw-w64-x86_64-pango
   ```

3. **Add MSYS2 to PATH**
   - Add `C:\msys64\mingw64\bin` to your system PATH
   - Restart your command prompt/IDE

4. **Test WeasyPrint**
   ```python
   python -c "import weasyprint; print('WeasyPrint working!')"
   ```

### Option 2: Use GTK Windows Runtime

1. **Download GTK Windows Runtime**
   - Download from: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
   - Install the runtime

2. **Add to PATH**
   - Add GTK installation directory to PATH
   - Usually: `C:\Program Files\GTK3-Runtime Win64\bin`

### Option 3: Use Conda (Alternative)

```bash
# If using conda
conda install -c conda-forge weasyprint
```

### Option 4: Docker Solution

```dockerfile
# Use in Docker for consistent environment
FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info

RUN pip install weasyprint
```

## Current Fallback Behavior

The system automatically falls back to ReportLab when WeasyPrint fails, so PDF generation continues to work. However, WeasyPrint provides:

- Better HTML/CSS support
- More accurate rendering
- Better typography
- Support for complex layouts

## Testing

After installation, test with:

```python
from weasyprint import HTML, CSS

html_content = "<html><body><h1>Test</h1></body></html>"
HTML(string=html_content).write_pdf("test.pdf")
print("WeasyPrint working correctly!")
```

## Troubleshooting

1. **DLL Load Failed**: Ensure GTK bin directory is in PATH
2. **Import Error**: Reinstall weasyprint after GTK installation
3. **Font Issues**: Install additional fonts if needed
4. **Permission Issues**: Run as administrator if needed

## Production Deployment

For production on Windows servers:
1. Use Docker with Linux base image (recommended)
2. Install GTK runtime on Windows server
3. Use ReportLab-only mode by modifying the fallback logic