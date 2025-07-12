# Import Troubleshooting Guide

## Issue: ModuleNotFoundError for 'utils.guide_verification'

### Problem
The application fails to start with the error:
```
ERROR: Failed to import required modules: cannot import name 'is_guide_in_use' from 'utils'
```

### Root Cause
This error typically occurs when:
1. The application is run from the wrong directory
2. The Python path doesn't include the project root
3. The utils package isn't properly configured

### Solution

#### Step 1: Verify Directory
Make sure you're in the correct project directory:
```bash
cd /path/to/Exam_Grader
```

The directory should contain:
- `run_app.py`
- `webapp/exam_grader_app.py`
- `utils/__init__.py`
- `src/` folder

#### Step 2: Run Setup Verification
```bash
python verify_setup.py
```

This script will:
- Check if you're in the correct directory
- Verify all imports work correctly
- Provide guidance if issues are found

#### Step 3: Start the Application
Use the recommended startup method:
```bash
python run_app.py
```

Or alternatively:
```bash
python webapp/exam_grader_app.py
```

### What Was Fixed

1. **Updated `utils/__init__.py`**:
   - Added automatic Python path setup
   - Added fallback imports with error handling
   - Created dummy functions if imports fail

2. **Moved imports to proper location**:
   - Moved `is_guide_in_use` import to the top of files
   - Changed from direct module import to package import

3. **Added verification scripts**:
   - `verify_setup.py` - Checks setup before running
   - `fix_imports.py` - Diagnoses import issues

### Prevention

- Always run the application from the project root directory
- Use `python run_app.py` as the preferred startup method
- Run `python verify_setup.py` if you encounter import issues

### Directory Structure
```
Exam_Grader/
├── run_app.py              # Preferred startup script
├── verify_setup.py         # Setup verification
├── webapp/
│   ├── exam_grader_app.py  # Main Flask application
│   └── optimized_routes.py
├── utils/
│   ├── __init__.py         # Package initialization (fixed)
│   ├── guide_verification.py
│   └── logger.py
├── src/
│   ├── config/
│   ├── database/
│   └── services/
└── ...
```

### Additional Notes

- The `utils/__init__.py` now includes robust error handling
- Fallback functions are provided if imports fail
- The application will show warning messages but continue to run
- Always check the console output for any warning messages