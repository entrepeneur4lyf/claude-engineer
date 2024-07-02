class ClaudeEngineerException(Exception):
    """Base exception class for Claude Engineer"""
    pass

class APIError(ClaudeEngineerException):
    """Raised when there's an error with API calls"""
    pass

class FileOperationError(ClaudeEngineerException):
    """Raised when there's an error with file operations"""
    pass

class ImageProcessingError(ClaudeEngineerException):
    """Raised when there's an error processing images"""
    pass

class ValidationError(ClaudeEngineerException):
    """Raised when there's an error with input validation"""
    pass

class ConfigurationError(ClaudeEngineerException):
    """Raised when there's an error with the configuration"""
    pass

class APILimitError(ClaudeEngineerException):
    """Raised when the API usage limit is reached"""
    pass

class GracefulExit(Exception):
    """Raised to indicate a graceful exit from the application"""
    pass

class FileExistsError(Exception):
    pass

class DirectoryExistsError(Exception):
    pass
