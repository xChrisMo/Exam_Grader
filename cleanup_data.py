#!/usr/bin/env python3
"""
Data Cleanup Utility for Exam Grader Application.

This script cleans up all application data except user accounts:
1. Removes all marking guides and their files
2. Removes all submissions and their files  
3. Removes all mappings and grading results
4. Removes all session data
5. Cleans up temp, output, and upload directories
6. Preserves user accounts and authentication data

Usage:
    python cleanup_data.py
    python cleanup_data.py --confirm
    python cleanup_data.py --status
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv("instance/.env", override=True)


def check_data_status():
    """Check current data status."""
    try:
        print("📊 CHECKING DATA STATUS...")
        print("=" * 50)
        
        # Set up Flask app context
        from flask import Flask
        from src.config.unified_config import config
        from src.database import db, User, MarkingGuide, Submission, Mapping, GradingResult, Session
        
        app = Flask(__name__)
        app.config.update(config.get_flask_config())
        db.init_app(app)
        
        with app.app_context():
            # Count database records
            user_count = User.query.count()
            guide_count = MarkingGuide.query.count()
            submission_count = Submission.query.count()
            mapping_count = Mapping.query.count()
            result_count = GradingResult.query.count()
            session_count = Session.query.count()
            
            print(f"👥 Users: {user_count}")
            print(f"📋 Marking Guides: {guide_count}")
            print(f"📄 Submissions: {submission_count}")
            print(f"🔗 Mappings: {mapping_count}")
            print(f"📊 Grading Results: {result_count}")
            print(f"🔐 Sessions: {session_count}")
            
            # Check file directories
            temp_files = count_files_in_directory("temp")
            output_files = count_files_in_directory("output")
            upload_files = count_files_in_directory("uploads")
            
            print(f"\n📁 FILE DIRECTORIES:")
            print(f"   temp/: {temp_files} files")
            print(f"   output/: {output_files} files")
            print(f"   uploads/: {upload_files} files")
            
            # Calculate total data to be cleaned
            total_data_records = guide_count + submission_count + mapping_count + result_count + session_count
            total_files = temp_files + output_files + upload_files
            
            print(f"\n🧹 DATA TO BE CLEANED:")
            print(f"   Database records: {total_data_records}")
            print(f"   Files: {total_files}")
            print(f"   Users preserved: {user_count}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking data status: {str(e)}")
        return False


def count_files_in_directory(directory_path):
    """Count files in a directory recursively."""
    try:
        path = Path(directory_path)
        if not path.exists():
            return 0
        
        count = 0
        for item in path.rglob("*"):
            if item.is_file():
                count += 1
        return count
    except Exception:
        return 0


def cleanup_database_data():
    """Clean up database data except users."""
    try:
        print("🗄️  CLEANING DATABASE DATA...")

        from flask import Flask
        from src.config.unified_config import config
        from src.database import db, MarkingGuide, Submission, Mapping, GradingResult, Session

        app = Flask(__name__)
        app.config.update(config.get_flask_config())
        db.init_app(app)

        with app.app_context():
            # Count records before deletion
            guide_count = MarkingGuide.query.count()
            submission_count = Submission.query.count()
            mapping_count = Mapping.query.count()
            result_count = GradingResult.query.count()
            session_count = Session.query.count()

            print(f"   Deleting {result_count} grading results...")
            GradingResult.query.delete()

            print(f"   Deleting {mapping_count} mappings...")
            Mapping.query.delete()

            print(f"   Deleting {submission_count} submissions...")
            Submission.query.delete()

            print(f"   Deleting {guide_count} marking guides...")
            MarkingGuide.query.delete()

            print(f"   Deleting {session_count} sessions...")
            Session.query.delete()

            # Commit all deletions
            db.session.commit()

            print("✅ Database data cleaned successfully")
            return True

    except Exception as e:
        print(f"❌ Error cleaning database: {str(e)}")
        return False


def cleanup_session_data():
    """Clean up session data by clearing Flask sessions."""
    try:
        print("🔐 CLEANING SESSION DATA...")

        from flask import Flask
        from src.config.unified_config import config
        from src.database import db, Session as SessionModel

        app = Flask(__name__)
        app.config.update(config.get_flask_config())
        db.init_app(app)

        with app.app_context():
            # Clear all session records (this will force users to re-login)
            session_count = SessionModel.query.count()
            print(f"   Clearing {session_count} active sessions...")
            SessionModel.query.delete()
            db.session.commit()

            print("✅ Session data cleaned successfully")
            print("   Note: Users will need to log in again")
            return True

    except Exception as e:
        print(f"❌ Error cleaning session data: {str(e)}")
        return False


def cleanup_file_directories():
    """Clean up file directories."""
    try:
        print("📁 CLEANING FILE DIRECTORIES...")
        
        directories = ["temp", "output", "uploads"]
        
        for directory in directories:
            path = Path(directory)
            if path.exists():
                file_count = count_files_in_directory(directory)
                print(f"   Cleaning {directory}/: {file_count} files...")
                
                # Remove all contents but keep the directory
                for item in path.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                
                print(f"   ✅ {directory}/ cleaned")
            else:
                print(f"   ℹ️  {directory}/ doesn't exist")
                # Create the directory
                path.mkdir(exist_ok=True)
                print(f"   ✅ {directory}/ created")
        
        print("✅ File directories cleaned successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning file directories: {str(e)}")
        return False


def cleanup_data(confirm: bool = False):
    """Clean up all application data except users."""
    
    if not confirm:
        print("⚠️  WARNING: This will delete all application data except user accounts!")
        print("   The following will be removed:")
        print("   • All marking guides and their files")
        print("   • All submissions and their files")
        print("   • All mappings and grading results")
        print("   • All session data (users will need to log in again)")
        print("   • All files in temp/, output/, and uploads/ directories")
        print("\n   User accounts will be preserved.")
        response = input("\n   Are you sure you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Data cleanup cancelled.")
            return False
    
    try:
        print("\n🧹 STARTING DATA CLEANUP...")
        print("=" * 50)
        
        # Check current status
        if not check_data_status():
            return False
        
        print("\n" + "=" * 50)
        
        # Clean database data
        if not cleanup_database_data():
            return False

        # Clean session data
        if not cleanup_session_data():
            return False

        # Clean file directories
        if not cleanup_file_directories():
            return False
        
        print("\n🎉 DATA CLEANUP COMPLETED SUCCESSFULLY!")
        print("\n" + "=" * 60)
        print("DATA CLEANUP COMPLETE")
        print("=" * 60)
        print("All application data has been cleaned except user accounts.")
        print("The application is ready for fresh data.")
        print("You can continue using the application with existing user accounts.")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean up Exam Grader application data (preserves users)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup_data.py --status      # Check data status
  python cleanup_data.py              # Interactive cleanup
  python cleanup_data.py --confirm    # Cleanup without confirmation
        """
    )
    
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check data status only"
    )
    
    args = parser.parse_args()
    
    print("🧹 EXAM GRADER DATA CLEANUP UTILITY")
    print("=" * 40)
    
    if args.status:
        success = check_data_status()
        sys.exit(0 if success else 1)
    else:
        success = cleanup_data(args.confirm)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
