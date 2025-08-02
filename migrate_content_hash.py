#!/usr/bin/env python3
"""
Migration script to add content_hash field to existing records.

This script will:
1. Add content_hash column to database tables if not exists
2. Calculate and populate content_hash for existing records
3. Create indexes for performance
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

print("🔄 Starting content hash migration...")

try:
    # Import Flask app and models
    from webapp.app import app
    from src.database.models import db, MarkingGuide, Submission, LLMDocument
    from src.utils.content_deduplication import calculate_content_hash, update_content_hash
    from sqlalchemy import text
    
    with app.app_context():
        print("📊 Checking database schema...")
        
        # Check if content_hash columns exist and add if missing
        inspector = db.inspect(db.engine)
        
        # Check MarkingGuide table
        mg_columns = [col['name'] for col in inspector.get_columns('marking_guides')]
        if 'content_hash' not in mg_columns:
            print("➕ Adding content_hash column to marking_guides table...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE marking_guides ADD COLUMN content_hash VARCHAR(64)'))
                conn.execute(text('CREATE INDEX idx_marking_guides_content_hash ON marking_guides(content_hash)'))
                conn.commit()
        
        # Check Submission table
        sub_columns = [col['name'] for col in inspector.get_columns('submissions')]
        if 'content_hash' not in sub_columns:
            print("➕ Adding content_hash column to submissions table...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE submissions ADD COLUMN content_hash VARCHAR(64)'))
                conn.execute(text('CREATE INDEX idx_submissions_content_hash ON submissions(content_hash)'))
                conn.commit()
        
        # Check LLMDocument table
        llm_columns = [col['name'] for col in inspector.get_columns('llm_documents')]
        if 'content_hash' not in llm_columns:
            print("➕ Adding content_hash column to llm_documents table...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE llm_documents ADD COLUMN content_hash VARCHAR(64)'))
                conn.execute(text('CREATE INDEX idx_llm_documents_content_hash ON llm_documents(content_hash)'))
                conn.commit()
        
        db.session.commit()
        print("✅ Database schema updated successfully")
        
        # Update existing records
        print("🔄 Updating existing records with content hashes...")
        
        # Update MarkingGuides
        guides = MarkingGuide.query.filter(MarkingGuide.content_hash.is_(None)).all()
        print(f"📚 Found {len(guides)} marking guides to update...")
        
        for guide in guides:
            if guide.content_text:
                update_content_hash(guide, guide.content_text)
                print(f"  ✓ Updated guide: {guide.title}")
        
        # Update Submissions
        submissions = Submission.query.filter(Submission.content_hash.is_(None)).all()
        print(f"📝 Found {len(submissions)} submissions to update...")
        
        for submission in submissions:
            if submission.content_text:
                update_content_hash(submission, submission.content_text)
                print(f"  ✓ Updated submission: {submission.filename}")
        
        # Update LLMDocuments
        llm_docs = LLMDocument.query.filter(LLMDocument.content_hash.is_(None)).all()
        print(f"🤖 Found {len(llm_docs)} LLM documents to update...")
        
        for doc in llm_docs:
            if doc.text_content:
                update_content_hash(doc, doc.text_content)
                print(f"  ✓ Updated LLM document: {doc.name}")
        
        # Commit all changes
        db.session.commit()
        print("✅ All records updated successfully")
        
        # Report duplicates found
        print("\n📊 Duplicate Analysis:")
        
        # Check for duplicate marking guides (simplified for SQLite)
        try:
            duplicate_guides_result = db.session.execute(text("""
                SELECT content_hash, COUNT(*) as count
                FROM marking_guides 
                WHERE content_hash IS NOT NULL AND content_hash != ''
                GROUP BY content_hash, user_id
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            if duplicate_guides_result:
                print(f"⚠️  Found {len(duplicate_guides_result)} sets of duplicate marking guides:")
                for dup in duplicate_guides_result:
                    print(f"   - Hash {dup[0][:8]}...: {dup[1]} duplicates")
            else:
                print("✅ No duplicate marking guides found")
        except Exception as e:
            print(f"⚠️  Could not check for duplicate marking guides: {e}")
        
        # Check for duplicate submissions
        try:
            duplicate_submissions_result = db.session.execute(text("""
                SELECT content_hash, COUNT(*) as count
                FROM submissions 
                WHERE content_hash IS NOT NULL AND content_hash != ''
                GROUP BY content_hash, user_id
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            if duplicate_submissions_result:
                print(f"⚠️  Found {len(duplicate_submissions_result)} sets of duplicate submissions:")
                for dup in duplicate_submissions_result:
                    print(f"   - Hash {dup[0][:8]}...: {dup[1]} duplicates")
            else:
                print("✅ No duplicate submissions found")
        except Exception as e:
            print(f"⚠️  Could not check for duplicate submissions: {e}")
        
        # Check for duplicate LLM documents
        try:
            duplicate_llm_docs_result = db.session.execute(text("""
                SELECT content_hash, COUNT(*) as count
                FROM llm_documents 
                WHERE content_hash IS NOT NULL AND content_hash != ''
                GROUP BY content_hash, user_id, type
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            if duplicate_llm_docs_result:
                print(f"⚠️  Found {len(duplicate_llm_docs_result)} sets of duplicate LLM documents:")
                for dup in duplicate_llm_docs_result:
                    print(f"   - Hash {dup[0][:8]}...: {dup[1]} duplicates")
            else:
                print("✅ No duplicate LLM documents found")
        except Exception as e:
            print(f"⚠️  Could not check for duplicate LLM documents: {e}")
        
        print("\n🎉 Content hash migration completed successfully!")
        print("\n📋 Summary:")
        print(f"   - Updated {len(guides)} marking guides")
        print(f"   - Updated {len(submissions)} submissions") 
        print(f"   - Updated {len(llm_docs)} LLM documents")
        print("   - Duplicate analysis completed successfully")
        
except Exception as e:
    print(f"❌ Error during migration: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)