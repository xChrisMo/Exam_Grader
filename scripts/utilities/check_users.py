import sqlite3
import os

def check_users():
    db_path = 'instance/exam_grader.db'
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table schema first
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        print(f"\n=== Users table schema ===")
        for col in columns:
            print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, Default: {col[4]}, PK: {col[5]}")
        
        # Get all users with available columns
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        
        print(f"\n=== Users in {db_path} ===")
        for user in users:
            print(f"User data: {user}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking users: {e}")

if __name__ == "__main__":
    check_users()