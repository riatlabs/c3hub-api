import json
import os
import sys
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from c3hub_cli import fetch_schedule_data, format_markdown, main


class TestC3HubCLI(unittest.TestCase):
    @patch("c3hub_cli.C3HubClient")
    def test_fetch_schedule_data_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock assemblies
        mock_client.get_assemblies.return_value = {
            "data": [{"id": "a1", "name": "Test Assembly"}]
        }

        # Mock rooms
        mock_client.get_assembly_rooms.return_value = {
            "data": [{"id": "r1", "name": "Room 1"}]
        }

        # Mock events (fetched via paginate())
        mock_client.paginate.return_value = [
            {
                "id": "e1",
                "name": "Event 1",
                "room_id": "r1",
                "schedule_start": "2025-12-28T10:00:00Z",
            },
            {
                "id": "e2",
                "name": "Event 2",
                "room": {"id": "r1"},  # legacy fallback field
                # no schedule_start
            },
        ]

        data = fetch_schedule_data("Test Assembly", "2025-12-28", "fake_token")

        mock_client_class.assert_called_once_with(year=2026, api_token="fake_token")
        mock_client.paginate.assert_called()

        # Day boundaries use Europe/Berlin (UTC+1 in winter), not UTC
        args, kwargs = mock_client.paginate.call_args
        self.assertEqual(args[0], "/events/")
        self.assertEqual(kwargs["params"]["startAfter"], "2025-12-28T00:00:00+01:00")
        self.assertEqual(kwargs["params"]["startBefore"], "2025-12-28T23:59:59+01:00")

        self.assertEqual(data["assembly"], "Test Assembly")
        self.assertEqual(data["date"], "2025-12-28")
        self.assertIn("Room 1", data["schedule"])
        self.assertEqual(len(data["schedule"]["Room 1"]), 2)
        # Should sort by start time, so e1 comes first
        self.assertEqual(data["schedule"]["Room 1"][0]["name"], "Event 1")

    @patch("c3hub_cli.C3HubClient")
    def test_fetch_schedule_data_year(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_assemblies.return_value = {
            "data": [{"id": "a1", "name": "Test Assembly"}]
        }
        mock_client.get_assembly_rooms.return_value = {
            "data": [{"id": "r1", "name": "Room 1"}]
        }
        mock_client.paginate.return_value = []

        fetch_schedule_data("Test Assembly", "2025-12-28", year=2025)

        mock_client_class.assert_called_once_with(year=2025, api_token=None)

    @patch("c3hub_cli.C3HubClient")
    def test_fetch_schedule_data_no_assembly(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_assemblies.return_value = {"data": []}

        with self.assertRaises(ValueError) as cm:
            fetch_schedule_data("NotFound", "2025-12-28", "fake_token")
        self.assertIn("Could not find assembly: NotFound", str(cm.exception))

    @patch("c3hub_cli.C3HubClient")
    def test_fetch_schedule_data_slug_fallback(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        def mock_get_assemblies(params):
            if "name" in params:
                return {"data": []}
            if "slug" in params:
                return {"data": [{"id": "a1", "name": "Test Assembly"}]}
            return {"data": []}

        mock_client.get_assemblies.side_effect = mock_get_assemblies
        mock_client.get_assembly_rooms.return_value = {
            "data": [{"id": "r1", "name": "Room 1"}]
        }
        mock_client.paginate.return_value = []

        data = fetch_schedule_data("Test-Slug", "2025-12-28", "fake_token")
        self.assertEqual(data["assembly"], "Test Assembly")
        # Slugs are case-sensitive: the fallback must use the lowercase query
        params = [
            call.kwargs["params"] for call in mock_client.get_assemblies.call_args_list
        ]
        self.assertIn({"slug": ["test-slug"]}, params)

    @patch("c3hub_cli.C3HubClient")
    def test_fetch_schedule_data_no_rooms(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_assemblies.return_value = {
            "data": [{"id": "a1", "name": "Test Assembly"}]
        }
        mock_client.get_assembly_rooms.return_value = {"data": []}

        with self.assertRaises(ValueError) as cm:
            fetch_schedule_data("Test Assembly", "2025-12-28", "fake_token")
        self.assertIn("No spaces were found for assembly", str(cm.exception))

    @patch("c3hub_cli.C3HubClient")
    def test_fetch_schedule_data_invalid_date(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_assemblies.return_value = {
            "data": [{"id": "a1", "name": "Test Assembly"}]
        }
        mock_client.get_assembly_rooms.return_value = {
            "data": [{"id": "r1", "name": "Room 1"}]
        }

        with self.assertRaises(ValueError) as cm:
            fetch_schedule_data("Test Assembly", "28.12.2025", "fake_token")
        self.assertIn("Invalid date format", str(cm.exception))

    def test_format_markdown(self):
        data = {
            "assembly": "Test",
            "date": "2025-12-28",
            "schedule": {
                "Room A": [
                    {"name": "E1", "schedule_start": "2025-12-28T10:00:00Z"},
                    {"name": "E2"},  # No start
                ],
                "Room B": [],  # Empty
            },
        }
        md = format_markdown(data)
        self.assertIn("# Test Program - 2025-12-28", md)
        self.assertIn("## Room A", md)
        self.assertIn("- **10:00**: E1", md)
        self.assertIn("- **TBA**: E2", md)
        self.assertIn("## Room B", md)
        self.assertIn("*No events scheduled.*", md)

    @patch("c3hub_cli.fetch_schedule_data")
    def test_main_export_markdown(self, mock_fetch):
        mock_fetch.return_value = {
            "assembly": "Test",
            "date": "2025-12-28",
            "schedule": {"Room A": []},
        }
        testargs = [
            "c3hub_cli",
            "export-markdown",
            "--assembly",
            "Test",
            "--date",
            "2025-12-28",
        ]
        captured_output = StringIO()

        with (
            patch.object(sys, "argv", testargs),
            patch("sys.stdout", captured_output),
            patch.dict(os.environ, {"C3HUB_API_TOKEN": "fake_token"}),
        ):
            main()

        out = captured_output.getvalue()
        self.assertIn("# Test Program - 2025-12-28", out)

    @patch("c3hub_cli.fetch_schedule_data")
    def test_main_to_json(self, mock_fetch):
        mock_fetch.return_value = {
            "assembly": "Test",
            "date": "2025-12-28",
            "schedule": {"Room A": []},
        }
        testargs = [
            "c3hub_cli",
            "to-json",
            "--assembly",
            "Test",
            "--date",
            "2025-12-28",
        ]
        captured_output = StringIO()

        with (
            patch.object(sys, "argv", testargs),
            patch("sys.stdout", captured_output),
            patch.dict(os.environ, {"C3HUB_API_TOKEN": "fake_token"}),
        ):
            main()

        out = captured_output.getvalue()
        data = json.loads(out)
        self.assertEqual(data["assembly"], "Test")

    @patch("c3hub_cli.fetch_schedule_data")
    def test_main_year_option(self, mock_fetch):
        mock_fetch.return_value = {
            "assembly": "Test",
            "date": "2025-12-28",
            "schedule": {},
        }
        testargs = [
            "c3hub_cli",
            "to-json",
            "--assembly",
            "Test",
            "--date",
            "2025-12-28",
            "--year",
            "2025",
        ]

        with (
            patch.object(sys, "argv", testargs),
            patch("sys.stdout", StringIO()),
            patch.dict(os.environ, {"C3HUB_API_TOKEN": "fake_token"}),
        ):
            main()

        _, kwargs = mock_fetch.call_args
        self.assertEqual(kwargs["year"], 2025)

    @patch("c3hub_cli.fetch_schedule_data")
    def test_main_value_error(self, mock_fetch):
        mock_fetch.side_effect = ValueError("Not found error message")
        testargs = [
            "c3hub_cli",
            "to-json",
            "--assembly",
            "Test",
            "--date",
            "2025-12-28",
        ]
        captured_err = StringIO()

        with (
            patch.object(sys, "argv", testargs),
            patch("sys.stderr", captured_err),
            patch.dict(os.environ, {"C3HUB_API_TOKEN": "fake_token"}),
        ):
            with self.assertRaises(SystemExit) as cm:
                main()

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Not found error message", captured_err.getvalue())

    @patch("c3hub_cli.fetch_schedule_data")
    def test_main_http_error(self, mock_fetch):
        import requests

        err_response = MagicMock()
        err_response.status_code = 401
        mock_fetch.side_effect = requests.exceptions.HTTPError(
            "401 Unauthorized", response=err_response
        )

        testargs = [
            "c3hub_cli",
            "to-json",
            "--assembly",
            "Test",
            "--date",
            "2025-12-28",
        ]
        captured_err = StringIO()

        with (
            patch.object(sys, "argv", testargs),
            patch("sys.stderr", captured_err),
            patch.dict(os.environ, {"C3HUB_API_TOKEN": "fake_token"}),
        ):
            with self.assertRaises(SystemExit) as cm:
                main()

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Authentication failed", captured_err.getvalue())

    @patch("c3hub_cli.fetch_schedule_data")
    def test_main_generic_error(self, mock_fetch):
        mock_fetch.side_effect = Exception("Some weird error")
        testargs = [
            "c3hub_cli",
            "to-json",
            "--assembly",
            "Test",
            "--date",
            "2025-12-28",
        ]
        captured_err = StringIO()

        with (
            patch.object(sys, "argv", testargs),
            patch("sys.stderr", captured_err),
            patch.dict(os.environ, {"C3HUB_API_TOKEN": "fake_token"}),
        ):
            with self.assertRaises(SystemExit) as cm:
                main()

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Some weird error", captured_err.getvalue())


if __name__ == "__main__":
    unittest.main()
