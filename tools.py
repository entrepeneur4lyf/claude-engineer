import os
import logging
from tavily import TavilyClient
from config import TAVILY_API_KEY
from exceptions import FileOperationError, APIError, FileExistsError, DirectoryExistsError
from logger import tools_logger
from error_handler import log_error

tavily = TavilyClient(api_key=TAVILY_API_KEY)

def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder '{path}' has been created successfully."
    except OSError as e:
        raise OSError(f"An error occurred while creating the folder '{path}': {str(e)}")

def create_file(path, content=""):
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"File '{path}' is ready."
    except OSError as e:
        raise OSError(f"An error occurred while creating/updating the file '{path}': {str(e)}")

def write_to_file(path, content):
    try:
        with open(path, 'w') as f:
            f.write(content)
        tools_logger.info(f"Content written to file: {path}")
        return f"Content written to file: {path}"
    except Exception as e:
        log_error(tools_logger, f"Error writing to file: {path}", e)
        raise FileOperationError(f"Error writing to file: {str(e)}")

def read_file(path):
    try:
        with open(path, 'r') as f:
            content = f.read()
        tools_logger.info(f"File read: {path}")
        return content
    except Exception as e:
        log_error(tools_logger, f"Error reading file: {path}", e)
        raise FileOperationError(f"Error reading file: {str(e)}")

def list_files(path="."):
    try:
        files = os.listdir(path)
        tools_logger.info(f"Files listed in: {path}")
        return "\n".join(files)
    except Exception as e:
        log_error(tools_logger, f"Error listing files: {path}", e)
        raise FileOperationError(f"Error listing files: {str(e)}")

def tavily_search(query):
    try:
        response = tavily.qna_search(query=query, search_depth="advanced")
        tools_logger.info(f"Tavily search performed: {query}")
        return response
    except Exception as e:
        log_error(tools_logger, f"Error performing Tavily search: {query}", e)
        raise APIError(f"Error performing Tavily search: {str(e)}")

tools = [
    {
        "name": "create_folder",
        "description": "Create a new folder at the specified path. Use this when you need to create a new directory in the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path where the folder should be created"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "create_file",
        "description": "Create a new file at the specified path with optional content. Use this when you need to create a new file in the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path where the file should be created"
                },
                "content": {
                    "type": "string",
                    "description": "The initial content of the file (optional)"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_to_file",
        "description": "Write content to an existing file at the specified path. Use this when you need to add or update content in an existing file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to write to"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file at the specified path. Use this when you need to examine the contents of an existing file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to read"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_files",
        "description": "List all files and directories in the root folder where the script is running. Use this when you need to see the contents of the current directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the folder to list (default: current directory)"
                }
            }
        }
    },
    {
        "name": "tavily_search",
        "description": "Perform a web search using Tavily API to get up-to-date information or additional context. Use this when you need current information or feel a search could provide a better answer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    }
]

def execute_tool(tool_name, tool_input):
    tools_logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
    if tool_name == "create_folder":
        return create_folder(tool_input["path"])
    elif tool_name == "create_file":
        return create_file(tool_input["path"], tool_input.get("content", ""))
    elif tool_name == "write_to_file":
        return write_to_file(tool_input["path"], tool_input.get("content", ""))
    elif tool_name == "read_file":
        return read_file(tool_input["path"])
    elif tool_name == "list_files":
        return list_files(tool_input.get("path", "."))
    elif tool_name == "tavily_search":
        return tavily_search(tool_input["query"])
    else:
        error_message = f"Unknown tool: {tool_name}"
        tools_logger.error(error_message)
        raise ValueError(error_message)
