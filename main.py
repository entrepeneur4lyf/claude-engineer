import logging
import signal
import os
import time
import sys
from colorama import init, Style
from config import USER_COLOR, CLAUDE_COLOR, TOOL_COLOR, MAX_CONTINUATION_ITERATIONS, CONTINUATION_EXIT_PHRASE, DATABASE_NAME
from utils import print_colored, parse_goals, process_and_display_response, safe_input, GracefulExit, save_state, load_state
from chat import chat_with_claude, execute_goals
from exceptions import ClaudeEngineerException, APILimitError, APIError
from logger import main_logger
from error_handler import handle_exception, log_error
from database import init_db, save_conversation, load_conversation, list_conversations
from preferences import load_preferences, update_preference
from api_limiter import api_limiter

# Set the global exception handler
sys.excepthook = handle_exception

# Initialize colorama
init()

# Global flag to indicate if the program should exit
should_exit = False

def signal_handler(sig, frame):
    global should_exit
    should_exit = True

def main():
    global should_exit
    automode = False

    logging.debug("Starting main function")
    main_logger.info(f"Starting Claude Engineer application with database: {DATABASE_NAME}")

    # Initialize the database
    init_db()

    # Load user preferences
    preferences = load_preferences()

    print_colored("Welcome to the Claude-3.5-Sonnet Engineer Chat with Image Support!", CLAUDE_COLOR)
    print_colored("Type 'exit' to end the conversation.", CLAUDE_COLOR)
    print_colored("Type 'image' to include an image in your message.", CLAUDE_COLOR)
    print_colored("Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.", CLAUDE_COLOR)
    print_colored("Type 'save' to save the current conversation.", CLAUDE_COLOR)
    print_colored("Type 'load [id]' to load a previous conversation.", CLAUDE_COLOR)
    print_colored("Type 'list' to see all saved conversations.", CLAUDE_COLOR)
    print_colored("Type 'preferences' to view or update your preferences.", CLAUDE_COLOR)
    print_colored("Press Ctrl+C at any time to exit gracefully.", CLAUDE_COLOR)
    
    # Set up the signal handler for CTRL+C
    signal.signal(signal.SIGINT, signal_handler)
    
    saved_state = load_state()
    if saved_state:
        print_colored("A saved state was found. Would you like to resume from the saved state? (yes/no)", TOOL_COLOR)
        if safe_input().lower() == 'yes':
            conversation_history = saved_state["conversation_history"]
            automode = saved_state["automode"]
            iteration_count = saved_state["iteration_count"]
            max_iterations = saved_state["max_iterations"]
            print_colored("State loaded successfully.", TOOL_COLOR)
        else:
            conversation_history = []
    else:
        conversation_history = []
    
    try:
        while not should_exit:
            try:
                user_input = safe_input(f"\n{USER_COLOR}You: {Style.RESET_ALL}")
                
                if user_input.lower() == 'exit' or should_exit:
                    break
                
                if user_input is None:
                    time.sleep(0.1)  # Short sleep to prevent CPU hogging
                    continue
                
                if user_input.lower() == 'save':
                    conversation_id = save_conversation(conversation_history)
                    if conversation_id:
                        print_colored(f"Conversation saved with ID: {conversation_id}", TOOL_COLOR)
                    else:
                        print_colored("Failed to save conversation", TOOL_COLOR)
                    continue
                
                if user_input.lower().startswith('load '):
                    conversation_id = int(user_input.split()[1])
                    loaded_conversation = load_conversation(conversation_id)
                    if loaded_conversation:
                        conversation_history = loaded_conversation
                        print_colored(f"Conversation {conversation_id} loaded", TOOL_COLOR)
                    else:
                        print_colored(f"Failed to load conversation {conversation_id}", TOOL_COLOR)
                    continue
                
                if user_input.lower() == 'list':
                    conversations = list_conversations()
                    for conv in conversations:
                        print_colored(f"ID: {conv[0]}, Timestamp: {conv[1]}", TOOL_COLOR)
                    continue
                
                if user_input.lower() == 'preferences':
                    print_colored("Current preferences:", TOOL_COLOR)
                    for key, value in preferences.items():
                        print_colored(f"{key}: {value}", TOOL_COLOR)
                    update_key = safe_input("Enter preference key to update (or press Enter to skip): ")
                    if update_key:
                        update_value = safe_input(f"Enter new value for {update_key}: ")
                        update_preference(update_key, update_value)
                        preferences = load_preferences()
                    continue
                
                try:
                    if user_input.lower() == 'image':
                        image_path = safe_input(f"{USER_COLOR}Drag and drop your image here: {Style.RESET_ALL}")
                        if image_path is None:
                            continue
                        image_path = image_path.strip().replace("'", "")
                        
                        if not os.path.isfile(image_path):
                            raise ClaudeEngineerException("Invalid image path. Please try again.")
                        
                        user_input = safe_input(f"{USER_COLOR}You (prompt for image): {Style.RESET_ALL}")
                        if user_input is None:
                            continue
                        if not should_exit:
                            logging.debug("About to call chat_with_claude with image")
                            response, _ = chat_with_claude(user_input, image_path, conversation_history=conversation_history, preferences=preferences)
                            logging.debug("chat_with_claude call with image completed")
                            process_and_display_response(response, file_path=None)
                            conversation_history.append({"role": "user", "content": user_input})
                            conversation_history.append({"role": "assistant", "content": response})
                    elif user_input.lower().startswith('automode'):
                        parts = user_input.split()
                        max_iterations = MAX_CONTINUATION_ITERATIONS
                        if len(parts) > 1:
                            try:
                                max_iterations = int(parts[1])
                            except ValueError:
                                raise ClaudeEngineerException("Invalid number of iterations. Using default value.")
                        
                        automode = True
                        print_colored(f"Entering automode with {max_iterations} iterations. Press Ctrl+C to exit automode at any time.", TOOL_COLOR)
                        user_input = safe_input(f"\n{USER_COLOR}You: {Style.RESET_ALL}")
                        if user_input is None:
                            continue
                        
                        iteration_count = 0
                        while automode and iteration_count < max_iterations and not should_exit:
                            logging.debug(f"Automode iteration {iteration_count + 1}")
                            response, exit_continuation = chat_with_claude(user_input, current_iteration=iteration_count+1, max_iterations=max_iterations, conversation_history=conversation_history, preferences=preferences)
                            process_and_display_response(response, file_path=None)
                            conversation_history.append({"role": "user", "content": user_input})
                            conversation_history.append({"role": "assistant", "content": response})
                            
                            if exit_continuation or CONTINUATION_EXIT_PHRASE in response or should_exit:
                                print_colored("Automode completed or interrupted.", TOOL_COLOR)
                                automode = False
                            else:
                                print_colored(f"Continuation iteration {iteration_count + 1} completed.", TOOL_COLOR)
                                user_input = "Continue with the next step."
                            
                            iteration_count += 1
                            
                            if iteration_count >= max_iterations:
                                print_colored("Max iterations reached. Exiting automode.", TOOL_COLOR)
                                automode = False
                        
                        print_colored("Exited automode. Returning to regular chat.", TOOL_COLOR)
                    else:
                        if not should_exit:
                            logging.debug("About to call chat_with_claude")
                            response, _ = chat_with_claude(user_input, conversation_history=conversation_history, preferences=preferences)
                            logging.debug("chat_with_claude call completed")
                            process_and_display_response(response, file_path=None)
                            conversation_history.append({"role": "user", "content": user_input})
                            conversation_history.append({"role": "assistant", "content": response})
                
                except APILimitError as e:
                    log_error(main_logger, "API Limit Reached", e)
                    print_colored(f"API limit reached: {str(e)}", TOOL_COLOR)
                    print_colored("Would you like to save the current state and exit? (yes/no)", TOOL_COLOR)
                    if safe_input().lower() == 'yes':
                        save_state(conversation_history, automode, iteration_count, max_iterations)
                        print_colored("State saved. You can resume later by loading this state.", TOOL_COLOR)
                        should_exit = True
                    else:
                        print_colored("Continuing in limited mode. Some features may be unavailable.", TOOL_COLOR)
                    continue

                except APIError as e:
                    log_error(main_logger, "API Error", e)
                    print_colored(f"An API error occurred: {str(e)}", TOOL_COLOR)
                    continue

                except ClaudeEngineerException as e:
                    log_error(main_logger, "Claude Engineer Exception", e)
                    print_colored(f"Error: {str(e)}", TOOL_COLOR)
                except Exception as e:
                    log_error(main_logger, "Unexpected error", e)
                    print_colored(f"An unexpected error occurred: {str(e)}", TOOL_COLOR)
                
                if should_exit:
                    break
            
            except GracefulExit:
                break
            except KeyboardInterrupt:
                break
            except ClaudeEngineerException as e:
                log_error(main_logger, "Claude Engineer Exception", e)
                print_colored(f"Error: {str(e)}", TOOL_COLOR)
            except Exception as e:
                log_error(main_logger, "Unexpected error", e)
                print_colored(f"An unexpected error occurred: {str(e)}", TOOL_COLOR)
    
    finally:
        if preferences.get("auto_save", True):
            save_conversation(conversation_history)
            print_colored("Conversation auto-saved.", TOOL_COLOR)
        main_logger.info("Shutting down Claude Engineer application")
        print_colored("Thank you for using Claude Engineer. Goodbye!", CLAUDE_COLOR)
        sys.exit(0)

if __name__ == "__main__":
    main()