import os
import unittest
from unittest.mock import patch, MagicMock
from c3hub import C3HubClient, default_year, resolve_api_token


class TestC3HubClient(unittest.TestCase):
    def setUp(self):
        self.client = C3HubClient(year=2025, api_token="test_token")
        self.client_2026 = C3HubClient(year=2026, api_token="test_token")

    def assert_request(self, mock_request, method, url, params=None, timeout=None):
        """Assert that exactly one request was made with the given arguments."""
        mock_request.assert_called_once_with(
            method,
            url,
            params=params,
            timeout=timeout if timeout is not None else self.client.timeout,
        )

    # --- Configuration ---

    def test_default_year_is_2026(self):
        client = C3HubClient()
        self.assertEqual(client.base_url, "https://api.events.ccc.de/congress/2026")

    def test_legacy_year_keeps_v2_prefix(self):
        client = C3HubClient(year=2025)
        self.assertEqual(client.base_url, "https://api.events.ccc.de/congress/2025/v2")

    @patch("c3hub.requests.Session.request")
    def test_get_user_by_username_2026(self, mock_request):
        mock_request.return_value = MagicMock()
        self.client_2026.get_user("alice")
        self.assert_request(
            mock_request, "GET", "https://api.events.ccc.de/congress/2026/users/alice"
        )

    @patch("c3hub.requests.Session.request")
    def test_revoke_token(self, mock_request):
        mock_request.return_value = MagicMock()
        self.client_2026.revoke_token()
        self.assert_request(
            mock_request, "POST", "https://api.events.ccc.de/congress/2026/auth/revoke/"
        )

    @patch("c3hub.requests.Session.request")
    def test_get_languages(self, mock_request):
        mock_request.return_value = MagicMock()
        self.client_2026.get_languages()
        self.client_2026.get_language("de")
        urls = [c.args[1] for c in mock_request.call_args_list]
        self.assertEqual(
            urls,
            [
                "https://api.events.ccc.de/congress/2026/languages/",
                "https://api.events.ccc.de/congress/2026/languages/de/",
            ],
        )

    @patch("c3hub.requests.Session.request")
    def test_custom_timeout(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = "pong"
        mock_request.return_value = mock_response

        client = C3HubClient(year=2026, timeout=5)
        client.ping()
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2026/ping/",
            timeout=5,
        )

    # --- Token aus der Umgebung ---

    @patch.dict(
        os.environ,
        {
            "C3HUB_API_TOKEN": "token_generic",
            "C3HUB_API_TOKEN_2025": "token_2025",
            "C3HUB_API_TOKEN_39C3": "token_39c3",
        },
    )
    def test_token_env_prefers_year_variable(self):
        client = C3HubClient(year=2025)
        self.assertEqual(client.session.headers["Authorization"], "Bearer token_2025")

    @patch.dict(
        os.environ,
        {
            "C3HUB_API_TOKEN": "token_generic",
            "C3HUB_API_TOKEN_2025": "",
            "C3HUB_API_TOKEN_39C3": "token_39c3",
        },
    )
    def test_token_env_supports_c3_suffix(self):
        client = C3HubClient(year=2025)
        self.assertEqual(client.session.headers["Authorization"], "Bearer token_39c3")

    @patch.dict(
        os.environ,
        {
            "C3HUB_API_TOKEN": "token_generic",
            "C3HUB_API_TOKEN_2026": "",
            "C3HUB_API_TOKEN_40C3": "",
        },
    )
    def test_token_env_generic_fallback(self):
        client = C3HubClient(year=2026)
        self.assertEqual(
            client.session.headers["Authorization"], "Bearer token_generic"
        )

    @patch.dict(os.environ, {"C3HUB_API_TOKEN": "token_generic"})
    def test_explicit_token_wins_over_env(self):
        client = C3HubClient(year=2026, api_token="explicit_token")
        self.assertEqual(
            client.session.headers["Authorization"], "Bearer explicit_token"
        )

    # --- Ping ---
    @patch("c3hub.requests.Session.request")
    def test_ping(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = "pong"
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        response = self.client.ping()
        self.assertEqual(response, "pong")
        self.assert_request(
            mock_request, "GET", "https://api.events.ccc.de/congress/2025/v2/ping/"
        )

    # --- Conference & Tracks ---
    @patch("c3hub.requests.Session.request")
    def test_get_conference_info(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"title": "39C3"}}
        mock_request.return_value = mock_response

        response = self.client.get_conference_info()
        self.assertEqual(response["data"]["title"], "39C3")
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/conference/",
        )

    @patch("c3hub.requests.Session.request")
    def test_get_tracks(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": 1, "name": "Security"}]}
        mock_request.return_value = mock_response

        response = self.client.get_tracks(params={"pageSize": 10})
        self.assertEqual(len(response["data"]), 1)
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/conference/tracks/",
            params={"pageSize": 10},
        )

    @patch("c3hub.requests.Session.request")
    def test_get_track(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"id": "t1", "name": "Art"}}
        mock_request.return_value = mock_response

        response = self.client.get_track("t1")
        self.assertEqual(response["data"]["name"], "Art")
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/conference/tracks/t1/",
        )

    # --- Assemblies ---
    @patch("c3hub.requests.Session.request")
    def test_get_assemblies(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"id": "1", "name": "Assembly1"}],
            "pagination": {},
        }
        mock_request.return_value = mock_response

        response = self.client.get_assemblies(params={"pageSize": 1})
        self.assertEqual(len(response["data"]), 1)
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/assemblies/",
            params={"pageSize": 1},
        )

    @patch("c3hub.requests.Session.request")
    def test_get_assemblies_by_state(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "3", "state": "placed"}]}
        mock_request.return_value = mock_response

        response = self.client.get_assemblies(params={"state": "placed"})
        self.assertEqual(response["data"][0]["state"], "placed")
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/assemblies/",
            params={"state": "placed"},
        )

    @patch("c3hub.requests.Session.request")
    def test_get_habitats(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"id": "2", "name": "Habitat1", "hierarchy": "cluster"}]
        }
        mock_request.return_value = mock_response

        response = self.client.get_assemblies(params={"hierarchy": "cluster"})
        self.assertEqual(len(response["data"]), 1)
        self.assertEqual(response["data"][0]["hierarchy"], "cluster")
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/assemblies/",
            params={"hierarchy": "cluster"},
        )

    @patch("c3hub.requests.Session.request")
    def test_get_assembly(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"id": "a1", "name": "Assm1"}}
        mock_request.return_value = mock_response

        response = self.client.get_assembly("a1")
        self.assertEqual(response["data"]["name"], "Assm1")
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/assemblies/a1/",
        )

    # --- Rooms (top-level since 40C3 / 2026) ---
    @patch("c3hub.requests.Session.request")
    def test_get_rooms(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "r1", "name": "Hall 1"}]}
        mock_request.return_value = mock_response

        response = self.client_2026.get_rooms(params={"roomType": ["stage"]})
        self.assertEqual(response["data"][0]["name"], "Hall 1")
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2026/rooms/",
            params={"roomType": ["stage"]},
        )

    @patch("c3hub.requests.Session.request")
    def test_get_room(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"id": "r1", "name": "Hall 1"}}
        mock_request.return_value = mock_response

        response = self.client_2026.get_room("r1")
        self.assertEqual(response["data"]["name"], "Hall 1")
        self.assert_request(
            mock_request, "GET", "https://api.events.ccc.de/congress/2026/rooms/r1/"
        )

    @patch("c3hub.requests.Session.request")
    def test_get_assembly_rooms_40c3_uses_top_level_rooms_endpoint(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "r1", "name": "Triangle"}]}
        mock_request.return_value = mock_response

        response = self.client_2026.get_assembly_rooms("a1")
        self.assertEqual(response["data"][0]["id"], "r1")
        # 40C3: rooms are served via /rooms/?assemblyID=..., the old
        # /assemblies/{id}/rooms/ route no longer exists.
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2026/rooms/",
            params={"assemblyID": "a1"},
        )

    @patch("c3hub.requests.Session.request")
    def test_get_assembly_rooms_39c3_uses_legacy_endpoint(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "r1", "name": "Triangle"}]}
        mock_request.return_value = mock_response

        response = self.client.get_assembly_rooms("a1")
        self.assertEqual(response["data"][0]["id"], "r1")
        # The 2025 API does not have the top-level /rooms/ endpoint.
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/assemblies/a1/rooms/",
        )

    @patch("c3hub.requests.Session.request")
    def test_get_assembly_rooms_merges_extra_params(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_request.return_value = mock_response

        self.client_2026.get_assembly_rooms("a1", params={"pageSize": 50})
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2026/rooms/",
            params={"pageSize": 50, "assemblyID": "a1"},
        )

    @patch("c3hub.requests.Session.request")
    def test_get_assembly_room_39c3_uses_legacy_endpoint(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"id": "r1", "name": "Room1"}}
        mock_request.return_value = mock_response

        response = self.client.get_assembly_room("a1", "r1")
        self.assertEqual(response["data"]["name"], "Room1")
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/assemblies/a1/rooms/r1/",
        )

    @patch("c3hub.requests.Session.request")
    def test_get_assembly_room_40c3_uses_top_level_endpoint(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"id": "r1", "name": "Room1"}}
        mock_request.return_value = mock_response

        response = self.client_2026.get_assembly_room("a1", "r1")
        self.assertEqual(response["data"]["name"], "Room1")
        self.assert_request(
            mock_request, "GET", "https://api.events.ccc.de/congress/2026/rooms/r1/"
        )

    # --- Events ---
    @patch("c3hub.requests.Session.request")
    def test_get_events_for_habitat(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "e1", "name": "Event1"}]}
        mock_request.return_value = mock_response

        response = self.client.get_events(params={"assemblyID": "hab1"})
        self.assertEqual(len(response["data"]), 1)
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/events/",
            params={"assemblyID": "hab1"},
        )

    @patch("c3hub.requests.Session.request")
    def test_get_events_by_kind_and_tags(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "e2", "kind": "sos"}]}
        mock_request.return_value = mock_response

        response = self.client.get_events(params={"kind": "sos", "tag": ["hacking"]})
        self.assertEqual(response["data"][0]["kind"], "sos")
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/events/",
            params={"kind": "sos", "tag": ["hacking"]},
        )

    @patch("c3hub.requests.Session.request")
    def test_get_events_upcoming_filter(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "e3", "name": "Upcoming"}]}
        mock_request.return_value = mock_response

        response = self.client_2026.get_events(
            params={"upcoming": True, "current": True}
        )
        self.assertEqual(response["data"][0]["name"], "Upcoming")
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2026/events/",
            params={"upcoming": True, "current": True},
        )

    @patch("c3hub.requests.Session.request")
    def test_get_event(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"id": "e1", "name": "Event1"}}
        mock_request.return_value = mock_response

        response = self.client.get_event("e1")
        self.assertEqual(response["data"]["name"], "Event1")
        self.assert_request(
            mock_request, "GET", "https://api.events.ccc.de/congress/2025/v2/events/e1/"
        )

    # --- Pagination helper ---
    @patch("c3hub.requests.Session.request")
    def test_paginate_follows_pages(self, mock_request):
        pages = {
            1: {
                "data": [{"id": "e1"}, {"id": "e2"}],
                "pagination": {"page": 1, "page_size": 2, "total": 3},
            },
            2: {
                "data": [{"id": "e3"}],
                "pagination": {"page": 2, "page_size": 2, "total": 3},
            },
        }

        def side_effect(method, url, params=None, timeout=None):
            response = MagicMock()
            response.json.return_value = pages[params["page"]]
            response.raise_for_status.return_value = None
            return response

        mock_request.side_effect = side_effect

        items = list(self.client.paginate("/events/", params={"pageSize": 2}))
        self.assertEqual([item["id"] for item in items], ["e1", "e2", "e3"])
        self.assertEqual(mock_request.call_count, 2)

    @patch("c3hub.requests.Session.request")
    def test_paginate_stops_without_pagination_info(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "e1"}]}  # no pagination key
        mock_request.return_value = mock_response

        items = list(self.client.paginate("/events/"))
        self.assertEqual([item["id"] for item in items], ["e1"])
        self.assertEqual(mock_request.call_count, 1)

    # --- Projects ---
    @patch("c3hub.requests.Session.request")
    def test_get_projects(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "p1", "name": "Project1"}]}
        mock_request.return_value = mock_response

        response = self.client.get_projects()
        self.assertEqual(len(response["data"]), 1)
        self.assert_request(
            mock_request, "GET", "https://api.events.ccc.de/congress/2025/v2/projects/"
        )

    @patch("c3hub.requests.Session.request")
    def test_get_project(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"id": "p1", "name": "Project1"}}
        mock_request.return_value = mock_response

        response = self.client.get_project("p1")
        self.assertEqual(response["data"]["name"], "Project1")
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/projects/p1/",
        )

    # --- Users ---
    @patch("c3hub.requests.Session.request")
    def test_get_user(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"id": "u1", "display_name": "User1"}
        }
        mock_request.return_value = mock_response

        response = self.client.get_user("u1")
        self.assertEqual(response["data"]["display_name"], "User1")
        self.assert_request(
            mock_request, "GET", "https://api.events.ccc.de/congress/2025/v2/users/u1"
        )

    @patch("c3hub.requests.Session.request")
    def test_get_me(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"id": "u1", "display_name": "Me"}}
        mock_request.return_value = mock_response

        response = self.client_2026.get_me()
        self.assertEqual(response["data"]["display_name"], "Me")
        self.assert_request(
            mock_request, "GET", "https://api.events.ccc.de/congress/2026/auth/me/"
        )

    # --- Badges ---
    @patch("c3hub.requests.Session.request")
    def test_get_badges(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "b1", "name": "Badge1"}]}
        mock_request.return_value = mock_response

        response = self.client.get_badges()
        self.assertEqual(len(response["data"]), 1)
        self.assert_request(
            mock_request, "GET", "https://api.events.ccc.de/congress/2025/v2/badges/"
        )

    @patch("c3hub.requests.Session.request")
    def test_get_badges_by_category(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"id": "b2", "category": {"slug": "assembly"}}]
        }
        mock_request.return_value = mock_response

        response = self.client.get_badges(params={"category": ["assembly"]})
        self.assertEqual(response["data"][0]["category"]["slug"], "assembly")
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/badges/",
            params={"category": ["assembly"]},
        )

    @patch("c3hub.requests.Session.request")
    def test_get_badge(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"id": "b1", "name": "Badge1"}}
        mock_request.return_value = mock_response

        response = self.client.get_badge("b1")
        self.assertEqual(response["data"]["name"], "Badge1")
        self.assert_request(
            mock_request, "GET", "https://api.events.ccc.de/congress/2025/v2/badges/b1/"
        )

    # --- iCal (since 40C3 / 2026) ---
    @patch("c3hub.requests.Session.request")
    def test_get_ical_events_returns_text(self, mock_request):
        mock_response = MagicMock()
        mock_response.text = "BEGIN:VCALENDAR\nEND:VCALENDAR"
        mock_request.return_value = mock_response

        response = self.client_2026.get_ical_events(params={"kind": "sos"})
        self.assertTrue(response.startswith("BEGIN:VCALENDAR"))
        mock_response.json.assert_not_called()
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2026/ical/events/",
            params={"kind": "sos"},
        )

    @patch("c3hub.requests.Session.request")
    def test_get_ical_event(self, mock_request):
        mock_response = MagicMock()
        mock_response.text = "BEGIN:VCALENDAR"
        mock_request.return_value = mock_response

        response = self.client_2026.get_ical_event("e1")
        self.assertEqual(response, "BEGIN:VCALENDAR")
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2026/ical/events/e1/",
        )

    @patch("c3hub.requests.Session.request")
    def test_get_ical_ping(self, mock_request):
        mock_response = MagicMock()
        mock_response.text = "pong"
        mock_request.return_value = mock_response

        response = self.client_2026.get_ical_ping()
        self.assertEqual(response, "pong")
        self.assert_request(
            mock_request, "GET", "https://api.events.ccc.de/congress/2026/ical/ping/"
        )

    @patch("c3hub.requests.Session.request")
    def test_get_favorites_ical_feed(self, mock_request):
        mock_response = MagicMock()
        mock_response.text = "BEGIN:VCALENDAR"
        mock_request.return_value = mock_response

        response = self.client_2026.get_favorites_ical_feed("alice", "secret123")
        self.assertEqual(response, "BEGIN:VCALENDAR")
        self.assert_request(
            mock_request,
            "GET",
            "https://api.events.ccc.de/congress/2026/ical/events/favorites/alice/secret123/",
        )

    @patch("c3hub.requests.Session.request")
    def test_hello(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = "pong"
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        response = self.client.hello()

        self.assertEqual(response, "pong")
        mock_request.assert_called_once_with(
            "GET",
            "https://api.events.ccc.de/congress/2025/v2/ping/",
            params=None,
            timeout=15,
        )


class TestEnvironmentHelpers(unittest.TestCase):
    """Tests for the module-level environment helpers."""

    def test_resolve_api_token_prefers_year_variable(self):
        with patch.dict(
            os.environ,
            {
                "C3HUB_API_TOKEN": "generic",
                "C3HUB_API_TOKEN_2025": "year",
                "C3HUB_API_TOKEN_39C3": "congress",
            },
        ):
            self.assertEqual(resolve_api_token(2025), "year")

    def test_resolve_api_token_congress_suffix(self):
        with patch.dict(
            os.environ,
            {
                "C3HUB_API_TOKEN": "generic",
                "C3HUB_API_TOKEN_39C3": "congress",
            },
        ):
            os.environ.pop("C3HUB_API_TOKEN_2025", None)
            self.assertEqual(resolve_api_token(2025), "congress")

    def test_resolve_api_token_generic_fallback(self):
        with patch.dict(os.environ, {"C3HUB_API_TOKEN": "generic"}):
            os.environ.pop("C3HUB_API_TOKEN_2026", None)
            os.environ.pop("C3HUB_API_TOKEN_40C3", None)
            self.assertEqual(resolve_api_token(2026), "generic")

    def test_default_year_from_env(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(default_year(), 2026)
        with patch.dict(os.environ, {"C3HUB_YEAR": "2025"}):
            self.assertEqual(default_year(), 2025)


if __name__ == "__main__":
    unittest.main()
