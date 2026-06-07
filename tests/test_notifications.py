import json
import unittest
from unittest.mock import patch, MagicMock, mock_open

from shipmybox.exceptions import NotificationError
from shipmybox.notifications import (
    PushoverNotifier,
    get_notification_config,
    get_notifier,
)
from shipmybox.state import load_state, save_state
from shipmybox.cli import check
from typer.testing import CliRunner
from shipmybox.cli import app

class TestNotificationsAndState(unittest.TestCase):
    @patch("shipmybox.notifications.CONFIG_FILE")
    @patch.dict("os.environ", {}, clear=True)
    def test_get_notification_config_defaults(self, mock_config_path):
        mock_config_path.exists.return_value = False
        method, config = get_notification_config()
        self.assertEqual(method, "pushover")
        self.assertEqual(config, {})

    @patch("shipmybox.notifications.CONFIG_FILE")
    @patch.dict("os.environ", {"SHIPMYBOX_NOTIFICATION_METHOD": "pushover", "PUSHOVER_TOKEN": "env_token", "PUSHOVER_USER": "env_user"})
    def test_get_notification_config_env_vars(self, mock_config_path):
        mock_config_path.exists.return_value = False
        method, config = get_notification_config()
        self.assertEqual(method, "pushover")
        self.assertEqual(config.get("token"), "env_token")
        self.assertEqual(config.get("user"), "env_user")

    @patch("shipmybox.notifications.CONFIG_FILE")
    @patch.dict("os.environ", {}, clear=True)
    def test_get_notification_config_file(self, mock_config_path):
        mock_config_path.exists.return_value = True
        file_content = json.dumps({
            "notification_method": "pushover",
            "notifiers": {
                "pushover": {
                    "token": "file_token",
                    "user": "file_user"
                }
            }
        })
        with patch("builtins.open", mock_open(read_data=file_content)):
            method, config = get_notification_config()
            self.assertEqual(method, "pushover")
            self.assertEqual(config.get("token"), "file_token")
            self.assertEqual(config.get("user"), "file_user")

    @patch("shipmybox.notifications.CONFIG_FILE")
    @patch.dict("os.environ", {"PUSHOVER_TOKEN": "override_token"}, clear=True)
    def test_get_notification_config_env_override(self, mock_config_path):
        mock_config_path.exists.return_value = True
        file_content = json.dumps({
            "notification_method": "pushover",
            "notifiers": {
                "pushover": {
                    "token": "file_token",
                    "user": "file_user"
                }
            }
        })
        with patch("builtins.open", mock_open(read_data=file_content)):
            method, config = get_notification_config()
            self.assertEqual(method, "pushover")
            self.assertEqual(config.get("token"), "override_token")
            self.assertEqual(config.get("user"), "file_user")

    def test_get_notifier(self):
        notifier = get_notifier("pushover", {"token": "t", "user": "u"})
        self.assertIsInstance(notifier, PushoverNotifier)
        self.assertEqual(notifier.token, "t")
        self.assertEqual(notifier.user, "u")

        with self.assertRaises(NotificationError):
            get_notifier("unsupported_method", {})

    @patch("shipmybox.notifications.requests.post")
    def test_pushover_send_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": 1}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier = PushoverNotifier("token123", "user456")
        notifier.send("Hello Test")

        mock_post.assert_called_once_with(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": "token123",
                "user": "user456",
                "message": "Hello Test",
                "title": "ShipMyBox Monitor"
            },
            timeout=10
        )

    @patch("shipmybox.notifications.requests.post")
    def test_pushover_send_api_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": 0, "errors": ["invalid token"]}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier = PushoverNotifier("token123", "user456")
        with self.assertRaises(NotificationError) as ctx:
            notifier.send("Hello Test")
        self.assertIn("invalid token", str(ctx.exception))


class TestStateManagement(unittest.TestCase):
    @patch("shipmybox.state.STATE_FILE")
    def test_load_state_not_exists(self, mock_state_path):
        mock_state_path.exists.return_value = False
        self.assertIsNone(load_state())

    @patch("shipmybox.state.STATE_FILE")
    def test_load_state_success(self, mock_state_path):
        mock_state_path.exists.return_value = True
        state_data = json.dumps({"number": "123", "status": "Shipped"})
        with patch("builtins.open", mock_open(read_data=state_data)):
            state = load_state()
            self.assertEqual(state, {"number": "123", "status": "Shipped"})

    @patch("shipmybox.state.STATE_FILE")
    def test_save_state(self, mock_state_path):
        mock_state_path.parent.mkdir.return_value = None
        m = mock_open()
        with patch("builtins.open", m):
            save_state({"number": "123", "status": "Shipped"})
            m.assert_called_once_with(mock_state_path, "w")
            # Get all written chunks to check content
            handle = m()
            written = "".join([call[0][0] for call in handle.write.call_args_list])
            self.assertIn('"number": "123"', written)


class TestCliCheckCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    @patch("shipmybox.cli.get_client")
    @patch("shipmybox.cli.load_state")
    @patch("shipmybox.cli.save_state")
    @patch("shipmybox.cli.get_notifier")
    @patch("shipmybox.cli.get_notification_config")
    def test_check_first_run(self, mock_get_config, mock_get_notifier, mock_save_state, mock_load_state, mock_get_client):
        # Mock client returning parcels
        mock_client = MagicMock()
        mock_client.get_parcels.return_value = [{"number": "PAR123", "status": "Processing"}]
        mock_get_client.return_value = mock_client

        # First run: state file doesn't exist
        mock_load_state.return_value = None
        mock_get_config.return_value = ("pushover", {"token": "t", "user": "u"})
        
        mock_notifier = MagicMock()
        mock_get_notifier.return_value = mock_notifier

        result = self.runner.invoke(app, ["check", "--verbose"])
        self.assertEqual(result.exit_code, 0)
        
        # State should be updated, notifier should be called
        mock_save_state.assert_called_once_with({"number": "PAR123", "status": "Processing"})
        mock_notifier.send.assert_called_once()
        sent_message = mock_notifier.send.call_args[0][0]
        self.assertIn("New parcel has appeared", sent_message)
        self.assertIn("PAR123", sent_message)
        self.assertIn("First run detected", result.output)

    @patch("shipmybox.cli.get_client")
    @patch("shipmybox.cli.load_state")
    @patch("shipmybox.cli.save_state")
    @patch("shipmybox.cli.get_notifier")
    @patch("shipmybox.cli.get_notification_config")
    def test_check_no_changes(self, mock_get_config, mock_get_notifier, mock_save_state, mock_load_state, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_parcels.return_value = [{"number": "PAR123", "status": "Processing"}]
        mock_get_client.return_value = mock_client

        mock_load_state.return_value = {"number": "PAR123", "status": "Processing"}
        mock_get_config.return_value = ("pushover", {})

        result = self.runner.invoke(app, ["check", "--verbose"])
        self.assertEqual(result.exit_code, 0)
        
        # State should be saved again, notifier not called
        mock_save_state.assert_called_once_with({"number": "PAR123", "status": "Processing"})
        mock_get_notifier.assert_not_called()
        self.assertIn("No changes detected", result.output)

    @patch("shipmybox.cli.get_client")
    @patch("shipmybox.cli.load_state")
    @patch("shipmybox.cli.save_state")
    @patch("shipmybox.cli.get_notifier")
    @patch("shipmybox.cli.get_notification_config")
    def test_check_status_changed(self, mock_get_config, mock_get_notifier, mock_save_state, mock_load_state, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_parcels.return_value = [{"number": "PAR123", "status": "Delivered"}]
        mock_get_client.return_value = mock_client

        mock_load_state.return_value = {"number": "PAR123", "status": "Processing"}
        mock_get_config.return_value = ("pushover", {"token": "t", "user": "u"})
        
        mock_notifier = MagicMock()
        mock_get_notifier.return_value = mock_notifier

        result = self.runner.invoke(app, ["check", "--verbose"])
        self.assertEqual(result.exit_code, 0)

        mock_save_state.assert_called_once_with({"number": "PAR123", "status": "Delivered"})
        mock_notifier.send.assert_called_once()
        sent_message = mock_notifier.send.call_args[0][0]
        self.assertIn("status changed: Processing -> Delivered", sent_message)

    @patch("shipmybox.cli.get_client")
    @patch("shipmybox.cli.load_state")
    @patch("shipmybox.cli.save_state")
    @patch("shipmybox.cli.get_notifier")
    @patch("shipmybox.cli.get_notification_config")
    def test_check_new_parcel(self, mock_get_config, mock_get_notifier, mock_save_state, mock_load_state, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_parcels.return_value = [
            {"number": "PAR123", "status": "Delivered"},
            {"number": "PAR124", "status": "In Transit"}
        ]
        mock_get_client.return_value = mock_client

        mock_load_state.return_value = {"number": "PAR123", "status": "Delivered"}
        mock_get_config.return_value = ("pushover", {"token": "t", "user": "u"})
        
        mock_notifier = MagicMock()
        mock_get_notifier.return_value = mock_notifier

        result = self.runner.invoke(app, ["check", "--verbose"])
        self.assertEqual(result.exit_code, 0)

        mock_save_state.assert_called_once_with({"number": "PAR124", "status": "In Transit"})
        mock_notifier.send.assert_called_once()
        sent_message = mock_notifier.send.call_args[0][0]
        self.assertIn("New parcel has appeared", sent_message)
        self.assertIn("PAR124", sent_message)

    @patch("shipmybox.cli.get_client")
    @patch("shipmybox.cli.load_state")
    @patch("shipmybox.cli.save_state")
    @patch("shipmybox.cli.get_notifier")
    @patch("shipmybox.cli.get_notification_config")
    def test_check_dry_run(self, mock_get_config, mock_get_notifier, mock_save_state, mock_load_state, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_parcels.return_value = [{"number": "PAR123", "status": "Delivered"}]
        mock_get_client.return_value = mock_client

        mock_load_state.return_value = {"number": "PAR123", "status": "Processing"}
        mock_get_config.return_value = ("pushover", {"token": "t", "user": "u"})
        
        mock_notifier = MagicMock()
        mock_get_notifier.return_value = mock_notifier

        result = self.runner.invoke(app, ["check", "--dry-run", "--verbose"])
        self.assertEqual(result.exit_code, 0)

        # In dry run: state should NOT be saved, and notifier should NOT be called
        mock_save_state.assert_not_called()
        mock_notifier.send.assert_not_called()
        self.assertIn("DRY RUN: Notification would be sent", result.output)
