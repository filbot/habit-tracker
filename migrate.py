import json
import os
import database

STATS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "stats.json")

def migrate():
    if not os.path.exists(STATS_FILE):
        print("No stats.json found. Skipping migration.")
        return

    print("Found stats.json. initializing database...")
    database.init_db()

    try:
        with open(STATS_FILE, 'r') as f:
            data = json.load(f)
        
        history = data.get('history', [])
        offset = data.get('offset', 0)
        
        # Handle old format if present
        if 'count' in data and 'history' not in data:
            offset = data['count']
            history = []

        print(f"Migrating {len(history)} logs and offset {offset}...")
        
        # Migrate Offset
        database.set_offset(offset)
        
        # Migrate History
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        # Check if data already exists to avoid duplicates if run multiple times
        cursor.execute('SELECT COUNT(*) FROM logs')
        count = cursor.fetchone()[0]
        
        if count == 0:
            for timestamp in history:
                cursor.execute('INSERT INTO logs (timestamp) VALUES (?)', (timestamp,))
            conn.commit()
            print("Migration complete.")
        else:
            print("Database not empty. Skipping history migration to avoid duplicates.")
            
        conn.close()
        
        # Rename stats.json to stats.json.bak
        os.rename(STATS_FILE, STATS_FILE + ".bak")
        print("Renamed stats.json to stats.json.bak")

    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
