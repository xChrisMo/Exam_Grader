#!/usr/bin/env python3
"""Data Cleanup Utility for Exam Grader Application.

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
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv("instance/.env", override=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)


def check_data_status():
    """Check current data status."""
    try:
        logging.info("📊 CHECKING DATA STATUS...")
        logging.info("=" * 50)
        
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
            
            logging.info(f"👥 Users: {user_count}")
            logging.info(f"📋 Marking Guides: {guide_count}")
            logging.info(f"📄 Submissions: {submission_count}")
            logging.info(f"🔗 Mappings: {mapping_count}")
            logging.info(f"📊 Grading Results: {result_count}")
            logging.info(f"🔐 Sessions: {session_count}")
            
            # Check file directories
            temp_files = count_files_in_directory("temp")
            output_files = count_files_in_directory("output")
            upload_files = count_files_in_directory("uploads")
            
            logging.info(f"\n📁 FILE DIRECTORIES:")
            logging.info(f"   temp/: {temp_files} files")
            logging.info(f"   output/: {output_files} files")
            logging.info(f"   uploads/: {upload_files} files")
            
            # Calculate total data to be cleaned
            total_data_records = guide_count + submission_count + mapping_count + result_count + session_count
            total_files = temp_files + output_files + upload_files
            
            logging.info(f"\n🧹 DATA TO BE CLEANED:")
            logging.info(f"   Database records: {total_data_records}")
            logging.info(f"   Files: {total_files}")
            logging.info(f"   Users preserved: {user_count}")
            
        return True
        
    except Exception as e:
        logging.error(f"❌ Error checking data status: {str(e)}")
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
        logging.info("🗄️  CLEANING DATABASE DATA...")

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

            logging.info(f"   Deleting {result_count} grading results...")
            GradingResult.query.delete()

            logging.info(f"   Deleting {mapping_count} mappings...")
            Mapping.query.delete()

            logging.info(f"   Deleting {submission_count} submissions...")
            Submission.query.delete()

            logging.info(f"   Deleting {guide_count} marking guides...")
            MarkingGuide.query.delete()

            logging.info(f"   Deleting {session_count} sessions...")
            Session.query.delete()

            # Commit all deletions
            db.session.commit()

            logging.info("✅ Database data cleaned successfully")
            return True

    except Exception as e:
        logging.error(f"❌ Error cleaning database: {str(e)}")
        return False


def cleanup_session_data():
    """Clean up session data by clearing Flask sessions."""
    try:
        logging.info("🔐 CLEANING SESSION DATA...")

        from flask import Flask
        from src.config.unified_config import config
        from src.database import db, Session as SessionModel

        app = Flask(__name__)
        app.config.update(config.get_flask_config())
        db.init_app(app)

        with app.app_context():
            # Clear all session records (this will force users to re-login)
            session_count = SessionModel.query.count()
            logging.info(f"   Clearing {session_count} active sessions...")
            SessionModel.query.delete()
            db.session.commit()

            logging.info("✅ Session data cleaned successfully")
            logging.info("   Note: Users will need to log in again")
            return True

    except Exception as e:
        logging.error(f"❌ Error cleaning session data: {str(e)}")
        return False


def cleanup_file_directories():
    """Clean up file directories."""
    try:
        logging.info("📁 CLEANING FILE DIRECTORIES...")
        
        directories = ["temp", "output", "uploads"]
        
        for directory in directories:
            path = Path(directory)
            if path.exists():
                file_count = count_files_in_directory(directory)
                logging.info(f"   Cleaning {directory}/: {file_count} files...")
                
                # Remove all contents but keep the directory
                for item in path.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                
                logging.info(f"   ✅ {directory}/ cleaned")
            else:
                logging.info(f"   ℹ️  {directory}/ doesn't exist")
                # Create the directory
                path.mkdir(exist_ok=True)
                logging.info(f"   ✅ {directory}/ created")
        
        logging.info("✅ File directories cleaned successfully")
        return True
        
    except Exception as e:
        logging.error(f"❌ Error cleaning file directories: {str(e)}")
        return False


def cleanup_data(confirm: bool = False):
    """Clean up all application data except users."""
    
    if not confirm:
        logging.warning("⚠️  WARNING: This will delete all application data except user accounts!")
        logging.info("   The following will be removed:")
        logging.info("   • All marking guides and their files")
        logging.info("   • All submissions and their files")
        logging.info("   • All mappings and grading results")
        logging.info("   • All session data (users will need to log in again)")
        logging.info("   • All files in temp/, output/, and uploads/ directories")
        logging.info("\n   User accounts will be preserved.")
        response = input("\n   Are you sure you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            logging.info("Data cleanup cancelled.")
            return False
    
    try:
        logging.info("\n🧹 STARTING DATA CLEANUP...")
        logging.info("=" * 50)
        
        # Check current status
        if not check_data_status():
            return False
        
        logging.info("\n" + "=" * 50)
        
        # Clean database data
        if not cleanup_database_data():
            return False

        # Clean session data
        if not cleanup_session_data():
            return False

        # Clean file directories
        if not cleanup_file_directories():
            return False
        
        logging.info("\n🎉 DATA CLEANUP COMPLETED SUCCESSFULLY!")
        logging.info("\n" + "=" * 60)
        logging.info("DATA CLEANUP COMPLETE")
        logging.info("=" * 60)
        logging.info("All application data has been cleaned except user accounts.")
        logging.info("The application is ready for fresh data.")
        logging.info("You can continue using the application with existing user accounts.")
        logging.info("=" * 60)
        
        return True
        
    except Exception as e:
        logging.error(f"❌ Error during cleanup: {str(e)}")
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
    
    logging.info("🧹 EXAM GRADER DATA CLEANUP UTILITY")
    logging.info("=" * 40)
    
    if args.status:
        success = check_data_status()
        sys.exit(0 if success else 1)
    else:
        success = cleanup_data(args.confirm)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
