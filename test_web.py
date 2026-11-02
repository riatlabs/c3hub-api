import os
import unittest
from unittest.mock import patch
from web import app


class TestWebApp(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    @patch("web.C3HubClient.ping")
    def test_index_route(self, mock_ping):
        mock_ping.return_value = "pong"
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"C3 Hub Client Web", response.data)
        self.assertIn(b"pong", response.data)

    @patch("web.fetch_cdc_program")
    @patch("web.C3HubClient.ping")
    def test_cdc_program_route(self, mock_ping, mock_fetch):
        mock_ping.return_value = "pong"

        # Mock what fetch_cdc_program does: write into the provided output stream
        def mock_fetch_effect(date, year=None, out=None):
            print(f"Mocked program output for {date}", file=out)

        mock_fetch.side_effect = mock_fetch_effect

        response = self.client.get("/cdc_program?date=2025-12-28")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Mocked program output for 2025-12-28", response.data)

        # Default year is 2026 and an output stream is passed
        args, kwargs = mock_fetch.call_args
        self.assertEqual(args[0], "2025-12-28")
        self.assertEqual(kwargs["year"], 2026)
        self.assertIsNotNone(kwargs["out"])

    @patch("web.fetch_cdc_program")
    @patch("web.C3HubClient.ping")
    def test_cdc_program_route_year_from_env(self, mock_ping, mock_fetch):
        mock_ping.return_value = "pong"

        def mock_fetch_effect(date, year=None, out=None):
            print(f"year={year}", file=out)

        mock_fetch.side_effect = mock_fetch_effect

        with patch.dict(os.environ, {"C3HUB_YEAR": "2025"}):
            response = self.client.get("/cdc_program?date=2025-12-28")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"year=2025", response.data)
        _, kwargs = mock_fetch.call_args
        self.assertEqual(kwargs["year"], 2025)

    @patch("web.fetch_cdc_program")
    @patch("web.C3HubClient.ping")
    def test_cdc_program_route_handles_errors(self, mock_ping, mock_fetch):
        mock_ping.return_value = "pong"
        mock_fetch.side_effect = ValueError("Could not find the CDC assembly.")

        response = self.client.get("/cdc_program?date=2025-12-28")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Could not find the CDC assembly.", response.data)

    @patch("web.C3HubClient.ping")
    def test_api_ping_route(self, mock_ping):
        mock_ping.return_value = "pong"
        response = self.client.get("/api/ping")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "success", "data": "pong"})

    @patch("web.C3HubClient.ping")
    def test_index_route_error(self, mock_ping):
        mock_ping.side_effect = Exception("Ping failed")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Error: Ping failed", response.data)

    def test_cdc_program_route_no_date(self):
        response = self.client.get("/cdc_program")
        # Should render index if no date is provided
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"C3 Hub Client Web", response.data)

    @patch("web.fetch_cdc_program")
    @patch("web.C3HubClient.ping")
    def test_cdc_program_route_exception(self, mock_ping, mock_fetch):
        mock_ping.return_value = "pong"
        mock_fetch.side_effect = Exception("Fetch failed")

        response = self.client.get("/cdc_program?date=2025-12-28")
        self.assertEqual(response.status_code, 200)
        # Should not crash, output might be empty or contain standard print

    @patch("web.fetch_cdc_program")
    @patch("web.C3HubClient.ping")
    def test_cdc_program_route_systemexit(self, mock_ping, mock_fetch):
        mock_ping.return_value = "pong"
        mock_fetch.side_effect = SystemExit(1)

        response = self.client.get("/cdc_program?date=2025-12-28")
        self.assertEqual(response.status_code, 200)

    @patch("web.fetch_cdc_program")
    @patch("web.C3HubClient.ping")
    def test_cdc_program_route_exception_ping(self, mock_ping, mock_fetch):
        mock_ping.side_effect = Exception("Ping failed")
        mock_fetch.return_value = None

        response = self.client.get("/cdc_program?date=2025-12-28")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Error: Ping failed", response.data)

    @patch("web.C3HubClient.ping")
    def test_api_ping_route_error(self, mock_ping):
        mock_ping.side_effect = Exception("Ping failed")
        response = self.client.get("/api/ping")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json, {"status": "error", "message": "Ping failed"})

    @patch("web.app.run")
    def test_main_func(self, mock_run):
        from web import main
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"PORT": "5001"}):
            main()
            mock_run.assert_called_with(host="0.0.0.0", port=5001)


if __name__ == "__main__":
    unittest.main()
