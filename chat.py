from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, SYSTEM_PROMPT, CONTINUATION_EXIT_PHRASE, CLAUDE_COLOR, TOOL_COLOR, RESULT_COLOR
from tools import execute_tool, tools
from utils import print_colored, encode_image_to_base64, load_preferences, process_and_display_response
from exceptions import APIError, ImageProcessingError, APILimitError, FileExistsError, DirectoryExistsError
from logger import chat_logger, tools_logger, api_logger
from error_handler import log_error
from api_limiter import api_limiter
from dateutil import parser
from datetime import datetime
import time
from tenacity import retry, stop_after_attempt, wait_exponential
import requests
import json

client = Anthropic(api_key=ANTHROPIC_API_KEY)

conversation_history = []
automode = False

def update_system_prompt(current_iteration=None, max_iterations=None):
    global SYSTEM_PROMPT
    automode_status = "You are currently in automode." if automode else "You are not in automode."
    iteration_info = ""
    if current_iteration is not None and max_iterations is not None:
        iteration_info = f"You are currently on iteration {current_iteration} out of {max_iterations} in automode."
    action_encouragement = (
        "When asked to perform a task, take immediate action using the available tools. "
        "Do not apologize or explain your intentions repeatedly. Instead, use the appropriate "
        "tool to create folders, files, or perform other required actions. If you encounter an "
        "error, report it briefly and try an alternative approach. Always aim to make progress "
        "on the task with each response."
    )
    return SYSTEM_PROMPT.format(automode_status=automode_status, iteration_info=iteration_info) + " " + action_encouragement

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_claude_api(client, **kwargs):
    api_logger.info("Calling Claude API")
    try:
        # First, make a call with raw response to get headers
        raw_response = client.messages.with_raw_response.create(**kwargs)
        
        # Check rate limit headers
        requests_remaining = int(raw_response.headers.get('anthropic-ratelimit-requests-remaining', 1))
        tokens_remaining = int(raw_response.headers.get('anthropic-ratelimit-tokens-remaining', 1000))
        reset_time = parser.parse(raw_response.headers.get('anthropic-ratelimit-requests-reset', ''))

        api_logger.info(f"API Usage: Requests remaining: {requests_remaining}, Tokens remaining: {tokens_remaining}, Reset time: {reset_time}")

        if requests_remaining == 0 or tokens_remaining == 0:
            wait_time = (reset_time - datetime.now(reset_time.tzinfo)).total_seconds()
            api_logger.warning(f"Rate limit reached. Waiting for {wait_time} seconds before next request.")
            time.sleep(wait_time)

        # Now, make a regular call to get the full response with tool calls
        response = client.messages.create(**kwargs)

        api_logger.info("Claude API call successful")
        return response
    except Exception as e:
        if 'Rate limit' in str(e):
            api_logger.error(f"Rate limit error in Claude API call: {str(e)}")
            raise APILimitError(f"Rate limit error: {str(e)}")
        api_logger.error(f"Error in Claude API call: {str(e)}")
        raise

def check_api_status():
    try:
        response = requests.get("https://status.anthropic.com")
        return response.status_code == 200
    except:
        return False

