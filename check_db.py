import sqlite3
import os

# Check the unified database file
db_files = ['exam_grader.db']

for db_path in db_files:
    if os.path.exists(db_path):
        print(f'\n=== {db_path} ===')
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f'Tables: {[t[0] for t in tables]}')
            
            # If we have the expected tables, count records
            expected_tables = ['submissions', 'users', 'marking_guides']
            for table in expected_tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    count = cursor.fetchone()[0]
                    print(f'{table}: {count} records')
                except sqlite3.OperationalError:
                    print(f'{table}: table does not exist')
            
            conn.close()
        except Exception as e:
            print(f'Error: {e}')
    else:
        print(f'{db_path}: file does not exist')