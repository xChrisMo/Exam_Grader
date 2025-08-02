#!/usr/bin/env python3
"""
Fix Hanging Training Jobs Script

This script identifies and fixes training jobs that are taking too long to complete.
It applies the fixes from the LLM Training Service Fix module.
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webapp.app import create_app
from src.database.models import db, LLMTrainingJob
from src.services.llm_training_service import LLMTrainingService
from src.services.llm_training_service_fix import apply_training_service_fixes
from utils.logger import logger

def main():
    """Main function to fix hanging training jobs"""
    print("🔧 Starting Training Job Fix Script...")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Initialize the training service
            training_service = LLMTrainingService(app)
            
            # Check for hanging jobs
            print("\n📊 Checking for hanging training jobs...")
            
            # Find jobs that have been running too long (more than 15 minutes)
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=15)
            
            hanging_jobs = db.session.query(LLMTrainingJob).filter(
                LLMTrainingJob.status.in_(['training', 'preparing', 'evaluating']),
                LLMTrainingJob.start_time < cutoff_time
            ).all()
            
            if not hanging_jobs:
                print("✅ No hanging training jobs found!")
                return
            
            print(f"⚠️  Found {len(hanging_jobs)} hanging training jobs:")
            for job in hanging_jobs:
                runtime = datetime.now(timezone.utc) - (job.start_time or datetime.now(timezone.utc))
                print(f"   - Job {job.id}: '{job.name}' (Status: {job.status}, Runtime: {runtime})")
            
            # Apply fixes
            print("\n🛠️  Applying fixes...")
            fix_service = apply_training_service_fixes(training_service)
            
            # Fix each hanging job
            fixed_count = 0
            for job in hanging_jobs:
                print(f"   Fixing job {job.id}...")
                if fix_service.fix_hanging_training_job(job.id):
                    fixed_count += 1
                    print(f"   ✅ Fixed job {job.id}")
                else:
                    print(f"   ❌ Failed to fix job {job.id}")
            
            print(f"\n🎉 Successfully fixed {fixed_count}/{len(hanging_jobs)} hanging training jobs!")
            
            # Show updated status
            print("\n📈 Updated job statuses:")
            updated_jobs = db.session.query(LLMTrainingJob).filter(
                LLMTrainingJob.id.in_([job.id for job in hanging_jobs])
            ).all()
            
            for job in updated_jobs:
                accuracy = f"{job.accuracy * 100:.1f}%" if job.accuracy else "N/A"
                print(f"   - Job {job.id}: {job.status} (Accuracy: {accuracy})")
            
        except Exception as e:
            print(f"❌ Error fixing training jobs: {e}")
            logger.error(f"Error in fix script: {e}")
            return 1
    
    print("\n✨ Training job fix completed successfully!")
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)