# Developer Migration Guide

**Version:** Post-Cleanup Architecture  
**Date:** January 4, 2025  
**Audience:** Development Team  
**Status:** Required Reading

## Overview

This guide helps developers migrate from the old service architecture to the new consolidated service structure. The cleanup consolidated 60+ services into 12 well-organized services while maintaining all functionality.

## 🚨 Breaking Changes Summary

### Import Path Changes
All service imports have been updated to reflect the new consolidated structure.

### Configuration Changes
Configuration now uses a unified system with environment variables.

### Service Interface Changes
Some service method signatures have been updated for consistency.

## Import Path Migration

### File Processing Services

#### ❌ Old Imports (DEPRECATED)
```python
# These imports will no longer work
from src.services.enhanced_file_processing_service import EnhancedFileProcessingService
from src.services.file_processor_chain import FileProcessorChain
from src.services.ultra_fast_processing import UltraFastProcessingService
from src.services.fast_processing_service import FastProcessingService
```

#### ✅ New Imports (REQUIRED)
```python
# Use these imports instead
from src.services.file_processing_service import FileProcessingService
from src.services.core.file_processing_service import FileProcessingService as CoreFileProcessingService
```

#### Migration Example
```python
# OLD CODE
from src.services.enhanced_file_processing_service import enhanced_file_processing_service
result = enhanced_file_processing_service.process_file(file_path)

# NEW CODE
from src.services.file_processing_service import FileProcessingService
service = FileProcessingService()
result = service.process_file_with_fallback(file_path, file_info)
```

### LLM Services

#### ❌ Old Imports (DEPRECATED)
```python
from src.services.llm_enhancements import LLMEnhancementService
from src.services.llm_training_service import LLMTrainingService
```

#### ✅ New Imports (REQUIRED)
```python
from src.services.consolidated_llm_service import ConsolidatedLLMService
from src.services.enhanced_training_service import EnhancedTrainingService
```

#### Migration Example
```python
# OLD CODE
from src.services.llm_enhancements import llm_enhancement_service
response = llm_enhancement_service.generate_response(prompt)

# NEW CODE
from src.services.consolidated_llm_service import ConsolidatedLLMService
service = ConsolidatedLLMService()
response = service.generate_response(system_prompt=system_prompt, user_prompt=prompt)
```

### OCR Services

#### ❌ Old Imports (DEPRECATED)
```python
from src.services.ocr_fallback_service import OCRFallbackService
from src.services.handwriting_ocr_service import HandwritingOCRService
```

#### ✅ New Imports (REQUIRED)
```python
from src.services.consolidated_ocr_service import ConsolidatedOCRService
```

#### Migration Example
```python
# OLD CODE
from src.services.handwriting_ocr_service import handwriting_ocr_service
result = handwriting_ocr_service.extract_text(image_path)

# NEW CODE
from src.services.consolidated_ocr_service import ConsolidatedOCRService
service = ConsolidatedOCRService()
result = service.extract_text(image_path)
```

### Grading Services

#### ❌ Old Imports (DEPRECATED)
```python
from src.services.grading_enhancements import GradingEnhancementService
from src.services.intelligent_grading_service import IntelligentGradingService
```

#### ✅ New Imports (REQUIRED)
```python
from src.services.consolidated_grading_service import ConsolidatedGradingService
```

### Monitoring Services

#### ❌ Old Imports (DEPRECATED)
```python
from src.services.health_monitor import HealthMonitor
from src.services.performance_monitor import PerformanceMonitor
from src.services.system_monitoring import SystemMonitoring
```

#### ✅ New Imports (REQUIRED)
```python
from src.services.monitoring.monitoring_service import MonitoringService
```

### Error Handling Services

#### ❌ Old Imports (DEPRECATED)
```python
from src.services.enhanced_error_handler import EnhancedErrorHandler
from src.services.error_handling_service import ErrorHandlingService
from src.services.error_tracking_service import ErrorTrackingService
```

#### ✅ New Imports (REQUIRED)
```python
from src.services.core.error_service import ErrorService
```

### Background Task Services

#### ❌ Old Imports (DEPRECATED)
```python
from src.services.background_tasks import BackgroundTaskService
from src.services.optimized_background_tasks import OptimizedBackgroundTasks
```

