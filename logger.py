import datetime
import os
import sys
import requests


class log:
    LOG_LEVELS = {
        "DEBUG": 0,
        "INFO": 1,
        "SUCCESS": 2,
        "ERROR": 3,
        "CRITICAL": 4
    }

    # ANSI escape codes for colors
    COLORS = {
        "DEBUG": "\033[94m",     # Blue
        "INFO": "\033[93m",      # Yellow
        "ERROR": "\033[91m",     # Red
        "CRITICAL": "\033[95m",  # Magenta
        "SUCCESS": "\033[92m",   # Green
        "RESET": "\033[0m",      # Reset color
    }

    def __init__(
        self,
        log_file="app.log",
        log_level="DEBUG",
        debug_webhook=None,
        info_webhook=None,
        error_webhook=None,
        critical_webhook=None,
        success_webhook=None
    ):
        self.log_file = log_file
        self.log_level = log_level
        self.webhooks = {
            "DEBUG": debug_webhook,
            "INFO": info_webhook,
            "ERROR": error_webhook,
            "CRITICAL": critical_webhook,
            'SUCCESS': success_webhook
        }

        # Enable ANSI escape codes for Windows
        if sys.platform == "win32":
            os.system("")

        # Ensure the log file exists
        if not os.path.exists(log_file):
            with open(log_file, 'w') as file:
                file.write("")

    def _log(self, level, message):
        """Internal method to write log messages."""
        if log.LOG_LEVELS[level] >= log.LOG_LEVELS[self.log_level]:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_message = f"{timestamp} - {level} - {message}"
            colored_message = f"{log.COLORS[level]}{formatted_message}{log.COLORS['RESET']}"  # noqa: E501

            # Print to console with color
            print(colored_message)

            # Append to log file without color
            with open(self.log_file, "a") as file:
                file.write(formatted_message + "\n")

            # Send a notification to Discord if a webhook is provided
            webhook_url = self.webhooks.get(level)
            if webhook_url:
                self._send_discord_notification(webhook_url, formatted_message)

    def _send_discord_notification(self, webhook_url, message):
        """Send a notification to a Discord webhook."""
        try:
            payload = {"content": message}
            response = requests.post(webhook_url, json=payload)
            if response.status_code != 204:
                print(f"Failed to send Discord notification: {response.status_code} - {response.text}")  # noqa: E501
        except Exception as e:
            print(f"Error sending Discord notification: {e}")

    def debug(self, message):
        """Log a debug message."""
        self._log("DEBUG", message)

    def info(self, message):
        """Log an info message."""
        self._log("INFO", message)

    def error(self, message):
        """Log an error message."""
        self._log("ERROR", message)

    def critical(self, message):
        """Log a critical message."""
        self._log("CRITICAL", message)

    def success(self, message):
        """Log a success message."""
        self._log("SUCCESS", message)


# Example usage
# log = log(
#     log_level="DEBUG",
#     error_webhook="https://discord.com/api/webhooks/1312960982817050706/r5v3fYRBONjXulTyc0UGslear2PRB9qIcutg8INJsqHI_fPcO31fASwxIWg-AVSHpvBo",
#     critical_webhook="https://discord.com/api/webhooks/1312960874889216083/vKxMcXl2Jx_zVfOn3X4uki90LxQHbenFeDyqgon1zYCkmcdYvx7Tm7Kcfi8es4YRDZrC"
# )

# log.debug("This is a debug message")
# log.info("This is an info message")
# log.error("This is an error message")
# log.critical("This is a critical message")
