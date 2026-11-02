"""Shared helpers to fetch and organize assembly schedules.

Used by the CDC program display (``cdc_program.py``) and the standalone
export CLI (``c3hub_cli.py``) so both behave identically (timezone,
pagination, error messages).
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

from dateutil import parser

# The congress takes place in Berlin; day boundaries must use this timezone,
# otherwise events in the first hours after midnight would be missed.
BERLIN = ZoneInfo("Europe/Berlin")


def find_assembly(client: Any, query: str) -> Dict[str, Any]:
    """Find an assembly by name, falling back to its (lowercase) slug.

    Slugs are case-sensitive, so the fallback query is lowercased; this
    keeps e.g. ``CDC`` working when the assembly's display name changed.

    Raises ``ValueError`` if no assembly matches.
    """
    assemblies = client.get_assemblies(params={"name": [query]}).get("data", [])
    if not assemblies:
        assemblies = client.get_assemblies(params={"slug": [query.lower()]}).get(
            "data", []
        )
    if not assemblies:
        raise ValueError(f"Could not find assembly: {query}")
    return assemblies[0]


def fetch_rooms(client: Any, assembly_id: str) -> List[Dict[str, Any]]:
    """Fetch the rooms of an assembly, skipping empty/invalid API entries."""
    rooms_data = client.get_assembly_rooms(assembly_id)
    return [room for room in rooms_data.get("data", []) if room]


def day_bounds(date_str: str) -> tuple:
    """Return the first and last second of the given day in Europe/Berlin.

    Raises ``ValueError`` if the date is not in YYYY-MM-DD format.
    """
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format '{date_str}'. Use YYYY-MM-DD.") from None

    start = datetime(target.year, target.month, target.day, tzinfo=BERLIN)
    return start, start + timedelta(days=1) - timedelta(seconds=1)


def fetch_events(
    client: Any, room_ids: Iterable[str], date_str: str
) -> List[Dict[str, Any]]:
    """Fetch all events of the given rooms for one day, following pagination."""
    start, end = day_bounds(date_str)
    params = {
        "roomID": list(room_ids),
        "startAfter": start.isoformat(),
        "startBefore": end.isoformat(),
        "pageSize": 100,
        "sortBy": "id",  # UUIDs, not chronological; sorting happens in memory
        "sortOrder": "asc",
    }
    return list(client.paginate("/events/", params=params))


def event_room_id(event: Dict[str, Any]) -> Optional[str]:
    """Return the room ID of an event, supporting both API field styles."""
    room_id = event.get("room_id")
    if not room_id and isinstance(event.get("room"), dict):
        room_id = event["room"].get("id")
    return room_id


def sort_events(events: List[Dict[str, Any]]) -> None:
    """Sort events by start time, with events without a start time last."""

    def start_time(event: Dict[str, Any]) -> datetime:
        start = event.get("schedule_start")
        if start:
            return parser.parse(start)
        return datetime.max.replace(tzinfo=BERLIN)

    events.sort(key=start_time)


def events_by_room(
    rooms: List[Dict[str, Any]], events: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Group events by room ID and sort each room's events by start time."""
    program = {room["id"]: [] for room in rooms}
    for event in events:
        room_id = event_room_id(event)
        if room_id in program:
            program[room_id].append(event)
    for room_events in program.values():
        sort_events(room_events)
    return program


def time_label(event: Dict[str, Any]) -> str:
    """Return the event start time as ``HH:MM``, or ``TBA`` if unknown."""
    start = event.get("schedule_start")
    if not start:
        return "TBA"
    return parser.parse(start).strftime("%H:%M")