def chat_with_claude(user_input, image_path=None, current_iteration=None, max_iterations=None, conversation_history=None, preferences=None):
    global automode
    
    chat_logger.info(f"Starting chat with user input: {user_input}")
    
    if conversation_history is None:
        conversation_history = []
    
    if preferences is None:
        preferences = load_preferences()
    
    estimated_tokens = len(user_input.split()) + 500
    can_make_request, warning_message = api_limiter.can_make_request(estimated_tokens)

    if warning_message:
        print_colored(warning_message, TOOL_COLOR)
        if not can_make_request:
            raise APILimitError(warning_message)
    
    if not check_api_status():
        log_error(chat_logger, "Anthropic API might be experiencing issues")
        raise APIError("Anthropic API might be down or experiencing issues")
    
    if image_path:
        chat_logger.info(f"Processing image at path: {image_path}")
        print_colored(f"Processing image at path: {image_path}", TOOL_COLOR)
        try:
            image_base64 = encode_image_to_base64(image_path)
        except Exception as e:
            log_error(chat_logger, f"Error encoding image: {image_path}", e)
            raise ImageProcessingError(f"Error encoding image: {str(e)}")

        image_message = {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_base64
                    }
                },
                {
                    "type": "text",
                    "text": f"User input for image: {user_input}"
                }
            ]
        }
        conversation_history.append(image_message)
        chat_logger.info("Image message added to conversation history")
        print_colored("Image message added to conversation history", TOOL_COLOR)
    else:
        conversation_history.append({"role": "user", "content": user_input})

    messages = [msg for msg in conversation_history if msg.get('content')]

    try:
        response = call_claude_api(
            client,
            model=preferences.get("model", "claude-3-5-sonnet-20240620"),
            max_tokens=preferences.get("max_tokens", 4000),
            temperature=preferences.get("temperature", 0.7),
            system=update_system_prompt(current_iteration, max_iterations),
            messages=messages,
            tools=tools,
            tool_choice={"type": "auto"}
        )
        chat_logger.info("Received response from Claude API")
    except Exception as e:
        log_error(chat_logger, "Error calling Claude API", e)
        raise APIError(f"Error calling Claude API: {str(e)}")

    assistant_response = ""
    exit_continuation = False

    chat_logger.info("Processing Claude's response")
    for content_block in response.content:
        if content_block.type == "text":
            assistant_response += content_block.text
            print_colored(f"\nClaude: {content_block.text}", CLAUDE_COLOR)
            chat_logger.info(f"Claude text response: {content_block.text[:100]}...")
            if CONTINUATION_EXIT_PHRASE in content_block.text:
                exit_continuation = True
        elif content_block.type == "tool_use":
            tool_name = content_block.name
            tool_input = content_block.input
            tool_use_id = content_block.id
            
            chat_logger.info(f"Tool called: {tool_name}")
            tools_logger.info(f"Tool called: {tool_name} with input: {tool_input}")
            print_colored(f"\nTool Used: {tool_name}", TOOL_COLOR)
            print_colored(f"Tool Input: {tool_input}", TOOL_COLOR)
            
            try:
                result = execute_tool(tool_name, json.loads(tool_input) if isinstance(tool_input, str) else tool_input)
                print_colored(f"Tool Result: {result}", RESULT_COLOR)
                tools_logger.info(f"Tool Result: {result}")
                
                conversation_history.append({"role": "assistant", "content": [content_block]})
                conversation_history.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result
                        }
                    ]
                })
                
                tool_response = call_claude_api(
                    client,
                    model=preferences.get("model", "claude-3-5-sonnet-20240620"),
                    max_tokens=preferences.get("max_tokens", 4000),
                    temperature=preferences.get("temperature", 0.7),
                    system=update_system_prompt(current_iteration, max_iterations),
                    messages=[msg for msg in conversation_history if msg.get('content')],
                    tools=tools,
                    tool_choice={"type": "auto"}
                )
                
                for tool_content_block in tool_response.content:
                    if tool_content_block.type == "text":
                        assistant_response += tool_content_block.text
                        print_colored(f"\nClaude: {tool_content_block.text}", CLAUDE_COLOR)
                        chat_logger.info(f"Claude tool response: {tool_content_block.text[:100]}...")
            
            except Exception as e:
                error_message = f"Error executing tool {tool_name}: {str(e)}"
                log_error(tools_logger, error_message, e)
                log_error(chat_logger, error_message, e)
                assistant_response += f"\nError: {error_message}\n"
                print_colored(f"\nError: {error_message}", TOOL_COLOR)
        else:
            chat_logger.warning(f"Unknown content type in response: {content_block.type}")

    if assistant_response:
        conversation_history.append({"role": "assistant", "content": assistant_response})

    chat_logger.info("Chat completed successfully")
    return assistant_response, exit_continuation

def execute_goals(goals):
    global automode
    for i, goal in enumerate(goals, 1):
        chat_logger.info(f"Executing Goal {i}: {goal}")
        print_colored(f"\nExecuting Goal {i}: {goal}", TOOL_COLOR)
        response, _ = chat_with_claude(f"Continue working on goal: {goal}")
        if CONTINUATION_EXIT_PHRASE in response:
            automode = False
            chat_logger.info("Exiting automode")
            print_colored("Exiting automode.", TOOL_COLOR)
            break