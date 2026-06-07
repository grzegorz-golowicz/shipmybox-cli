import abc
import json
import os
from pathlib import Path
from typing import Dict, Any, Tuple

import requests

from shipmybox.exceptions import NotificationError

CONFIG_FILE = Path.home() / ".config" / "shipmybox" / "config.json"

class BaseNotifier(abc.ABC):
    @abc.abstractmethod
    def send(self, message: str) -> None:
        """Send a notification message.
        
        Args:
            message: The message body.
        
        Raises:
            NotificationError: If sending the notification fails.
        """
        pass

class PushoverNotifier(BaseNotifier):
    API_URL = "https://api.pushover.net/1/messages.json"
    
    def __init__(self, token: str, user: str):
        if not token:
            raise NotificationError("Pushover token is missing. Please set PUSHOVER_TOKEN environment variable or configure it in config.json")
        if not user:
            raise NotificationError("Pushover user key is missing. Please set PUSHOVER_USER environment variable or configure it in config.json")
        self.token = token
        self.user = user

    def send(self, message: str) -> None:
        data = {
            "token": self.token,
            "user": self.user,
            "message": message,
            "title": "ShipMyBox Monitor"
        }
        try:
            # Pushover API expects application/x-www-form-urlencoded, so we pass as `data`
            response = requests.post(self.API_URL, data=data, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            raise NotificationError(f"Failed to send Pushover notification: {e}")
        
        # Check Pushover API's logical response
        try:
            res_data = response.json()
            if res_data.get("status") != 1:
                errors = res_data.get("errors", ["Unknown error"])
                raise NotificationError(f"Pushover API error: {', '.join(errors)}")
        except ValueError:
            # In case the response is not valid JSON
            pass

def get_notification_config() -> Tuple[str, Dict[str, Any]]:
    """Loads configuration from file and environment variables.
    
    Environment variables override configuration file settings.
    
    Returns:
        A tuple of (method, notifier_config).
    """
    # Default configuration
    config = {
        "notification_method": "pushover",
        "notifiers": {
            "pushover": {}
        }
    }
    
    # 1. Load from file if exists
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                file_config = json.load(f)
                if isinstance(file_config, dict):
                    if "notification_method" in file_config:
                        config["notification_method"] = file_config["notification_method"]
                    if "notifiers" in file_config and isinstance(file_config["notifiers"], dict):
                        for key, val in file_config["notifiers"].items():
                            if isinstance(val, dict):
                                config["notifiers"][key] = val
        except Exception:
            # Ignore read errors to fallback gracefully
            pass

    # 2. Apply environment variable overrides
    method = os.environ.get("SHIPMYBOX_NOTIFICATION_METHOD", config["notification_method"])
    
    # Ensure method is in our notifiers dict
    if method not in config["notifiers"]:
        config["notifiers"][method] = {}
        
    # Apply specific env vars
    if method == "pushover":
        token = os.environ.get("PUSHOVER_TOKEN", config["notifiers"]["pushover"].get("token"))
        user = os.environ.get("PUSHOVER_USER", os.environ.get("PUSHOVER_USER_KEY", config["notifiers"]["pushover"].get("user")))
        if token:
            config["notifiers"]["pushover"]["token"] = token
        if user:
            config["notifiers"]["pushover"]["user"] = user

    return method, config["notifiers"].get(method, {})

def get_notifier(method: str, config: Dict[str, Any]) -> BaseNotifier:
    """Factory function to get a notifier instance.
    
    Args:
        method: The notification method (e.g. 'pushover').
        config: The configuration dict for the notifier.
        
    Returns:
        An instance of BaseNotifier.
        
    Raises:
        NotificationError: If the method is unsupported.
    """
    if method == "pushover":
        return PushoverNotifier(
            token=config.get("token", ""),
            user=config.get("user", "")
        )
    else:
        raise NotificationError(f"Unsupported notification method: {method}")
