# Question Mapping Fix Guide

## Issue Description

The system was incorrectly retrieving and using mappings from ALL submissions that used the same marking guide, rather than only retrieving mappings for the specific submission being processed. This caused the system to return mappings from previous submissions, leading to incorrect processing results.

## Root Cause

The `_get_existing_mappings_from_db` method in `src/services/core_service.py` was querying the database for ALL mappings associated with a guide, regardless of which specific submission was being processed:

```python
# PROBLEMATIC CODE (before fix)
existing_mappings = db.session.query(Mapping).filter(
    Mapping.submission_id.in_(
        db.session.query(Submission.id).filter(Submission.marking_guide_id == guide_id)
    )
).all()
```

This query would return mappings from ALL submissions that used the same guide, not just the current submission.

## Solution Implemented

### 1. Updated Method Signature

Modified `_get_existing_mappings_from_db` to accept an optional `submission_id` parameter:

```python
def _get_existing_mappings_from_db(self, guide_id: str, submission_id: str = None) -> Optional[List[Dict]]:
```

### 2. Enhanced Query Logic

Updated the method to filter by specific submission when `submission_id` is provided:

```python
# Get existing mappings for this guide and optionally specific submission
if submission_id:
    # Get mappings for specific submission
    existing_mappings = db.session.query(Mapping).filter(
        Mapping.submission_id == submission_id
    ).all()
else:
    # Get mappings for all submissions using this guide (legacy behavior)
    existing_mappings = db.session.query(Mapping).filter(
        Mapping.submission_id.in_(
            db.session.query(Submission.id).filter(Submission.marking_guide_id == guide_id)
        )
    ).all()
```

### 3. Updated Method Call

Modified the `_map_answers` method to pass the submission ID:

```python
# Before
mappings = await self._map_answers(guide, submission_text)

# After  
mappings = await self._map_answers(guide, submission_text, submission.id)
```

### 4. Enhanced Logging

Improved logging to distinguish between submission-specific and guide-wide mapping retrieval:

```python
if submission_id:
    logger.info(f"Found {len(existing_mappings)} existing mappings in database for submission {submission_id}")
else:
    logger.info(f"Found {len(existing_mappings)} existing mappings in database for guide {guide_id}")
```

## Files Modified

1. **`src/services/core_service.py`**
   - Updated `_map_answers` method signature to accept `submission_id`
   - Modified `_get_existing_mappings_from_db` to filter by specific submission
   - Enhanced logging for better debugging
   - Updated method call to pass submission ID

## Expected Results

### Before Fix
- System would retrieve mappings from ALL submissions using the same guide
- Processing would use incorrect mappings from previous submissions
- Results would be inconsistent and potentially wrong

### After Fix
- System only retrieves mappings for the specific submission being processed
- Each submission is processed independently
- Results are accurate and consistent
- Better performance due to more targeted database queries

## Testing

To verify the fix is working:

1. **Check Logs**: Look for log messages like:
   ```
   INFO - Found X existing mappings in database for submission [submission_id]
   ```
   Instead of:
   ```
   INFO - Found X existing mappings in database for guide [guide_id]
   ```

2. **Database Queries**: The system should now make more targeted queries:
   ```sql
   -- New behavior (correct)
   SELECT * FROM mappings WHERE submission_id = 'specific-submission-id'
   
   -- Old behavior (incorrect)
   SELECT * FROM mappings WHERE submission_id IN (
       SELECT id FROM submissions WHERE marking_guide_id = 'guide-id'
   )
   ```

3. **Processing Results**: Each submission should be processed independently without interference from other submissions using the same guide.

## Backward Compatibility

The fix maintains backward compatibility:
- The `submission_id` parameter is optional
- When not provided, the method falls back to the original behavior
- Existing code that doesn't pass `submission_id` will continue to work

## Performance Impact

**Positive Impact:**
- More targeted database queries (faster execution)
- Reduced memory usage (fewer mappings loaded)
- Better cache efficiency

**No Negative Impact:**
- No breaking changes to existing functionality
- Maintains all existing features
- Improved accuracy and reliability

## Related Issues

This fix resolves the issue where:
- "All questions in the db are mapped only mapped question for the selected guide"
- System was incorrectly reusing mappings from other submissions
- Processing results were inconsistent across submissions

## Future Improvements

Consider implementing:
1. **Mapping Validation**: Verify that retrieved mappings actually belong to the correct submission
2. **Cache Invalidation**: Clear cached mappings when submissions are updated
3. **Audit Trail**: Track when mappings are retrieved and used for debugging
4. **Performance Monitoring**: Monitor query performance for mapping retrieval

## Support

If you encounter any issues after this fix:
1. Check the logs for the new submission-specific messages
2. Verify that each submission is being processed independently
3. Ensure database queries are targeting specific submissions
4. Contact the development team with specific error messages or unexpected behavior
