#!/usr/bin/env python3
"""
Test script to verify PyMuPDF installation.
"""

import sys
print(f"Python version: {sys.version}")

try:
    import fitz
    print(f"PyMuPDF imported successfully as fitz")
    print(f"PyMuPDF version: {fitz.version}")
    print("PyMuPDF installation is working correctly!")
except ImportError as e:
    print(f"Error importing PyMuPDF: {e}")
    print("\nTrying to import PyMuPDF directly...")
    try:
        import PyMuPDF
        print(f"PyMuPDF imported successfully")
        print(f"PyMuPDF version: {PyMuPDF.__version__}")
        print("PyMuPDF installation is working correctly, but should be imported as 'fitz'!")
    except ImportError as e2:
        print(f"Error importing PyMuPDF directly: {e2}")
        print("\nPyMuPDF installation failed. Please try reinstalling:")
        print("pip uninstall -y PyMuPDF fitz")
        print("pip install --no-cache-dir PyMuPDF==1.26.3")