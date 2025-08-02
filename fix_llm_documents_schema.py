#!/usr/bin/env python3
"""
Fix LLM Documents table schema by adding missing columns
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_llm_documents_schema():
    """Add missing columns to llm_documents table"""
    print("🔧 Fixing LLM Documents Schema...")
    
    try:
        from webapp.app import app
        from src.database.models import db
        from sqlalchemy import text, inspect
        
        with app.app_context():
            # Check current table structure
            inspector = inspect(db.engine)
            
            if 'llm_documents' not in inspector.get_table_names():
                print("❌ llm_documents table does not exist")
                return False
            
            columns = [col['name'] for col in inspector.get_columns('llm_documents')]
            print(f"📋 Current columns: {columns}")
            
            # Define missing columns that need to be added
            missing_columns = []
            
            required_columns = {
                'document_metadata': 'TEXT',
                'validation_status': "VARCHAR(50) DEFAULT 'pending'",
                'validation_errors': 'TEXT',
                'processing_retries': 'INTEGER DEFAULT 0',
                'content_quality_score': 'REAL',
                'extraction_method': 'VARCHAR(50)',
                'processing_duration_ms': 'INTEGER'
            }
            
            for col_name, col_def in required_columns.items():
                if col_name not in columns:
                    missing_columns.append((col_name, col_def))
            
            if not missing_columns:
                print("✅ All required columns already exist")
                return True
            
            print(f"📝 Adding {len(missing_columns)} missing columns...")
            
            # Add missing columns
            for col_name, col_def in missing_columns:
                try:
                    sql = f"ALTER TABLE llm_documents ADD COLUMN {col_name} {col_def}"
                    print(f"   Adding: {col_name}")
                    db.session.execute(text(sql))
                    db.session.commit()
                except Exception as e:
                    print(f"   ⚠️  Warning adding {col_name}: {e}")
                    db.session.rollback()
            
            # Verify columns were added
            columns_after = [col['name'] for col in inspector.get_columns('llm_documents')]
            print(f"📋 Columns after fix: {columns_after}")
            
            # Check if all required columns are now present
            all_present = all(col in columns_after for col in required_columns.keys())
            
            if all_present:
                print("✅ All required columns are now present")
                return True
            else:
                missing_after = [col for col in required_columns.keys() if col not in columns_after]
                print(f"❌ Still missing columns: {missing_after}")
                return False
                
    except Exception as e:
        print(f"❌ Error fixing schema: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_query():
    """Test if we can now query the database without errors"""
    print("\n🧪 Testing Database Query...")
    
    try:
        from webapp.app import app
        from src.database.models import db, LLMDocument
        
        with app.app_context():
            # Try to query the table
            count = LLMDocument.query.count()
            print(f"✅ Query successful: {count} documents in database")
            
            # Try to query with type filter
            guides = LLMDocument.query.filter_by(type='training_guide').count()
            submissions = LLMDocument.query.filter_by(type='test_submission').count()
            print(f"✅ Type queries successful: {guides} guides, {submissions} submissions")
            
            return True
            
    except Exception as e:
        print(f"❌ Database query test failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 LLM Documents Schema Fix")
    print("=" * 40)
    
    # Fix the schema
    schema_fixed = fix_llm_documents_schema()
    
    if schema_fixed:
        # Test queries
        query_works = test_database_query()
        
        print("\n" + "=" * 40)
        if query_works:
            print("🎉 Schema fix completed successfully!")
            print("\n✅ What was fixed:")
            print("- Added missing columns to llm_documents table")
            print("- Verified all required columns are present")
            print("- Tested database queries work properly")
            
            print("\n🚀 Next steps:")
            print("1. The LLM training page should now work without errors")
            print("2. Upload functionality should be fully operational")
            print("3. All API endpoints should return proper responses")
        else:
            print("⚠️ Schema was fixed but queries still have issues")
    else:
        print("❌ Failed to fix database schema")

if __name__ == "__main__":
    main()