"""Display the CDC assembly program for a given day."""

import argparse
import sys

import requests

from c3hub import C3HubClient, default_year, resolve_api_token
from schedule import (
    events_by_room,
    fetch_events,
    fetch_rooms,
    find_assembly,
    time_label,
)


def fetch_cdc_program(date_str, api_token=None, year=2026, out=None):
    """
    Fetch and print the CDC program for a given day.

    :param date_str: Target date in YYYY-MM-DD format.
    :param api_token: Optional API token. When omitted, the client resolves
                      it from the environment (see ``C3HubClient``).
    :param year: Congress year to query (default: 2026, i.e. 40C3).
    :param out: Output stream (default: sys.stdout). Can be used to
                capture the output, e.g. in the web interface.
    :raises ValueError: If the date is invalid or the CDC assembly/rooms
                        cannot be found.
    :raises requests.exceptions.HTTPError: If an API request fails.
    """
    out = out if out is not None else sys.stdout

    def log(message=""):
        print(message, file=out)

    client = C3HubClient(year=year, api_token=api_token)

    log("Fetching assemblies to find 'CDC'...")
    assembly = find_assembly(client, "CDC")
    assembly_id = assembly["id"]
    log(f"Found CDC assembly (ID: {assembly_id})")

    # Since 40C3 rooms come from the top-level /rooms/ endpoint (filtered by
    # assemblyID); the client handles that transparently.
    log("Fetching rooms for CDC...")
    rooms = fetch_rooms(client, assembly_id)
    log(f"Found {len(rooms)} spaces for {assembly.get('name', 'CDC')}.")
    for room in rooms:
        log(f"- {room.get('name')} (ID: {room['id']})")

    if not rooms:
        raise ValueError(
            f"No spaces were found for assembly '{assembly.get('name', 'CDC')}'."
        )

    log(f"Fetching events for {date_str}...")
    events = fetch_events(client, [room["id"] for room in rooms], date_str)
    program = events_by_room(rooms, events)

    log("\n" + "=" * 50)
    log(f"CDC Program for {date_str}")
    log("=" * 50)

    for room in rooms:
        name = room.get("name", "Unnamed Space")
        room_events = program[room["id"]]
        log(f"\n--- {name} ---")
        if not room_events:
            log("  No events scheduled.")
        else:
            for event in room_events:
                log(f"  [{time_label(event)}] {event.get('name', 'Unnamed Event')}")


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Display the CDC program for a given day."
    )
    parser.add_argument("date", help="The date to fetch the program for (YYYY-MM-DD)")
    parser.add_argument(
        "--year",
        type=int,
        default=default_year(),
        help="Congress year to query (default: 2026 / 40C3)",
    )
    args = parser.parse_args()

    if not resolve_api_token(args.year):
        print(
            "Warning: No C3HUB API token found in the environment. "
            "API calls might fail with 401 Unauthorized.",
            file=sys.stderr,
        )

    try:
        fetch_cdc_program(args.date, year=args.year)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"API Error: {e}", file=sys.stderr)
        if e.response is not None and e.response.status_code == 401:
            print(
                "Authentication failed. Please check your C3HUB API token settings.",
                file=sys.stderr,
            )
        sys.exit(1)


if __name__ == "__main__":
    main()
