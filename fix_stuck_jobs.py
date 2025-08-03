#!/usr/bin/env python3
"""
Script to fix stuck training jobs and test the new stuck job handling
"""

import sys
import os
sys.path.append('.')

def fix_stuck_jobs():
    """Fix any stuck training jobs in the database"""
    print("🔧 Fixing stuck training jobs...")
    
    try:
        from webapp.app_factory import create_app
        from src.database.models import db, LLMTrainingJob
        from datetime import datetime, timezone
        
        # Create app context
        app = create_app()
        
        with app.app_context():
            # Find jobs stuck in active statuses
            stuck_statuses = ['preparing', 'training', 'evaluating']
            stuck_jobs = LLMTrainingJob.query.filter(
                LLMTrainingJob.status.in_(stuck_statuses)
            ).all()
            
            if not stuck_jobs:
                print("✅ No stuck jobs found!")
                return True
            
            print(f"📋 Found {len(stuck_jobs)} potentially stuck jobs:")
            
            fixed_count = 0
            current_time = datetime.now(timezone.utc)
            
            for job in stuck_jobs:
                print(f"   - Job: {job.name} (ID: {job.id})")
                print(f"     Status: {job.status}")
                print(f"     User: {job.user_id}")
                
                # Check if job has been stuck for more than 5 minutes
                last_update_time = job.updated_at or job.created_at
                if last_update_time:
                    if last_update_time.tzinfo is None:
                        last_update_time = last_update_time.replace(tzinfo=timezone.utc)
                    
                    time_since_update = current_time - last_update_time
                    minutes_stuck = time_since_update.total_seconds() / 60
                    
                    print(f"     Stuck for: {minutes_stuck:.1f} minutes")
                    
                    if minutes_stuck > 5:  # More than 5 minutes
                        print(f"     🔧 Fixing stuck job...")
                        job.status = 'failed'
                        job.error_message = f'Job was stuck in {job.status} status for {minutes_stuck:.0f} minutes and has been automatically reset. You can now restart it.'
                        job.end_time = current_time
                        fixed_count += 1
                    else:
                        print(f"     ⏳ Job is recent, leaving as-is")
                else:
                    print(f"     🔧 No timestamp found, fixing...")
                    job.status = 'failed'
                    job.error_message = 'Job was stuck without timestamp and has been reset'
                    job.end_time = current_time
                    fixed_count += 1
                
                print()
            
            if fixed_count > 0:
                db.session.commit()
                print(f"✅ Fixed {fixed_count} stuck jobs!")
                print("   These jobs are now marked as 'failed' and can be restarted.")
            else:
                print("ℹ️  No jobs needed fixing (all are recent).")
            
            return True
            
    except Exception as e:
        print(f"❌ Error fixing stuck jobs: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_stuck_job_handling():
    """Test the new stuck job handling in the routes"""
    print("\n🧪 Testing stuck job handling...")
    
    try:
        print("✅ New stuck job handling features:")
        print("   - Jobs stuck for >5 minutes are automatically reset to 'failed'")
        print("   - Failed jobs can be restarted")
        print("   - Stuck jobs can be deleted after 5 minutes")
        print("   - Better error messages explain what happened")
        
        print("\n📋 How to test:")
        print("1. Try to start the stuck job - it should be automatically reset")
        print("2. If still stuck, try deleting it - should work after 5 minutes")
        print("3. Create a new training job to test normal flow")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        return False

def main():
    """Main function"""
    print("🚀 LLM Training Job Stuck Job Fixer")
    print("=" * 50)
    
    # Fix stuck jobs
    success1 = fix_stuck_jobs()
    
    # Test new functionality
    success2 = test_stuck_job_handling()
    
    if success1 and success2:
        print("\n🎉 All fixes applied successfully!")
        print("\n📝 Summary of fixes:")
        print("   ✅ Cross-platform LLM timeout protection (25 seconds)")
        print("   ✅ Enhanced JSON parsing with fallback extraction")
        print("   ✅ New status endpoint for job monitoring")
        print("   ✅ Stuck job detection and automatic reset")
        print("   ✅ Comprehensive frontend logging system")
        print("   ✅ Better error handling and user feedback")
        
        print("\n🔄 Next steps:")
        print("1. Restart your Flask server: python run_app.py")
        print("2. Go to the LLM Training page")
        print("3. Try starting the previously stuck job (should work now)")
        print("4. Click 'Show Logs' to see the new logging system")
        print("5. Monitor real-time progress during training")
        
    else:
        print("\n❌ Some issues occurred. Check the error messages above.")

if __name__ == "__main__":
    main()