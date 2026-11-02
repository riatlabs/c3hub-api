"""Standalone CLI to export assembly schedules as JSON or Markdown."""

import argparse
import json
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


def fetch_schedule_data(assembly_query, date_str, api_token=None, year=2026):
    """Fetch the schedule of an assembly for one day as structured data.

    :raises ValueError: If the date is invalid or the assembly/rooms
                        cannot be found.
    :raises requests.exceptions.HTTPError: If an API request fails.
    """
    client = C3HubClient(year=year, api_token=api_token)
    assembly = find_assembly(client, assembly_query)
    rooms = fetch_rooms(client, assembly["id"])

    if not rooms:
        raise ValueError(f"No spaces were found for assembly '{assembly_query}'.")

    events = fetch_events(client, [room["id"] for room in rooms], date_str)
    program = events_by_room(rooms, events)

    schedule = {}
    for room in rooms:
        schedule[room["name"]] = [
            {
                "id": event.get("id"),
                "name": event.get("name"),
                "schedule_start": event.get("schedule_start"),
            }
            for event in program[room["id"]]
        ]

    return {
        "assembly": assembly["name"],
        "date": date_str,
        "schedule": schedule,
    }


def format_markdown(data):
    """Render schedule data as a Markdown document."""
    lines = [f"# {data['assembly']} Program - {data['date']}", ""]
    for room_name, events in data["schedule"].items():
        lines.append(f"## {room_name}")
        if not events:
            lines.append("*No events scheduled.*")
        else:
            for event in events:
                lines.append(f"- **{time_label(event)}**: {event.get('name')}")
        lines.append("")
    return "\n".join(lines).strip()


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="C3 Hub CLI for E-Ink & Dynamic Displays"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command, help_text in (
        ("export-markdown", "Export schedule as Markdown"),
        ("to-json", "Export schedule as JSON"),
    ):
        subparser = subparsers.add_parser(command, help=help_text)
        subparser.add_argument(
            "--assembly", required=True, help="Name or slug of the assembly"
        )
        subparser.add_argument("--date", required=True, help="Date (YYYY-MM-DD)")
        subparser.add_argument(
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
        data = fetch_schedule_data(args.assembly, args.date, year=args.year)

        if args.command == "export-markdown":
            print(format_markdown(data))
        elif args.command == "to-json":
            print(json.dumps(data, indent=2))

    except requests.exceptions.HTTPError as e:
        print(f"API Error: {e}", file=sys.stderr)
        if e.response is not None and e.response.status_code == 401:
            print(
                "Authentication failed. Please check your C3HUB API token settings.",
                file=sys.stderr,
            )
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
