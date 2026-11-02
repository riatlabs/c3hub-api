# C3 Hub API Client

This repository provides a Python client and examples for interacting with the **C3 Hub API**, useful for extracting information for local displays during Congress. It targets the current congress (**40C3 / 2026**) and supports backtesting with data from earlier years (e.g. 39C3 / 2025).

## What is the C3 Hub?

The Hub is the central place for getting information about content at the Chaos Communication Congress (C3). It aggregates:
- **Events**: From all the stages, art & music events, and self-organized sessions (SoS) into a "Fahrplan" (schedule).
- **Assemblies**: Self-organized groups of people showing their projects and setting up workshops/rooms.
- **Projects**: Connects people with interests or showcases something.
- **Badges**: Virtual awards managed and awarded by assemblies.
- **Wiki & Bulletin Board**: Places to share knowledge, find ride-sharing options, or start projects with like-minded people.

The Hub mainly consists of two parts:
1. **The UI**: Centered around your profile and the contents of the Congress.
2. **The Backoffice**: Used to create and manage entries like assemblies and projects.

*Information sourced from the [C3 Hub HowTo](https://events.ccc.de/congress/2025/infos/hub-howto.html)*

## API Documentation Reference

- **Current (40C3 / 2026):** https://api.events.ccc.de/congress/2026/docs
- **OpenAPI spec (40C3):** https://api.events.ccc.de/congress/2026/openapi.json (also included in this repository as `openapi.json`, v3.0.0)
- **Backtesting (39C3 / 2025):** https://api.events.ccc.de/congress/2025/v2/docs

## Entities and Categorization

The API exposes several entities. Here's how to understand and filter them:

*   **Assemblies**: Self-organized groups.
    *   **Habitats**: These are essentially large assemblies that group other assemblies. You can filter them by setting `hierarchy='cluster'`. Other assemblies might have a `parent_id` pointing to a habitat.
    *   **States**: Assemblies go through different states: `planned`, `registered`, `hidden`, `accepted`, `rejected`, `placed`, `arrived`, `confirmed`. Public assemblies are typically limited to `accepted`, `placed`, `arrived`, `confirmed`.
    *   **Rooms**: Rooms are exposed through the top-level `rooms` endpoint (since 40C3). Each room is optionally linked to an assembly via `assembly_id`.

*   **Events**: Sessions, talks, and workshops.
    *   **Kinds**: Events are categorized by their nature: `official` (official tracks), `assembly` (organized by assemblies), `sos` (self-organized sessions), `lightning` (lightning talks). The attribute on the event object is called `kind`.
    *   **Filtering**: You can filter events by `assemblyID`, `roomID`, `trackID`, and `language`. Since 40C3 there are also `current=True` and `upcoming=True` filters, which are handy for local displays.
    *   **Tags**: Events (and other entities) can be tagged. You can filter by one or multiple tags (e.g., `tag=['security', 'hardware']`).

*   **Badges**: Virtual awards given out by assemblies.
    *   **Categories**: Badges belong to categories. You can filter them by category slug (e.g., `category=['assembly']`).
    *   **Visibility**: Badges have visibility settings like `public`, `private`, `friends`, `club`.

*   **Projects**: Connect people with interests or showcase something. Can be linked to an `assembly_id`.

*   **Users**: Participants. They have profiles, statuses, and badges.

## Getting Started

### Prerequisites

You'll need Python 3.9+ and the `requests` library.

```bash
pip install -r requirements.txt
```

### Authentication

Most of the Hub API endpoints require authentication. You can create an API token in your user profile page on the Hub.
Pass this token when initializing the client, or export it to the environment — either generically as `C3HUB_API_TOKEN`
or year-specific as `C3HUB_API_TOKEN_<YEAR>` (e.g. `C3HUB_API_TOKEN_2025`) or `C3HUB_API_TOKEN_<N>C3`
(e.g. `C3HUB_API_TOKEN_39C3`). Year-specific variables take precedence over the generic one.

Since Hub API 3.0.0 (40C3) API tokens carry scopes. For the read-only endpoints of this client the scopes `read_public`
and `read_private` are enough; `get_me()` additionally reports the `username` only with the `profile` scope (and the user
`id` with `openid`), and favorites need `read_favorites`. `get_user()` only returns users with a public profile, and passing
a UUID for 2026 is rejected with HTTP 400 (use the username).

```bash
export C3HUB_API_TOKEN="your_40c3_token_here"       # default year (2026)
export C3HUB_API_TOKEN_39C3="your_39c3_token_here"  # used for year=2025
```

Public endpoints that work without a token: `ping`, `ical/ping` and (as observed live for 40C3) the iCal feeds themselves.

The client performs this lookup automatically; the CLI tools, examples and web UI therefore only need the variables to be exported — no token has to be passed explicitly.

### Configuration

| Environment variable | Meaning | Default |
| --- | --- | --- |
| `C3HUB_API_TOKEN` | API token for authenticated requests | *(none)* |
| `C3HUB_API_TOKEN_<YEAR>` / `_<N>C3` | Year-specific token, takes precedence over `C3HUB_API_TOKEN` | *(none)* |
| `C3HUB_YEAR` | Congress year to query | `2026` (40C3) |
| `PORT` | Port of the Flask web interface | `5000` |

## Using the API Client

The provided `c3hub.py` module defines a `C3HubClient` class. By default, it initializes for the 2026 congress (40C3); pass `year=2025` for backtesting with 39C3 data.

### Initialization

```python
from c3hub import C3HubClient

# Initialize for 40C3 (2026); without an API token only public endpoints work
client = C3HubClient(year=2026)

# Initialize with an API token and a custom request timeout (seconds)
client_auth = C3HubClient(year=2026, api_token="YOUR_API_TOKEN", timeout=10)
```

### Querying and Filtering Examples

You can pass query parameters (like filtering or pagination) to list endpoints using the `params` dictionary. Use `pageSize` to control the number of objects per page (max 100, default 25):

```python
# Fetch only 5 assemblies per page
assemblies = client.get_assemblies(params={'pageSize': 5})

# Fetch Habitats (clusters of assemblies)
habitats = client.get_assemblies(params={'hierarchy': 'cluster'})

# Fetch arrived assemblies
arrived_assemblies = client.get_assemblies(params={'state': 'arrived'})

# Fetch self-organized sessions (SOS) that are tagged 'hacking'
sos_events = client.get_events(params={'kind': 'sos', 'tag': ['hacking']})

# Fetch currently running / upcoming events (since 40C3)
current = client.get_events(params={'current': True})
upcoming = client.get_events(params={'upcoming': True})

# Fetch all rooms of an assembly (40C3: uses the top-level /rooms/ endpoint)
rooms = client.get_assembly_rooms(assembly_id)

# Fetch badges from a specific category
assembly_badges = client.get_badges(params={'category': ['assembly']})

# Iterate over all items of a paginated endpoint, following pages automatically
for event in client.paginate('/events/', params={'kind': 'sos'}):
    print(event['name'])

# Fetch the iCal feed of events as raw text (text/calendar)
feed = client.get_ical_events(params={'kind': 'sos'})

# Public iCal feed of your favorited events (ical_secret from your profile)
feed = client.get_favorites_ical_feed(username, ical_secret)
```

### Available Methods

- **Conference Info**: `get_conference_info()`
- **Tracks**: `get_tracks()`, `get_track(track_id)`
- **Assemblies**: `get_assemblies()`, `get_assembly(assembly_id)`, `get_assembly_rooms(assembly_id)`, `get_assembly_room(assembly_id, room_id)`
- **Rooms (40C3)**: `get_rooms()`, `get_room(room_id)`
- **Events**: `get_events()`, `get_event(event_id)`
- **Projects**: `get_projects()`, `get_project(project_id)`
- **Users**: `get_user(username)`, `get_me()`, `revoke_token()` (since 40C3)
- **Languages (40C3)**: `get_languages()`, `get_language(tag)`
- **Badges**: `get_badges()`, `get_badge(badge_id)`
- **iCal (40C3)**: `get_ical_events()`, `get_ical_event(event_id)`, `get_ical_ping()`, `get_favorites_ical_feed(username, ical_secret)`
- **Pagination**: `paginate(endpoint, params)` — generator over all pages
- **Ping**: `ping()`

Run the examples with:

```bash
python3 examples.py
```

## Changes in Hub API 3.0.0 (40C3, 2026-10-27)

- **No more `/v2`:** the API for 2026 lives at `https://api.events.ccc.de/congress/2026/...` (no redirect from `/v2`). The client picks the right base URL per year; 2025 backtesting still uses `/v2`.
- **Users by username instead of UUID:** `get_user()` and `get_favorites_ical_feed()` take a username for 2026 (UUID for 2025). Message and event-participant payloads are keyed by username too.
- **New OIDC `sub`:** OIDC clients must re-link existing users (not relevant for this client).
- **API token scopes** can be set when creating a token in your Hub profile; `revoke_token()` revokes the token in use. New `/languages/` endpoints.

## Changes in 40C3 (v2.1.0)

- **Rooms moved:** `/assemblies/{id}/rooms/` was removed; rooms now live under the top-level `/rooms/` and `/rooms/{room_id}/` endpoints (filter by `assemblyID`). `C3HubClient.get_assembly_rooms()` handles this transparently and still works for 39C3 (2025) backtesting.
- **New iCal feeds:** `/ical/events/`, `/ical/events/{id}/`, `/ical/ping/` and a public favorites feed `/ical/events/favorites/{username}/{ical_secret}/`.
- **New event filters:** `current` and `upcoming`.
- **New endpoints:** `/auth/me/`, `/metanav/`, `/messages/` (send/read/delete), badge award/redeem/token management, favorites (POST/DELETE `/…/favorite/`), import/export under `/io/`.
- **New fields:** `favorited` on events/assemblies/projects, `links` on assemblies, `assembly_id`/`room_type`/`recording_state`/`capacity` on rooms.
- Response format (`data` + `pagination`) and authentication (Bearer token) are unchanged.

The client currently covers the read-side used for schedules and displays. Interactive features (sending messages, awarding badges, toggling favorites) can be added to the client if needed.

## Running the Web Interface

A lightweight Flask web server is also provided to serve information directly to a browser. This is particularly useful for local displays during the congress.

1. Install the additional dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the web server:
   ```bash
   python3 web.py
   ```
3. Open your browser and navigate to `http://localhost:5000/`. You can view the API status and use a form to fetch and display the CDC program directly in the browser window.

## Running the CDC Program Script

The `cdc_program.py` script prints the CDC assembly's program (Triangle and Square space) for a given day. Day boundaries are computed in the congress timezone (Europe/Berlin).

```bash
export C3HUB_API_TOKEN="your_token_here"
python3 cdc_program.py 2026-12-27            # 40C3 (default)
python3 cdc_program.py 2025-12-28 --year 2025  # backtesting 39C3
```

## Testing and Local Development

We recommend using a Python virtual environment (`venv`) to keep dependencies isolated when testing or developing locally.

### 1. Set up a Virtual Environment

Navigate to the repository folder and create a virtual environment named `venv`:

```bash
python3 -m venv venv
```

Activate the virtual environment:
- On **Linux/macOS**:
  ```bash
  source venv/bin/activate
  ```
- On **Windows**:
  ```cmd
  venv\Scripts\activate
  ```

### 2. Install Dependencies

With the virtual environment activated, install the required packages:

```bash
pip install -r requirements.txt
```

### 3. Run the Automated Tests

The repository includes a comprehensive automated test suite that uses mock API responses (meaning you don't need a real API token to run them). The tests cover the API client logic, the CDC program script, and the Flask web server.

To run all tests, use the standard `unittest` module:

```bash
python3 -m unittest test_c3hub.py test_cdc_program.py test_web.py
```

If everything is working correctly, you should see an `OK` message at the end of the output indicating all tests passed. Since the tests are fully mocked, they cannot detect changes to the live API — for a quick live check, run:

```bash
python3 -c "from c3hub import C3HubClient; print(C3HubClient().ping())"
```

When you are finished working, you can deactivate the virtual environment by simply running:

```bash
deactivate
```

## Important Links & Resources

Below is a collection of useful online resources extracted from the original CCC documentation related to the Hub and the Congress:

*   **Hub HowTo Documentation**: [What is the Hub?](https://events.ccc.de/congress/2025/infos/hub-howto.html)
*   **Official Hub Web Interface**: [C3 Hub 2025](https://events.ccc.de/congress/2025/hub/)
*   **Official API Documentation**: [Hubs API v2 Docs](https://api.events.ccc.de/congress/2025/v2/docs)
*   **Hub Backoffice**: [Maschinenraum](https://events.ccc.de/congress/2025/hub/backoffice)
*   **Hub Git Repository**: [git.cccv.de/hub/hub](https://git.cccv.de/hub/hub)
*   **Congress 2025 Homepage**: [events.ccc.de](https://events.ccc.de/congress/2025/infos/index.html)

## Standalone CLI Tool

A bash wrapper and CLI tool are provided to easily export program and schedule data for dynamic e-ink or web conference displays. The tool supports exporting schedule data into `JSON` or `Markdown` formatting.

To use the tool, run `./c3hub` followed by the subcommand (`export-markdown` or `to-json`) along with the target assembly name and date. The congress year defaults to 2026 (40C3); pass `--year 2025` for backtesting against 39C3 data.

**Export to JSON (for dynamic JS displays):**
```bash
./c3hub to-json --assembly CDC --date 2026-12-27 > cdc_display.json
```

**Export to Markdown (for E-ink generation or READMEs):**
```bash
./c3hub export-markdown --assembly cdc --date 2026-12-27 > cdc_display.md

# Backtesting against 39C3 (uses C3HUB_API_TOKEN_39C3 automatically)
./c3hub export-markdown --assembly cdc --date 2025-12-28 --year 2025 > cdc_39c3.md
```

*Note: The `./c3hub` wrapper will automatically source your `venv` if it exists, so you can just run it seamlessly from the root folder.*
