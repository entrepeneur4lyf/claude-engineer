from logger import main_logger

class ClaudeEngineerError(Exception):
    """Base exception class for Claude Engineer"""
    pass

def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't log keyboard interrupt exceptions
        return

    main_logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

def log_error(logger, message, exception=None):
    """Log an error message with optional exception details"""
    if exception:
        logger.error(f"{message}: {str(exception)}", exc_info=True)
    else:
        logger.error(message)