"""Edge-case tests for cdc_program (defensive room filtering, API errors)."""

import io
import unittest
from unittest.mock import MagicMock, patch

import cdc_program


class TestCoverageGap(unittest.TestCase):
    @patch("cdc_program.C3HubClient")
    def test_missing_room_events(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.get_assemblies.return_value = {
            "data": [{"id": "cdc_1", "name": "CDC"}]
        }
        # None entries (invalid API data) must be skipped
        mock_client.get_assembly_rooms.return_value = {
            "data": [{"id": "r_tri", "name": "Triangle Stage"}, None]
        }
        mock_client.paginate.return_value = []

        out = io.StringIO()
        cdc_program.fetch_cdc_program("2025-12-28", "fake_token", year=2025, out=out)

        output = out.getvalue()
        self.assertIn("Found 1 spaces for CDC.", output)
        self.assertIn("Triangle Stage", output)
        self.assertIn("No events scheduled.", output)

    @patch("cdc_program.C3HubClient")
    def test_general_http_error(self, mock_client_class):
        import requests

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        err_response = MagicMock()
        err_response.status_code = 500
        mock_client.get_assemblies.side_effect = requests.exceptions.HTTPError(
            "500 Server Error", response=err_response
        )

        with self.assertRaises(requests.exceptions.HTTPError):
            cdc_program.fetch_cdc_program(
                "2025-12-28", "fake_token", year=2025, out=io.StringIO()
            )


if __name__ == "__main__":
    unittest.main()