#### ✅ New Imports (REQUIRED)
```python
from src.services.background.task_manager import TaskManager
from src.services.background.scheduler_service import SchedulerService
from src.services.background.file_cleanup_service import FileCleanupService
```

## Configuration Migration

### Environment Variables

#### ❌ Old Configuration (DEPRECATED)
```bash
# Old scattered configuration
DEEPSEEK_SEED=12345
OCR_API_KEY=your_key
LLM_API_KEY=your_key
```

#### ✅ New Configuration (REQUIRED)
```bash
# New unified configuration
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_RANDOM_SEED=12345
HANDWRITING_OCR_API_KEY=your_ocr_api_key
OPENAI_API_KEY=your_openai_api_key
SECRETS_MASTER_KEY=your_master_key
```

### Configuration Access

#### ❌ Old Configuration Access (DEPRECATED)
```python
import os
api_key = os.getenv('OCR_API_KEY')
```

#### ✅ New Configuration Access (REQUIRED)
```python
from src.config.unified_config import unified_config
api_key = unified_config.get('HANDWRITING_OCR_API_KEY')
```

## Service Interface Changes

### File Processing Service

#### Method Signature Changes
```python
# OLD METHOD
def process_file(self, file_path: str) -> ProcessingResult:
    pass

# NEW METHOD
def process_file_with_fallback(self, file_path: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
    pass
```

#### Return Format Changes
```python
# OLD RETURN FORMAT
class ProcessingResult:
    success: bool
    content: str
    method_used: str
    processing_time: float

# NEW RETURN FORMAT
{
    "success": bool,
    "text_content": str,
    "word_count": int,
    "character_count": int,
    "extraction_method": str,
    "processing_duration_ms": int,
    "content_quality_score": float,
    "validation_status": str,
    "processing_timestamp": str
}
```

### LLM Service

#### Method Signature Changes
```python
# OLD METHOD
def generate_response(self, prompt: str, model: str = None) -> str:
    pass

# NEW METHOD
def generate_response(self, system_prompt: str, user_prompt: str, 
                     temperature: float = 0.7, max_tokens: int = None) -> str:
    pass
```

### Error Handling

#### ❌ Old Error Handling (DEPRECATED)
```python
try:
    result = service.process_file(file_path)
except ProcessingError as e:
    logger.error(f"Processing failed: {e}")
```

#### ✅ New Error Handling (REQUIRED)
```python
from src.services.core.error_service import error_service

try:
    result = service.process_file_with_fallback(file_path, file_info)
except Exception as e:
    error_result = error_service.handle_error(e, {
        'operation': 'file_processing',
        'file_path': file_path
    })
    if not error_result.get('recovered'):
        raise
```

## Database Changes

### Model Import Changes

#### ❌ Old Imports (DEPRECATED)
```python
from src.models.user import User
from src.models.submission import Submission
```

#### ✅ New Imports (REQUIRED)
```python
from src.database.models import User, Submission, MarkingGuide, GradingResult
```

### Query Pattern Changes

#### ❌ Old Query Patterns (DEPRECATED)
```python
# Raw SQL queries
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

#### ✅ New Query Patterns (REQUIRED)
```python
# SQLAlchemy ORM queries
user = User.query.filter_by(id=user_id).first()
```

## Testing Changes

### Test Import Updates

#### ❌ Old Test Imports (DEPRECATED)
```python
from src.services.enhanced_file_processing_service import enhanced_file_processing_service
```

#### ✅ New Test Imports (REQUIRED)
```python
from src.services.file_processing_service import FileProcessingService
```

### Test Pattern Updates

#### Updated Test Structure
```python
# OLD TEST PATTERN
def test_file_processing():
    result = enhanced_file_processing_service.process_file('test.pdf')
    assert result.success

# NEW TEST PATTERN
def test_file_processing():
    service = FileProcessingService()
    result = service.process_file_with_fallback('test.pdf', {
        'filename': 'test.pdf',
        'file_extension': '.pdf'
    })
    assert result['success']
```

## Common Migration Patterns

### Pattern 1: Service Initialization

#### ❌ Old Pattern
```python
# Services were often imported as global instances
from src.services.some_service import some_service_instance
result = some_service_instance.method()
```

#### ✅ New Pattern
```python
# Services are now instantiated when needed
from src.services.consolidated_service import ConsolidatedService
service = ConsolidatedService()
result = service.method()
```

### Pattern 2: Error Handling

#### ❌ Old Pattern
```python
try:
    result = service.risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    return None
