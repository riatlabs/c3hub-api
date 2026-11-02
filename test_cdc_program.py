import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
from cdc_program import fetch_cdc_program, main


class TestCDCProgram(unittest.TestCase):
    def _setup_mock_client(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # 1. Mock Assembly Response
        mock_client.get_assemblies.return_value = {
            "data": [{"id": "cdc_1", "name": "CDC"}]
        }

        # 2. Mock Rooms Response (top-level /rooms/ since 40C3)
        mock_client.get_assembly_rooms.return_value = {
            "data": [
                {"id": "r_tri", "name": "Triangle Stage"},
                {"id": "r_sq", "name": "Square Space"},
            ]
        }

        # 3. Mock Events (fetched via paginate())
        mock_client.paginate.return_value = [
            {
                "id": "e1",
                "name": "Opening Ceremony",
                "room_id": "r_tri",
                "schedule_start": "2025-12-28T10:00:00+01:00",
            },
            {
                "id": "e2",
                "name": "Workshop",
                "room_id": "r_sq",
                "schedule_start": "2025-12-28T11:30:00+01:00",
            },
            {
                "id": "e3",
                "name": "Other Room Event",
                "room_id": "r_other",
                "schedule_start": "2025-12-28T12:00:00+01:00",
            },
        ]
        return mock_client

    @patch("cdc_program.C3HubClient")
    def test_fetch_cdc_program_success(self, mock_client_class):
        mock_client = self._setup_mock_client(mock_client_class)

        captured_output = StringIO()
        fetch_cdc_program("2025-12-28", "fake_token", year=2025, out=captured_output)
        output = captured_output.getvalue()

        # Verify client initialization
        mock_client_class.assert_called_once_with(year=2025, api_token="fake_token")

        # Verify interactions
        mock_client.get_assemblies.assert_called_with(params={"name": ["CDC"]})
        mock_client.get_assembly_rooms.assert_called_with("cdc_1")
        mock_client.paginate.assert_called()

        # Verify event query parameters (Berlin timezone, paginated)
        args, kwargs = mock_client.paginate.call_args
        self.assertEqual(args[0], "/events/")
        params = kwargs["params"]
        self.assertEqual(params["roomID"], ["r_tri", "r_sq"])
        self.assertEqual(params["startAfter"], "2025-12-28T00:00:00+01:00")
        self.assertEqual(params["startBefore"], "2025-12-28T23:59:59+01:00")
        self.assertEqual(params["pageSize"], 100)

        # Check output formatting
        self.assertIn("Found CDC assembly (ID: cdc_1)", output)
        self.assertIn("Found 2 spaces for CDC.", output)
        self.assertIn("CDC Program for 2025-12-28", output)
        self.assertIn("--- Triangle Stage ---", output)
        self.assertIn("[10:00] Opening Ceremony", output)
        self.assertIn("--- Square Space ---", output)
        self.assertIn("[11:30] Workshop", output)
        # Events of other rooms must not appear
        self.assertNotIn("Other Room Event", output)

    @patch("cdc_program.C3HubClient")
    def test_fetch_cdc_program_default_year(self, mock_client_class):
        self._setup_mock_client(mock_client_class)

        captured_output = StringIO()
        fetch_cdc_program("2026-12-27", "fake_token", out=captured_output)

        mock_client_class.assert_called_once_with(year=2026, api_token="fake_token")

    @patch("cdc_program.C3HubClient")
    def test_fetch_cdc_program_invalid_date(self, mock_client_class):
        self._setup_mock_client(mock_client_class)

        with self.assertRaises(ValueError) as cm:
            fetch_cdc_program("28.12.2025", "fake_token", year=2025, out=StringIO())
        self.assertIn("Invalid date format", str(cm.exception))

    @patch("cdc_program.C3HubClient")
    def test_fetch_cdc_program_no_rooms(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_assemblies.return_value = {
            "data": [{"id": "cdc_1", "name": "CDC"}]
        }
        mock_client.get_assembly_rooms.return_value = {"data": []}

        with self.assertRaises(ValueError) as cm:
            fetch_cdc_program("2025-12-28", "fake_token", year=2025, out=StringIO())
        self.assertIn("No spaces were found", str(cm.exception))

    @patch("cdc_program.C3HubClient")
    def test_fetch_cdc_program_no_assembly(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_assemblies.return_value = {"data": []}

        with self.assertRaises(ValueError) as cm:
            fetch_cdc_program("2025-12-28", "fake_token", year=2025, out=StringIO())
        self.assertIn("Could not find assembly", str(cm.exception))

    @patch("cdc_program.C3HubClient")
    def test_fetch_cdc_program_slug_fallback(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        def mock_get_assemblies(params):
            if "name" in params:
                return {"data": []}
            if "slug" in params:
                return {"data": [{"id": "cdc_1", "name": "CDC"}]}
            return {"data": []}

        mock_client.get_assemblies.side_effect = mock_get_assemblies
        mock_client.get_assembly_rooms.return_value = {
            "data": [{"id": "r_tri", "name": "Triangle Stage"}]
        }
        mock_client.paginate.return_value = []

        captured_output = StringIO()
        fetch_cdc_program("2025-12-28", "fake_token", year=2025, out=captured_output)

        self.assertIn("Found CDC assembly", captured_output.getvalue())

    @patch("cdc_program.C3HubClient")
    def test_fetch_cdc_program_event_fallback_room(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_assemblies.return_value = {
            "data": [{"id": "cdc_1", "name": "CDC"}]
        }
        mock_client.get_assembly_rooms.return_value = {
            "data": [{"id": "r_tri", "name": "Triangle Stage"}]
        }
        mock_client.paginate.return_value = [
            {"id": "e3", "name": "Event Without Specific Start", "room_id": "r_tri"}
        ]

        captured_output = StringIO()
        fetch_cdc_program("2025-12-28", "fake_token", year=2025, out=captured_output)

        self.assertIn("[TBA] Event Without Specific Start", captured_output.getvalue())

    @patch("cdc_program.C3HubClient")
    def test_fetch_cdc_program_http_error(self, mock_client_class):
        import requests

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        err_response = MagicMock()
        err_response.status_code = 401
        mock_client.get_assemblies.side_effect = requests.exceptions.HTTPError(
            "401 Unauthorized", response=err_response
        )

        with self.assertRaises(requests.exceptions.HTTPError):
            fetch_cdc_program("2025-12-28", "fake_token", year=2025, out=StringIO())

    @patch("cdc_program.fetch_cdc_program")
    def test_main_func(self, mock_fetch):
        testargs = ["cdc_program.py", "2025-12-28"]
        captured_err = StringIO()

        with (
            patch.object(sys, "argv", testargs),
            patch("sys.stderr", captured_err),
            patch.dict(os.environ, {"C3HUB_YEAR": "2026"}),
        ):
            for key in (
                "C3HUB_API_TOKEN",
                "C3HUB_API_TOKEN_2026",
                "C3HUB_API_TOKEN_40C3",
            ):
                os.environ.pop(key, None)
            main()
            mock_fetch.assert_called_with("2025-12-28", year=2026)
            self.assertIn("No C3HUB API token found", captured_err.getvalue())

        captured_err2 = StringIO()
        with (
            patch.object(sys, "argv", testargs),
            patch("sys.stderr", captured_err2),
            patch.dict(
                os.environ, {"C3HUB_YEAR": "2026", "C3HUB_API_TOKEN": "fake_token"}
            ),
        ):
            main()
            mock_fetch.assert_called_with("2025-12-28", year=2026)
            self.assertNotIn("No C3HUB API token found", captured_err2.getvalue())

    @patch("cdc_program.fetch_cdc_program")
    def test_main_http_error(self, mock_fetch):
        import requests

        err_response = MagicMock()
        err_response.status_code = 401
        mock_fetch.side_effect = requests.exceptions.HTTPError(
            "401 Unauthorized", response=err_response
        )

        testargs = ["cdc_program.py", "2025-12-28"]
        captured_err = StringIO()

        with (
            patch.object(sys, "argv", testargs),
            patch("sys.stderr", captured_err),
            patch.dict(
                os.environ, {"C3HUB_YEAR": "2026", "C3HUB_API_TOKEN": "fake_token"}
            ),
        ):
            with self.assertRaises(SystemExit) as cm:
                main()

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Authentication failed", captured_err.getvalue())


if __name__ == "__main__":
    unittest.main()
