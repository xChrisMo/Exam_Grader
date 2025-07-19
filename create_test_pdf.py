#!/usr/bin/env python3
"""
Create a simple test PDF with text content for upload testing.
"""

import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_test_pdf_with_text():
    """Create a simple PDF with readable text content."""
    filename = "test_submission_with_text.pdf"
    filepath = os.path.join("temp", filename)
    
    # Ensure temp directory exists
    os.makedirs("temp", exist_ok=True)
    
    # Create PDF with text
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    # Add some text content
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 100, "Student Name: John Doe")
    c.drawString(100, height - 120, "Student ID: 12345")
    c.drawString(100, height - 150, "Question 1: What is 2 + 2?")
    c.drawString(100, height - 170, "Answer: 4")
    c.drawString(100, height - 200, "Question 2: Explain photosynthesis.")
    c.drawString(100, height - 220, "Answer: Photosynthesis is the process by which plants")
    c.drawString(100, height - 240, "convert sunlight into energy using chlorophyll.")
    
    c.save()
    print(f"Created test PDF: {filepath}")
    return filepath

if __name__ == "__main__":
    create_test_pdf_with_text()