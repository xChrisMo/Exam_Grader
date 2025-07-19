#!/usr/bin/env python3
"""
Diagnostic script to analyze PDF processing issues.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import fitz  # PyMuPDF
from src.parsing.parse_submission import DocumentParser
from utils.logger import logger

def analyze_pdf(pdf_path):
    """Analyze a PDF file to understand why text extraction might be failing."""
    print(f"\nAnalyzing PDF: {pdf_path}")
    print("=" * 60)
    
    if not os.path.exists(pdf_path):
        print(f"✗ File not found: {pdf_path}")
        return False
    
    try:
        # Basic file info
        file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # MB
        print(f"File size: {file_size:.2f} MB")
        
        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        print(f"Number of pages: {doc.page_count}")
        
        if doc.page_count == 0:
            print("✗ PDF has no pages")
            doc.close()
            return False
        
        # Analyze each page
        total_text_length = 0
        pages_with_text = 0
        pages_with_images = 0
        
        for page_num, page in enumerate(doc, 1):
            try:
                # Get text
                page_text = page.get_text()
                text_length = len(page_text.strip())
                total_text_length += text_length
                
                if text_length > 0:
                    pages_with_text += 1
                
                # Check for images
                image_list = page.get_images()
                if image_list:
                    pages_with_images += 1
                
                print(f"  Page {page_num}: {text_length} chars, {len(image_list)} images")
                
                # Show sample text from first page
                if page_num == 1 and text_length > 0:
                    sample_text = page_text.strip()[:200]
                    print(f"  Sample text: {repr(sample_text)}")
                
            except Exception as e:
                print(f"  Page {page_num}: Error - {e}")
        
        doc.close()
        
        # Summary
        print(f"\nSummary:")
        print(f"  Total text characters: {total_text_length}")
        print(f"  Pages with text: {pages_with_text}/{doc.page_count}")
        print(f"  Pages with images: {pages_with_images}/{doc.page_count}")
        
        # Diagnosis
        if total_text_length == 0:
            print(f"\n🔍 Diagnosis: PDF contains no extractable text")
            if pages_with_images > 0:
                print(f"   - PDF appears to be scanned/image-based")
                print(f"   - OCR processing would be required")
            else:
                print(f"   - PDF may be corrupted or empty")
        elif total_text_length < 50:
            print(f"\n🔍 Diagnosis: PDF contains very little text")
            print(f"   - May be mostly images or have formatting issues")
            print(f"   - OCR might help extract additional content")
        else:
            print(f"\n✓ Diagnosis: PDF should process normally")
            print(f"   - Contains sufficient extractable text")
        
        return True
        
    except Exception as e:
        print(f"✗ Error analyzing PDF: {e}")
        return False

def test_pdf_extraction(pdf_path):
    """Test the actual PDF extraction process."""
    print(f"\nTesting extraction process for: {pdf_path}")
    print("-" * 50)
    
    try:
        # Test direct PDF extraction
        print("1. Testing direct PDF text extraction...")
        text = DocumentParser.extract_text_from_pdf(pdf_path)
        
        if text and text.strip():
            print(f"   ✓ Success: Extracted {len(text)} characters")
            print(f"   Sample: {repr(text[:100])}")
        else:
            print(f"   ⚠ No text extracted (returned: {repr(text)})")
        
        # Test full parsing process
        print("\n2. Testing full parsing process...")
        result, raw_text, error = DocumentParser.parse_student_submission(pdf_path)
        
        if error:
            print(f"   ✗ Error: {error}")
        elif raw_text:
            print(f"   ✓ Success: Extracted {len(raw_text)} characters")
        else:
            print(f"   ⚠ No text returned")
            
    except Exception as e:
        print(f"   ✗ Exception: {e}")

def main():
    """Main diagnostic function."""
    print("PDF Processing Diagnostic Tool")
    print("=" * 50)
    
    # Check if specific PDF files are provided
    if len(sys.argv) > 1:
        pdf_files = sys.argv[1:]
    else:
        # Look for common PDF locations
        pdf_files = []
        
        # Check uploads directory
        uploads_dir = Path("uploads")
        if uploads_dir.exists():
            pdf_files.extend(uploads_dir.glob("*.pdf"))
        
        # Check current directory
        pdf_files.extend(Path(".").glob("*.pdf"))
        
        if not pdf_files:
            print("No PDF files found. Usage:")
            print("  python diagnose_pdf_issues.py file1.pdf file2.pdf ...")
            print("  or place PDF files in the current directory or uploads/ folder")
            return
    
    # Analyze each PDF
    for pdf_file in pdf_files:
        analyze_pdf(str(pdf_file))
        test_pdf_extraction(str(pdf_file))
        print("\n" + "="*60)

if __name__ == "__main__":
    main()