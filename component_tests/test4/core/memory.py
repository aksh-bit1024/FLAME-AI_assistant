import sqlite3
import json
import os

class MemoryManager:
    def __init__(self, db_path="../data/memory.sqlite"):
        """
        Initializes the long-term SQLite storage and sets up memory management.
        """
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Creates the preferences table if it doesn't already exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def set_preference(self, key, value):
        """Saves or updates a long-term preference or setting in SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Convert values to JSON strings so we can store strings, numbers, or lists safely
        cursor.execute('''
            INSERT OR REPLACE INTO preferences (key, value)
            VALUES (?, ?)
        ''', (key, json.dumps(value)))
        conn.commit()
        conn.close()

    def get_preference(self, key, default=None):
        """Retrieves a long-term preference by its key."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM preferences WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return default

    def trim_history(self, history, max_messages=10):
        """
        Manages short-term memory using a sliding window. 
        Keeps the system prompt (index 0) and the most recent N messages 
        to prevent filling up the model's context window.
        """
        if len(history) <= max_messages + 1:
            return history
        
        system_prompt = history[0]
        recent_messages = history[-max_messages:]
        return [system_prompt] + recent_messages