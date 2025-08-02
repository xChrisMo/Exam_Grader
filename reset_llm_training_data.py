#!/usr/bin/env python3
"""
Reset LLM Training Data - Remove all LLM training related data from database
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def reset_llm_training_data():
    """Remove all LLM training related data from the database"""
    print("🗑️  Resetting LLM Training Data...")
    
    try:
        from webapp.app import app
        from src.database.models import db, LLMDocument, LLMDataset, LLMDatasetDocument, LLMTrainingJob, LLMTrainingReport, LLMModelTest, LLMTestSubmission
        
        with app.app_context():
            print("📊 Checking current data...")
            
            # Count existing records
            documents_count = LLMDocument.query.count()
            datasets_count = LLMDataset.query.count()
            jobs_count = LLMTrainingJob.query.count()
            reports_count = LLMTrainingReport.query.count()
            tests_count = LLMModelTest.query.count()
            test_submissions_count = LLMTestSubmission.query.count()
            dataset_docs_count = LLMDatasetDocument.query.count()
            
            print(f"📋 Current LLM Training Data:")
            print(f"   - Documents: {documents_count}")
            print(f"   - Datasets: {datasets_count}")
            print(f"   - Training Jobs: {jobs_count}")
            print(f"   - Reports: {reports_count}")
            print(f"   - Model Tests: {tests_count}")
            print(f"   - Test Submissions: {test_submissions_count}")
            print(f"   - Dataset-Document Links: {dataset_docs_count}")
            
            total_records = documents_count + datasets_count + jobs_count + reports_count + tests_count + test_submissions_count + dataset_docs_count
            
            if total_records == 0:
                print("✅ No LLM training data found - database is already clean")
                return True
            
            print(f"\n🗑️  Removing {total_records} total records...")
            
            # Delete in correct order to avoid foreign key constraints
            print("   Deleting test submissions...")
            LLMTestSubmission.query.delete()
            
            print("   Deleting model tests...")
            LLMModelTest.query.delete()
            
            print("   Deleting training reports...")
            LLMTrainingReport.query.delete()
            
            print("   Deleting training jobs...")
            LLMTrainingJob.query.delete()
            
            print("   Deleting dataset-document links...")
            LLMDatasetDocument.query.delete()
            
            print("   Deleting datasets...")
            LLMDataset.query.delete()
            
            print("   Deleting documents...")
            LLMDocument.query.delete()
            
            # Commit all deletions
            db.session.commit()
            
            # Verify deletion
            print("\n📊 Verifying deletion...")
            documents_after = LLMDocument.query.count()
            datasets_after = LLMDataset.query.count()
            jobs_after = LLMTrainingJob.query.count()
            reports_after = LLMTrainingReport.query.count()
            tests_after = LLMModelTest.query.count()
            test_submissions_after = LLMTestSubmission.query.count()
            dataset_docs_after = LLMDatasetDocument.query.count()
            
            total_after = documents_after + datasets_after + jobs_after + reports_after + tests_after + test_submissions_after + dataset_docs_after
            
            if total_after == 0:
                print("✅ All LLM training data successfully removed from database")
                return True
            else:
                print(f"⚠️  Warning: {total_after} records still remain")
                return False
                
    except Exception as e:
        print(f"❌ Error resetting LLM training data: {e}")
        import traceback
        traceback.print_exc()
        return False

def clean_upload_directories():
    """Clean up uploaded files in the upload directories"""
    print("\n🗂️  Cleaning Upload Directories...")
    
    upload_dirs = [
        'uploads/training_guides',
        'uploads/test_submissions',
        'uploads/llm_training'
    ]
    
    total_files_removed = 0
    
    for upload_dir in upload_dirs:
        dir_path = project_root / upload_dir
        
        if dir_path.exists():
            files = list(dir_path.glob('*'))
            files_count = len([f for f in files if f.is_file()])
            
            if files_count > 0:
                print(f"   Cleaning {upload_dir}: {files_count} files")
                
                for file_path in files:
                    if file_path.is_file():
                        try:
                            file_path.unlink()
                            total_files_removed += 1
                        except Exception as e:
                            print(f"     Warning: Could not delete {file_path.name}: {e}")
            else:
                print(f"   {upload_dir}: already clean")
        else:
            print(f"   {upload_dir}: directory doesn't exist")
    
    if total_files_removed > 0:
        print(f"✅ Removed {total_files_removed} uploaded files")
    else:
        print("✅ No uploaded files to remove")

def reset_cache_and_temp():
    """Clean up cache and temporary files"""
    print("\n🧹 Cleaning Cache and Temporary Files...")
    
    cache_dirs = [
        'cache',
        'temp',
        'logs'
    ]
    
    total_files_removed = 0
    
    for cache_dir in cache_dirs:
        dir_path = project_root / cache_dir
        
        if dir_path.exists():
            files = list(dir_path.glob('*'))
            files_count = len([f for f in files if f.is_file()])
            
            if files_count > 0:
                print(f"   Cleaning {cache_dir}: {files_count} files")
                
                for file_path in files:
                    if file_path.is_file() and not file_path.name.startswith('.git'):
                        try:
                            file_path.unlink()
                            total_files_removed += 1
                        except Exception as e:
                            print(f"     Warning: Could not delete {file_path.name}: {e}")
            else:
                print(f"   {cache_dir}: already clean")
        else:
            print(f"   {cache_dir}: directory doesn't exist")
    
    if total_files_removed > 0:
        print(f"✅ Removed {total_files_removed} cache/temp files")
    else:
        print("✅ No cache/temp files to remove")

def main():
    """Main function"""
    print("🚀 LLM Training Data Reset")
    print("=" * 50)
    print("⚠️  WARNING: This will permanently delete ALL LLM training data!")
    print("   - All training guides")
    print("   - All datasets")
    print("   - All training jobs")
    print("   - All reports")
    print("   - All model tests")
    print("   - All uploaded files")
    print("=" * 50)
    
    # Confirm deletion
    try:
        confirm = input("Are you sure you want to proceed? Type 'YES' to confirm: ")
        if confirm != 'YES':
            print("❌ Operation cancelled")
            return
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        return
    
    print("\n🗑️  Starting data reset...")
    
    # Reset database data
    db_success = reset_llm_training_data()
    
    # Clean upload directories
    clean_upload_directories()
    
    # Clean cache and temp files
    reset_cache_and_temp()
    
    print("\n" + "=" * 50)
    if db_success:
        print("🎉 LLM Training Data Reset Complete!")
        print("\n✅ What was reset:")
        print("- All LLM training database records removed")
        print("- All uploaded training files deleted")
        print("- All cache and temporary files cleared")
        
        print("\n🚀 Ready for fresh data:")
        print("1. Start the application: python run_app.py")
        print("2. Navigate to: http://127.0.0.1:5000/llm-training/")
        print("3. Begin uploading new training guides and submissions")
    else:
        print("⚠️  Data reset completed with some warnings")
        print("Check the messages above for details")

if __name__ == "__main__":
    main()