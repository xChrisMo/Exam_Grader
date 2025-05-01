import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.parsing.parse_guide import parse_marking_guide

def main():
    # Test with simple file
    simple_test_path = os.path.join('temp', 'simple_test.txt')
    print(f"Testing with simple file: {simple_test_path}")
    print(f"File exists: {os.path.exists(simple_test_path)}")
    
    guide, error = parse_marking_guide(simple_test_path)
    if error:
        print(f"Error: {error}")
    else:
        print(f"Success! Questions: {len(guide.questions)}, Total marks: {guide.total_marks}")
        
    # Test with full guide
    full_test_path = os.path.join('temp', 'test_guide.txt')
    print(f"\nTesting with full guide: {full_test_path}")
    print(f"File exists: {os.path.exists(full_test_path)}")
    
    guide, error = parse_marking_guide(full_test_path)
    if error:
        print(f"Error: {error}")
    else:
        print(f"Success! Questions: {len(guide.questions)}, Total marks: {guide.total_marks}")

if __name__ == '__main__':
    main() 