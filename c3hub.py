"""Python client for the C3 Hub API of the Chaos Communication Congress.

Designed for the current congress (40C3 / 2026) and supports backtesting
against older years (e.g. 39C3 / 2025) by passing ``year``.
"""

import os
import requests
from typing import Optional, Dict, Any, Iterator


class C3HubClient:
    """
    Client for interacting with the C3 Hub API.

    This client is designed to work with different congress years,
    defaulting to 2026 (40C3), but allows backtesting with data from 2025 (39C3).
    """

    DEFAULT_YEAR = 2026
    DEFAULT_TIMEOUT = 15  # seconds
    API_V3_FIRST_YEAR = 2026  # first year served by Hub API 3.0.0 (no /v2 prefix)

    def __init__(
        self,
        year: int = DEFAULT_YEAR,
        api_token: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the C3 Hub API client.

        :param year: The year of the congress (e.g., 2025, 2026).
        :param api_token: Optional API token for authentication.
                          Can be created in the user profile page.
                          When omitted, the token is looked up in the environment:
                          ``C3HUB_API_TOKEN_<YEAR>`` (e.g. ``C3HUB_API_TOKEN_2025``),
                          then ``C3HUB_API_TOKEN_<N>C3`` (e.g. ``C3HUB_API_TOKEN_39C3``),
                          then the generic ``C3HUB_API_TOKEN``.
        :param timeout: Timeout in seconds for every request (default: 15).
        """
        self.year = year
        self.timeout = timeout
        # Hub API 3.0.0 (40C3 / 2026) dropped the ``/v2`` path prefix without a
        # redirect; older years (e.g. 39C3 / 2025) are still served under ``/v2``.
        suffix = "" if self.year >= self.API_V3_FIRST_YEAR else "/v2"
        self.base_url = f"https://api.events.ccc.de/congress/{self.year}{suffix}"
        self.session = requests.Session()

        if api_token is None:
            api_token = resolve_api_token(year)

        if api_token:
            self.session.headers.update({"Authorization": f"Bearer {api_token}"})

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        parse_json: bool = True,
    ) -> Any:
        """
        Internal method to make HTTP requests to the API.

        :param parse_json: If False, the raw response text is returned
                           (used for the iCal endpoints).
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.request(
            method, url, params=params, timeout=self.timeout
        )
        response.raise_for_status()
        if not parse_json:
            return response.text
        return response.json()

    def paginate(self, endpoint: str, params: Optional[Dict] = None) -> Iterator[Any]:
        """
        Iterate over all items of a paginated list endpoint, following pages.

        Usage::

            for event in client.paginate('/events/', params={'kind': 'sos'}):
                ...

        Falls back to a single page if the response does not contain
        pagination information.
        """
        query = dict(params or {})
        page = int(query.get("page", 1))

        while True:
            query["page"] = page
            payload = self._request("GET", endpoint, params=query)
            items = payload.get("data") or []
            for item in items:
                yield item

            pagination = payload.get("pagination") or {}
            total = pagination.get("total")
            page_size = pagination.get("page_size") or len(items) or 1

            if not items or total is None or page * page_size >= total:
                return
            page += 1

    # --- Conference & Tracks ---
    def get_conference_info(self) -> Dict:
        """Get information about the conference."""
        return self._request("GET", "/conference/")

    def get_tracks(self, params: Optional[Dict] = None) -> Dict:
        """Get the list of conference tracks."""
        return self._request("GET", "/conference/tracks/", params=params)

    def get_track(self, track_id: str) -> Dict:
        """Get information about a specific track."""
        return self._request("GET", f"/conference/tracks/{track_id}/")

    # --- Assemblies ---
    def get_assemblies(self, params: Optional[Dict] = None) -> Dict:
        """Get the list of assemblies."""
        return self._request("GET", "/assemblies/", params=params)

    def get_assembly(self, assembly_id: str) -> Dict:
        """Get information about a specific assembly."""
        return self._request("GET", f"/assemblies/{assembly_id}/")

    def get_assembly_rooms(
        self, assembly_id: str, params: Optional[Dict] = None
    ) -> Dict:
        """
        Get the list of rooms of a specific assembly.

        Since 40C3 (2026) rooms are exposed through the top-level ``/rooms/``
        endpoint, filtered by ``assemblyID``. For older years (e.g. 39C3 /
        2025) the legacy ``/assemblies/{id}/rooms/`` endpoint is used.
        """
        if self.year >= 2026:
            merged = dict(params or {})
            merged["assemblyID"] = assembly_id
            return self._request("GET", "/rooms/", params=merged)
        return self._request("GET", f"/assemblies/{assembly_id}/rooms/", params=params)

    def get_assembly_room(self, assembly_id: str, room_id: str) -> Dict:
        """
        Get information about a specific room of a specific assembly.

        Since 40C3 (2026) rooms are exposed through the top-level
        ``/rooms/{room_id}/`` endpoint. For older years the legacy
        ``/assemblies/{assembly_id}/rooms/{room_id}/`` endpoint is used.
        """
        if self.year >= 2026:
            return self.get_room(room_id)
        return self._request("GET", f"/assemblies/{assembly_id}/rooms/{room_id}/")

    # --- Rooms (top-level, since 40C3 / 2026) ---
    def get_rooms(self, params: Optional[Dict] = None) -> Dict:
        """
        Get the list of rooms (available since 40C3 / 2026).

        Supports filters such as ``assemblyID``, ``roomType``,
        ``recordingState``, ``isOfficial``, ``tag``, ``name``.
        """
        return self._request("GET", "/rooms/", params=params)

    def get_room(self, room_id: str) -> Dict:
        """Get information about a specific room (available since 40C3 / 2026)."""
        return self._request("GET", f"/rooms/{room_id}/")

    # --- Events ---
    def get_events(self, params: Optional[Dict] = None) -> Dict:
        """
        Get the list of events (including talks and self-organized sessions).

        Since 40C3 the filters ``current=True`` and ``upcoming=True`` are
        available, e.g. useful for local displays.
        """
        return self._request("GET", "/events/", params=params)

    def get_event(self, event_id: str) -> Dict:
        """Get information about a specific event."""
        return self._request("GET", f"/events/{event_id}/")

    # --- Projects ---
    def get_projects(self, params: Optional[Dict] = None) -> Dict:
        """Get the list of projects."""
        return self._request("GET", "/projects/", params=params)

    def get_project(self, project_id: str) -> Dict:
        """Get information about a specific project."""
        return self._request("GET", f"/projects/{project_id}/")

    # --- Users ---
    def get_user(self, username: str) -> Dict:
        """
        Get information about a specific user.

        Since Hub API 3.0.0 (40C3 / 2026) users are addressed by username;
        for older years (e.g. 39C3 / 2025) pass the user's UUID instead.
        """
        return self._request("GET", f"/users/{username}")

    def get_me(self) -> Dict:
        """Get information about the currently authenticated user (since 40C3)."""
        return self._request("GET", "/auth/me/")

    def revoke_token(self) -> Any:
        """
        Revoke the API token used for this client (since Hub API 3.0.0).

        Only API tokens can be revoked this way, not sessions or OIDC tokens.
        """
        return self._request("POST", "/auth/revoke/")

    # --- Languages (since Hub API 3.0.0) ---
    def get_languages(self, params: Optional[Dict] = None) -> Dict:
        """Get the list of languages."""
        return self._request("GET", "/languages/", params=params)

    def get_language(self, tag: str) -> Dict:
        """Get information about a specific language by its tag."""
        return self._request("GET", f"/languages/{tag}/")

    # --- Badges ---
    def get_badges(self, params: Optional[Dict] = None) -> Dict:
        """Get the list of badges."""
        return self._request("GET", "/badges/", params=params)

    def get_badge(self, badge_id: str) -> Dict:
        """Get information about a specific badge."""
        return self._request("GET", f"/badges/{badge_id}/")

    # --- iCal feeds ---
    def get_ical_events(self, params: Optional[Dict] = None) -> str:
        """
        Get the iCal feed of events as raw text (text/calendar).

        Supports the same filters as the events endpoint (e.g. ``roomID``,
        ``assemblyID``, ``startAfter``, ``startBefore``).
        """
        return self._request("GET", "/ical/events/", params=params, parse_json=False)

    def get_ical_event(self, event_id: str) -> str:
        """Get the iCal entry for a single event as raw text (text/calendar)."""
        return self._request("GET", f"/ical/events/{event_id}/", parse_json=False)

    def get_ical_ping(self) -> str:
        """Ping the iCal API to check if it is up and running."""
        return self._request("GET", "/ical/ping/", parse_json=False)

    def get_favorites_ical_feed(self, username: str, ical_secret: str) -> str:
        """
        Get the public iCal feed of favorited events for a user.

        Since Hub API 3.0.0 (40C3 / 2026) the user is addressed by username;
        for older years pass the user's UUID.

        The feed is accessible without an API token via the user's
        ``ical_secret`` (see your Hub user profile).
        """
        return self._request(
            "GET", f"/ical/events/favorites/{username}/{ical_secret}/", parse_json=False
        )

    # --- Miscellaneous ---
    def ping(self) -> Any:
        """Ping the API to check if it is up and running."""
        return self._request("GET", "/ping/")

    def hello(self) -> Any:
        """Alias for ``ping()`` (the spec's operationId is ``apiv2_routers_ping_hello``)."""
        return self.ping()


def resolve_api_token(year: int) -> Optional[str]:
    """Resolve an API token for a congress year from the environment.

    Lookup order:

    1. ``C3HUB_API_TOKEN_<YEAR>`` (e.g. ``C3HUB_API_TOKEN_2026``)
    2. ``C3HUB_API_TOKEN_<N>C3`` (e.g. ``C3HUB_API_TOKEN_40C3``)
    3. the generic ``C3HUB_API_TOKEN``
    """
    return (
        os.environ.get(f"C3HUB_API_TOKEN_{year}")
        or os.environ.get(f"C3HUB_API_TOKEN_{year - 1986}C3")
        or os.environ.get("C3HUB_API_TOKEN")
    )


def default_year() -> int:
    """Return the congress year configured via ``C3HUB_YEAR`` (default: 2026)."""
    value = os.environ.get("C3HUB_YEAR")
    return int(value) if value else C3HubClient.DEFAULT_YEAR
