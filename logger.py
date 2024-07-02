import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Generate a timestamp for this session
SESSION_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup as many loggers as you want"""
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    
    # Include the session timestamp in the log file name
    log_file_with_timestamp = f"logs/{name}_{SESSION_TIMESTAMP}.log"
    
    handler = RotatingFileHandler(log_file_with_timestamp, maxBytes=1024*1024, backupCount=5)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Setup loggers
main_logger = setup_logger('main', 'main')
chat_logger = setup_logger('chat', 'chat')
tools_logger = setup_logger('tools', 'tools')
utils_logger = setup_logger('utils', 'utils')
db_logger = setup_logger('db', 'db')
pref_logger = setup_logger('pref', 'pref')
api_logger = setup_logger('api', 'api')

# Log the start of a new session
main_logger.info(f"New session started: {SESSION_TIMESTAMP}")