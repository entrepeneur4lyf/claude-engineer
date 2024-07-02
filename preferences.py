import json
from logger import pref_logger
from error_handler import log_error

PREFERENCES_FILE = 'preferences.json'

def load_preferences():
    try:
        with open(PREFERENCES_FILE, 'r') as f:
            preferences = json.load(f)
        pref_logger.info("Preferences loaded")
        return preferences
    except FileNotFoundError:
        pref_logger.info("Preferences file not found, creating default")
        return create_default_preferences()
    except json.JSONDecodeError as e:
        log_error(pref_logger, "Error decoding preferences file", e)
        return create_default_preferences()

def save_preferences(preferences):
    try:
        with open(PREFERENCES_FILE, 'w') as f:
            json.dump(preferences, f, indent=2)
        pref_logger.info("Preferences saved")
    except Exception as e:
        log_error(pref_logger, "Error saving preferences", e)

def create_default_preferences():
    default_preferences = {
        "max_tokens": 4000,
        "temperature": 0.7,
        "model": "claude-3-5-sonnet-20240620",
        "auto_save": True,
        "theme": "default"
    }
    save_preferences(default_preferences)
    return default_preferences

def update_preference(key, value):
    preferences = load_preferences()
    preferences[key] = value
    save_preferences(preferences)
    pref_logger.info(f"Preference updated: {key} = {value}")