```

#### ✅ New Pattern
```python
from src.services.core.error_service import error_service

try:
    result = service.risky_operation()
except Exception as e:
    error_result = error_service.handle_error(e, {
        'operation': 'risky_operation',
        'context': 'additional_context'
    })
    if error_result.get('recovered'):
        result = error_result.get('result')
    else:
        raise
```

### Pattern 3: Configuration Access

#### ❌ Old Pattern
```python
import os
config_value = os.getenv('CONFIG_KEY', 'default_value')
```

#### ✅ New Pattern
```python
from src.config.unified_config import unified_config
config_value = unified_config.get('CONFIG_KEY', 'default_value')
```

## Step-by-Step Migration Process

### Step 1: Update Imports
1. Search for all old service imports in your code
2. Replace with new consolidated service imports
3. Update any global service instances to local instantiation

### Step 2: Update Method Calls
1. Check method signatures for any changes
2. Update parameter names and types
3. Update return value handling

### Step 3: Update Configuration
1. Move configuration to environment variables
2. Update configuration access to use unified_config
3. Validate all required environment variables are set

### Step 4: Update Error Handling
1. Replace specific error handling with centralized error service
2. Update error logging patterns
3. Add proper error context

### Step 5: Update Tests
1. Update test imports
2. Update test patterns to match new service interfaces
3. Run full test suite to validate changes

### Step 6: Validate Changes
1. Run application locally
2. Test all affected functionality
3. Check logs for any import or configuration errors

## Automated Migration Tools

### Import Update Script
```python
#!/usr/bin/env python3
"""
Automated import update script
Run this to automatically update most import statements
"""

import os
import re
from pathlib import Path

# Import mapping
IMPORT_MAPPINGS = {
    'from src.services.enhanced_file_processing_service import': 'from src.services.file_processing_service import',
    'from src.services.file_processor_chain import': 'from src.services.core.file_processing_service import',
    'from src.services.llm_enhancements import': 'from src.services.consolidated_llm_service import',
    'from src.services.health_monitor import': 'from src.services.monitoring.monitoring_service import',
    # Add more mappings as needed
}

