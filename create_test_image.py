#!/usr/bin/env python
"""
Create a test image with handwritten-like text for OCR testing.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_test_image():
    """Create a test image with handwritten-like text."""
    # Create a white background image
    width = 800
    height = 600
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Try to use a handwriting-like font
    try:
        # Try to use a handwriting font if available
        font = ImageFont.truetype("arial.ttf", 32)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Add some test text
    text = """Question 1: What is the capital of France?
Answer: Paris

Question 2: What is 2+2?
Answer: 4

Question 3: What is the largest planet in our solar system?
Answer: Jupiter"""
    
    # Draw the text
    draw.text((50, 50), text, fill='black', font=font)
    
    # Save the image
    output_file = "test.jpg"
    image.save(output_file)
    print(f"Test image created: {output_file}")
    return output_file

if __name__ == "__main__":
    create_test_image() 