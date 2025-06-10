#!/usr/bin/env python3
"""
Script to fix logger method calls throughout the codebase.
Replaces log_info, log_warning, log_error, log_debug with standard methods.
"""

import os
import re
from pathlib import Path

def fix_logger_methods(file_path):
    """Fix logger method calls in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Replace logger method calls
        replacements = [
            (r'logger\.log_info\(', 'logger.info('),
            (r'logger\.log_warning\(', 'logger.warning('),
            (r'logger\.log_error\(', 'logger.error('),
            (r'logger\.log_debug\(', 'logger.debug('),
        ]

        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)

        # Fix specific error patterns where there are two arguments
        # logger.error("Type", "message") -> logger.error("Type: message")
        content = re.sub(
            r'logger\.error\(\s*"([^"]+)",\s*f?"([^"]+)"\s*\)',
            r'logger.error(f"\1: \2")',
            content
        )

        # Fix remaining patterns with string concatenation
        content = re.sub(
            r'logger\.error\(\s*"([^"]+)",\s*([^)]+)\)',
            r'logger.error(f"\1: {str(\2)}")',
            content
        )

        # Fix multiline logger calls
        content = re.sub(
            r'logger\.error\(\s*\n\s*"([^"]+)",\s*f?"([^"]+)"\s*\n\s*\)',
            r'logger.error(f"\1: \2")',
            content,
            flags=re.MULTILINE
        )

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed logger methods in: {file_path}")
            return True
        else:
            print(f"No changes needed in: {file_path}")
            return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix logger methods in all Python files."""
    files_to_fix = [
        "src/parsing/parse_submission.py",
        "src/parsing/parse_guide.py",
        "src/services/ocr_service.py",
        "src/services/llm_service.py",
        "src/services/mapping_service.py",
        "src/services/grading_service.py",
        "src/services/file_cleanup_service.py",
        "webapp/exam_grader_app.py",
        "utils/error_handler.py",
        "utils/file_processor.py",
        "utils/input_sanitizer.py",
        "utils/rate_limiter.py",
    ]
    
    fixed_count = 0
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_logger_methods(file_path):
                fixed_count += 1
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nFixed logger methods in {fixed_count} files.")

if __name__ == "__main__":
    main()
