@echo off
echo ====================================
echo Exam Grader Parser Test Tool
echo ====================================
echo.
echo This script will test the parsers with sample files
echo.

echo Testing Guide Parser...
python test_guide_parser.py

echo.
echo.
echo All tests completed!
echo You can now run the application with: python -m web.app
echo.
pause 