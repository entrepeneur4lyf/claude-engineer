import json
from datetime import datetime, timedelta
from dateutil import parser
from logger import api_logger

class APIDailyLimiter:
    def __init__(self, file_path='api_usage.json'):
        self.file_path = file_path
        self.usage = self.load_usage()
        self.warning_threshold = 0.1  # Warn when 10% of limit remains

    def load_usage(self):
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'date': str(datetime.now().date()),
                'tokens_limit': None,
                'tokens_remaining': None,
                'tokens_reset': None,
                'requests_limit': None,
                'requests_remaining': None,
                'requests_reset': None
            }

    def save_usage(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.usage, f)

    def update_from_headers(self, headers):
        self.usage['tokens_limit'] = int(headers.get('anthropic-ratelimit-tokens-limit', self.usage['tokens_limit']))
        self.usage['tokens_remaining'] = int(headers.get('anthropic-ratelimit-tokens-remaining', self.usage['tokens_remaining']))
        self.usage['tokens_reset'] = headers.get('anthropic-ratelimit-tokens-reset', self.usage['tokens_reset'])
        self.usage['requests_limit'] = int(headers.get('anthropic-ratelimit-requests-limit', self.usage['requests_limit']))
        self.usage['requests_remaining'] = int(headers.get('anthropic-ratelimit-requests-remaining', self.usage['requests_remaining']))
        self.usage['requests_reset'] = headers.get('anthropic-ratelimit-requests-reset', self.usage['requests_reset'])
        self.usage['date'] = str(datetime.now().date())
        self.save_usage()
        self.log_usage()

    def log_usage(self):
        api_logger.info(f"API Usage: Tokens: {self.usage['tokens_remaining']}/{self.usage['tokens_limit']}, "
                        f"Requests: {self.usage['requests_remaining']}/{self.usage['requests_limit']}, "
                        f"Reset: {self.usage['tokens_reset']}")

    def can_make_request(self, estimated_tokens):
        if self.usage['tokens_remaining'] is None or self.usage['requests_remaining'] is None:
            return True, None  # If we don't have information yet, assume we can make the request
        
        if self.usage['tokens_reset'] and parser.parse(self.usage['tokens_reset']) < datetime.now().astimezone(datetime.timezone.utc):
            return True, None  # If the reset time has passed, assume we can make the request
        
        can_make_request = (self.usage['tokens_remaining'] >= estimated_tokens and self.usage['requests_remaining'] > 0)
        warning_message = None

        if not can_make_request:
            reset_time = parser.parse(self.usage['tokens_reset'])
            warning_message = f"API limit reached. Reset time: {reset_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        elif (self.usage['tokens_remaining'] / self.usage['tokens_limit'] < self.warning_threshold or
              self.usage['requests_remaining'] / self.usage['requests_limit'] < self.warning_threshold):
            reset_time = parser.parse(self.usage['tokens_reset'])
            warning_message = (f"Approaching API limit. Tokens remaining: {self.usage['tokens_remaining']}, "
                               f"Requests remaining: {self.usage['requests_remaining']}. "
                               f"Reset time: {reset_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        return can_make_request, warning_message

    def get_remaining_tokens(self):
        return self.usage['tokens_remaining']

    def get_reset_time(self):
        if self.usage['tokens_reset']:
            return parser.parse(self.usage['tokens_reset'])
        return None

api_limiter = APIDailyLimiter()