import sqlite3
import json
from logger import db_logger
from error_handler import log_error
from config import DATABASE_NAME

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conversations
                 (id INTEGER PRIMARY KEY, 
                 timestamp TEXT, 
                 conversation TEXT)''')
    conn.commit()
    conn.close()
    db_logger.info("Database initialized")

def save_conversation(conversation_history):
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO conversations (timestamp, conversation) VALUES (datetime('now'), ?)",
                  (json.dumps(conversation_history),))
        conn.commit()
        conversation_id = c.lastrowid
        conn.close()
        db_logger.info(f"Conversation saved with ID: {conversation_id}")
        return conversation_id
    except Exception as e:
        log_error(db_logger, "Error saving conversation", e)
        return None

def load_conversation(conversation_id):
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        c = conn.cursor()
        c.execute("SELECT conversation FROM conversations WHERE id = ?", (conversation_id,))
        result = c.fetchone()
        conn.close()
        if result:
            db_logger.info(f"Conversation loaded: ID {conversation_id}")
            return json.loads(result[0])
        else:
            db_logger.warning(f"No conversation found with ID: {conversation_id}")
            return None
    except Exception as e:
        log_error(db_logger, f"Error loading conversation: ID {conversation_id}", e)
        return None

def list_conversations():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        c = conn.cursor()
        c.execute("SELECT id, timestamp FROM conversations ORDER BY timestamp DESC")
        conversations = c.fetchall()
        conn.close()
        db_logger.info("Conversation list retrieved")
        return conversations
    except Exception as e:
        log_error(db_logger, "Error listing conversations", e)
        return []