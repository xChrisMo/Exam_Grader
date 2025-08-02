#!/usr/bin/env python3
"""
Fix database schema by adding missing type column to llm_documents table
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_database_schema():
    """Add missing type column to llm_documents table"""
    print("🔧 Fixing Database Schema...")
    
    try:
        from webapp.app import app
        from src.database.models import db
        from sqlalchemy import text, inspect
        
        with app.app_context():
            # Check if type column already exists
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('llm_documents')]
            
            if 'type' in columns:
                print("✅ Type column already exists in llm_documents table")
                return True
            
            print("📝 Adding type column to llm_documents table...")
            
            # Add the type column
            db.session.execute(text("""
                ALTER TABLE llm_documents 
                ADD COLUMN type VARCHAR(50) DEFAULT 'document' NOT NULL
            """))
            
            # Add index for better performance
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_llm_documents_type 
                ON llm_documents(type)
            """))
            
            # Add composite index for user_id and type
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_llm_documents_user_type 
                ON llm_documents(user_id, type)
            """))
            
            db.session.commit()
            
            print("✅ Successfully added type column to llm_documents table")
            print("✅ Added performance indexes")
            
            # Verify the column was added
            columns_after = [col['name'] for col in inspector.get_columns('llm_documents')]
            if 'type' in columns_after:
                print("✅ Verification: Type column is now present")
                return True
            else:
                print("❌ Verification failed: Type column not found")
                return False
                
    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_operations():
    """Test basic database operations after schema fix"""
    print("\n🧪 Testing Database Operations...")
    
    try:
        from webapp.app import app
        from src.database.models import db, LLMDocument
        
        with app.app_context():
            # Test query with type filter
            guides = LLMDocument.query.filter_by(type='training_guide').all()
            submissions = LLMDocument.query.filter_by(type='test_submission').all()
            
            print(f"✅ Query test passed: {len(guides)} training guides, {len(submissions)} test submissions")
            
            # Test creating a document (without actually saving)
            test_doc = LLMDocument(
                user_id='test_user',
                name='Test Document',
                original_name='test.txt',
                stored_name='test_stored.txt',
                file_type='.txt',
                mime_type='text/plain',
                file_size=100,
                file_path='/test/path',
                type='training_guide'
            )
            
            print("✅ Document creation test passed")
            return True
            
    except Exception as e:
        print(f"❌ Database operation test failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Database Schema Fix")
    print("=" * 40)
    
    # Fix the schema
    schema_fixed = fix_database_schema()
    
    if schema_fixed:
        # Test operations
        operations_work = test_database_operations()
        
        print("\n" + "=" * 40)
        if operations_work:
            print("🎉 Database schema fix completed successfully!")
            print("\n✅ What was fixed:")
            print("- Added 'type' column to llm_documents table")
            print("- Added performance indexes")
            print("- Verified database operations work")
            
            print("\n🚀 Next steps:")
            print("1. The upload functionality should now work")
            print("2. Test uploading training guides and submissions")
            print("3. Check the LLM training page for proper functionality")
        else:
            print("⚠️ Schema was fixed but operations still have issues")
    else:
        print("❌ Failed to fix database schema")

if __name__ == "__main__":
    main()