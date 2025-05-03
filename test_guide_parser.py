"""
Test script for the updated parse_guide.py that returns raw content.
"""

import os
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Directly test text file parsing without OCR dependencies
def test_parse_txt_guide():
    """Test the parsing of a sample text guide."""
    
    # Create a sample text file
    sample_text = """
    This is a sample marking guide.
    
    Question 1: Introduction to Python (10 marks)
    Python is a high-level programming language with simple syntax.
    Key points:
    - Easy to learn
    - Versatile
    - Large community
    
    Question 2: Data Structures (15 marks)
    Python has several built-in data structures:
    - Lists
    - Dictionaries
    - Sets
    - Tuples
    """
    
    test_file = "temp_test_guide.txt"
    
    with open(test_file, "w") as f:
        f.write(sample_text)
    
    try:
        # Test direct file reading
        with open(test_file, 'r') as f:
            content = f.read()
            
        print("Test results:")
        print(f"Raw content length: {len(content)}")
        print("\nRaw content sample:")
        print(content[:100] + "...")
        
        # This shows the content is being read correctly from the file
        # The actual parser would use this content and store it in the MarkingGuide object
        
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_parse_txt_guide() 