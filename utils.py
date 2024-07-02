import sys
import select
from colorama import Style
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import TerminalFormatter
import pygments.util
from PIL import Image
import os
import io
import base64
import re
import json
from config import CLAUDE_COLOR
from exceptions import ImageProcessingError, FileOperationError
from logger import utils_logger
from error_handler import log_error

class GracefulExit(Exception):
    pass

def print_colored(text, color):
    print(f"{color}{text}{Style.RESET_ALL}")

def print_code(code, language):
    try:
        lexer = get_lexer_by_name(language, stripall=True)
        formatted_code = highlight(code, lexer, TerminalFormatter())
        print(formatted_code)
    except pygments.util.ClassNotFound:
        print_colored(f"Code (language: {language}):\n{code}", CLAUDE_COLOR)

def encode_image_to_base64(image_path):
    try:
        with Image.open(image_path) as img:
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.DEFAULT_STRATEGY)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            utils_logger.info(f"Image encoded successfully: {image_path}")
            return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    except Exception as e:
        log_error(utils_logger, f"Error encoding image: {image_path}", e)
        raise ImageProcessingError(f"Error encoding image: {str(e)}")

def parse_goals(response):
    goals = re.findall(r'Goal \d+: (.+)', response)
    utils_logger.info(f"Parsed goals: {goals}")
    return goals

def process_and_display_response(code, file_path=None):
    is_complete, problematic_lines = check_for_incomplete_code(code)
    
    if file_path:
        print(f"Code for {file_path}:")
    print(code)
    
    if not is_complete:
        print("\nWarning: The code appears to be incomplete.")
        print("Problematic lines:")
        for line in problematic_lines:
            print(f"- {line.strip()}")
    
    return is_complete

def check_for_incomplete_code(code):
    lines = code.split('\n')
    placeholder_patterns = [
        '...', 'TODO', 'FIXME', '# Implement', '# Add', '# Fill in',
        '# Complete', '# Write', '# Define', '# Insert', '# Replace',
        '# [', '# ]', '# {', '# }', '# <', '# >', '# Your code here',
        '# Additional code', '# Rest of the', '# Remaining',
        '# (rest of function)', '# (rest of method)', '# (rest of class)',
        '// ... (keep all existing code)'
    ]
    problematic_lines = [
        line for line in lines 
        if any(pattern in line for pattern in placeholder_patterns)
    ]
    is_complete = len(problematic_lines) == 0
    return is_complete, problematic_lines

def safe_input(prompt):
    if not prompt:
        utils_logger.error("Empty prompt detected")
        print("\nEmpty prompt detected. Exiting.")
        raise GracefulExit()
    try:
        return input(prompt)
    except EOFError:
        utils_logger.error("EOF detected")
        print("\nEOF detected. Exiting.")
        raise GracefulExit()
    except KeyboardInterrupt:
        utils_logger.error("Keyboard interrupt detected")
        print("\nKeyboard interrupt detected. Exiting.")
        raise GracefulExit()

def validate_file_path(path):
    if not os.path.exists(path):
        error_message = f"The file or directory does not exist: {path}"
        utils_logger.error(error_message)
        raise FileNotFoundError(error_message)
    if os.path.isdir(path):
        error_message = f"The path is a directory, not a file: {path}"
        utils_logger.error(error_message)
        raise IsADirectoryError(error_message)
    return path

def safe_file_read(path):
    try:
        with open(path, 'r') as file:
            content = file.read()
        utils_logger.info(f"File read successfully: {path}")
        return content
    except IOError as e:
        log_error(utils_logger, f"Error reading file {path}", e)
        raise FileOperationError(f"Error reading file {path}: {str(e)}")

def safe_file_write(path, content):
    try:
        with open(path, 'w') as file:
            file.write(content)
        utils_logger.info(f"File written successfully: {path}")
    except IOError as e:
        log_error(utils_logger, f"Error writing to file {path}", e)
        raise FileOperationError(f"Error writing to file {path}: {str(e)}")

def truncate_string(string, max_length=100):
    return (string[:max_length] + '...') if len(string) > max_length else string

def retry_operation(operation, max_retries=3, delay=1):
    import time
    retries = 0
    while retries < max_retries:
        try:
            return operation()
        except Exception as e:
            retries += 1
            if retries == max_retries:
                raise
            time.sleep(delay)
    utils_logger.warning(f"Operation failed after {max_retries} retries")

def is_valid_json(json_string):
    import json
    try:
        json.loads(json_string)
        return True
    except json.JSONDecodeError:
        return False

def sanitize_filename(filename):
    import re
    return re.sub(r'[^\w\-_\. ]', '_', filename)

def get_file_extension(filename):
    import os
    return os.path.splitext(filename)[1]

def is_image_file(filename):
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    return get_file_extension(filename).lower() in valid_extensions

def format_time(seconds):
    import datetime
    return str(datetime.timedelta(seconds=int(seconds)))

def save_state(conversation_history, automode, iteration_count, max_iterations):
    state = {
        "conversation_history": conversation_history,
        "automode": automode,
        "iteration_count": iteration_count,
        "max_iterations": max_iterations
    }
    try:
        with open("saved_state.json", "w") as f:
            json.dump(state, f)
        utils_logger.info("State saved successfully")
    except Exception as e:
        log_error(utils_logger, "Error saving state", e)
        raise FileOperationError(f"Error saving state: {str(e)}")

def load_state():
    try:
        with open("saved_state.json", "r") as f:
            state = json.load(f)
        utils_logger.info("State loaded successfully")
        return state
    except FileNotFoundError:
        utils_logger.info("No saved state found")
        return None
    except Exception as e:
        log_error(utils_logger, "Error loading state", e)
        raise FileOperationError(f"Error loading state: {str(e)}")

def load_preferences():
    try:
        with open('preferences.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "model": "claude-3-5-sonnet-20240620",
            "max_tokens": 4000,
            "temperature": 0.7
        }