def update_imports_in_file(file_path):
    """Update imports in a single file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    for old_import, new_import in IMPORT_MAPPINGS.items():
        content = content.replace(old_import, new_import)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated imports in {file_path}")

def main():
    """Main migration function"""
    # Update all Python files
    for py_file in Path('.').rglob('*.py'):
        if 'backup_services' not in str(py_file):  # Skip backup directory
            update_imports_in_file(py_file)

if __name__ == '__main__':
    main()
```

### Configuration Migration Script
```python
#!/usr/bin/env python3
"""
Configuration migration script
Updates environment variable names
"""

import os
import re

def migrate_env_file():
    """Migrate .env file to new format"""
    if not os.path.exists('.env'):
        print("No .env file found")
        return
    
    with open('.env', 'r') as f:
        content = f.read()
    
    # Environment variable mappings
    mappings = {
        'DEEPSEEK_SEED': 'DEEPSEEK_RANDOM_SEED',
        'OCR_API_KEY': 'HANDWRITING_OCR_API_KEY',
        'LLM_API_KEY': 'OPENAI_API_KEY',
    }
    
    for old_var, new_var in mappings.items():
        content = re.sub(f'^{old_var}=', f'{new_var}=', content, flags=re.MULTILINE)
    
    with open('.env', 'w') as f:
        f.write(content)
    
    print("Environment variables migrated")

if __name__ == '__main__':
    migrate_env_file()
```

## Troubleshooting Common Issues

### Issue 1: Import Errors

#### Problem
```
ImportError: cannot import name 'enhanced_file_processing_service' from 'src.services.enhanced_file_processing_service'
```

#### Solution
```python
# Replace the old import
from src.services.enhanced_file_processing_service import enhanced_file_processing_service

# With the new import
from src.services.file_processing_service import FileProcessingService
service = FileProcessingService()
```

### Issue 2: Configuration Errors

#### Problem
```
KeyError: 'OCR_API_KEY'
```

#### Solution
1. Update your `.env` file:
```bash
# OLD
OCR_API_KEY=your_key

# NEW
HANDWRITING_OCR_API_KEY=your_key
```

2. Update your code:
```python
# OLD
api_key = os.getenv('OCR_API_KEY')

# NEW
from src.config.unified_config import unified_config
api_key = unified_config.get('HANDWRITING_OCR_API_KEY')
```

### Issue 3: Method Signature Errors

#### Problem
```
TypeError: process_file() missing 1 required positional argument: 'file_info'
```

#### Solution
```python
# OLD
result = service.process_file(file_path)

# NEW
result = service.process_file_with_fallback(file_path, {
    'filename': os.path.basename(file_path),
    'file_extension': os.path.splitext(file_path)[1]
})
```

### Issue 4: Return Format Changes

#### Problem
```
AttributeError: 'dict' object has no attribute 'success'
```

#### Solution
```python
# OLD
if result.success:
    content = result.content

# NEW
if result['success']:
    content = result['text_content']
```

### Issue 5: Service Instance Errors

#### Problem
```
NameError: name 'enhanced_file_processing_service' is not defined
```

#### Solution
```python
# OLD
from src.services.enhanced_file_processing_service import enhanced_file_processing_service
result = enhanced_file_processing_service.process_file(file_path)

# NEW
from src.services.file_processing_service import FileProcessingService
service = FileProcessingService()
result = service.process_file_with_fallback(file_path, file_info)
```

## Testing Your Migration

### Pre-Migration Checklist
- [ ] Backup your current codebase
- [ ] Document any custom modifications
- [ ] Run existing tests to establish baseline
- [ ] Review all service usage in your code

### Migration Checklist
- [ ] Update all import statements
- [ ] Update method calls and parameters
- [ ] Update configuration access
- [ ] Update error handling patterns
- [ ] Update test files
- [ ] Update environment variables

### Post-Migration Validation
- [ ] Run full test suite
- [ ] Start application locally
- [ ] Test core functionality
- [ ] Check application logs for errors
- [ ] Validate all features work as expected

### Validation Commands
```bash
# Run tests
python -m pytest tests/ -v

# Check for import errors
python -c "from webapp.app_factory import create_app; app = create_app('testing'); print('✓ App creation successful')"

# Run performance validation
python performance_profiler.py

# Check service health
python -c "
from src.services.consolidated_llm_service import ConsolidatedLLMService
from src.services.consolidated_ocr_service import ConsolidatedOCRService
from src.services.file_processing_service import FileProcessingService
print('✓ All services import successfully')
"
```

## Getting Help

### Documentation Resources
- [Project Structure Documentation](PROJECT_STRUCTURE.md)
- [Service Documentation](SERVICE_DOCUMENTATION.md)
- [API Documentation](API_DOCUMENTATION.md)
- [Codebase Cleanup Summary](../CODEBASE_CLEANUP_SUMMARY.md)

### Common Questions

#### Q: Can I still use the old services?
A: No, the old services have been removed. You must migrate to the new consolidated services.

#### Q: Will my existing data be affected?
A: No, database schema and data remain unchanged. Only the service layer has been consolidated.

#### Q: How do I know if my migration is complete?
A: Run the validation commands above. If they all pass without errors, your migration is complete.

#### Q: What if I have custom extensions?
A: Review your custom code for any dependencies on old services and update them using the patterns in this guide.

#### Q: Are there any performance implications?
A: Performance should be improved due to service consolidation and optimization. The cleanup achieved an 80% reduction in service complexity.

## Support

If you encounter issues during migration:

1. **Check this guide** for common patterns and solutions
2. **Review the error message** and match it to troubleshooting section
3. **Run validation commands** to identify specific issues
4. **Check logs** for detailed error information
5. **Consult team members** who have completed migration

## Migration Timeline

### Recommended Migration Schedule
- **Week 1:** Review guide and plan migration
- **Week 2:** Update development environment
- **Week 3:** Migrate and test core functionality
- **Week 4:** Complete testing and validation

### Critical Deadlines
- **Immediate:** Stop using deprecated imports
- **Within 1 week:** Complete environment variable migration
- **Within 2 weeks:** Complete service import migration
- **Within 1 month:** Complete full migration and validation

---

**Document Version:** 1.0  
**Last Updated:** January 4, 2025  
**Status:** Required for all developers  
**Next Review:** February 4, 2025