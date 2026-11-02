from c3hub import C3HubClient, default_year, resolve_api_token
import requests


def main():
    # Many endpoints in the Hub API require authentication. The client resolves
    # the token from the environment (C3HUB_API_TOKEN_<YEAR>, ..._<N>C3, generic).
    year = default_year()
    api_token = resolve_api_token(year)

    print("--- C3 Hub API Client Examples ---")
    print(f"Using API Token: {'Yes' if api_token else 'No'}")
    print(f"Congress year: {year}")

    client = C3HubClient(year=year)

    # 1. Ping the API to check if it's up
    try:
        print("\n1. Pinging the API:")
        response = client.ping()
        print(f"Ping response: {response}")
    except Exception as e:
        print(f"Failed to ping: {e}")

    # The following endpoints require authentication (API token).
    # We will try them, and handle unauthorized errors gracefully to show how they'd be used.

    # 2. Get Conference Info
    try:
        print("\n2. Fetching Conference Info:")
        conf_info = client.get_conference_info()
        print(f"Conference Title: {conf_info.get('data', {}).get('title', 'Unknown')}")
    except requests.exceptions.HTTPError as e:
        print(f"Could not fetch conference info (Auth required?): {e}")

    # 3. Get list of Tracks
    try:
        print("\n3. Fetching Tracks:")
        tracks = client.get_tracks(params={"pageSize": 3})
        for track in tracks.get("data", []):
            print(f"- Track: {track.get('name')}")
    except requests.exceptions.HTTPError as e:
        print(f"Could not fetch tracks: {e}")

    # 4. Get list of Assemblies
    try:
        print("\n4. Fetching Assemblies:")
        # Use pageSize to limit the number of results per page (max 100).
        assemblies = client.get_assemblies(params={"pageSize": 3})
        for assembly in assemblies.get("data", []):
            print(f"- Assembly: {assembly.get('name')} (Slug: {assembly.get('slug')})")
    except requests.exceptions.HTTPError as e:
        print(f"Could not fetch assemblies: {e}")

    # 5. Get list of Events
    try:
        print("\n5. Fetching Events:")
        events = client.get_events(params={"pageSize": 3})
        for event in events.get("data", []):
            print(f"- Event: {event.get('name')} (Kind: {event.get('kind')})")
    except requests.exceptions.HTTPError as e:
        print(f"Could not fetch events: {e}")

    # 6. Currently running / upcoming events (filters new in 40C3)
    try:
        print("\n6. Fetching Upcoming Events:")
        upcoming = client.get_events(params={"upcoming": True, "pageSize": 3})
        for event in upcoming.get("data", []):
            print(
                f"- Upcoming: {event.get('name')} (start: {event.get('schedule_start')})"
            )
    except requests.exceptions.HTTPError as e:
        print(f"Could not fetch upcoming events: {e}")

    # 7. Rooms (top-level endpoint since 40C3; replaces the old assembly rooms endpoint)
    try:
        print("\n7. Fetching Rooms:")
        rooms = client.get_rooms(params={"pageSize": 3})
        for room in rooms.get("data", []):
            print(
                f"- Room: {room.get('name')} (Type: {room.get('room_type')}, Assembly: {room.get('assembly_id')})"
            )
    except requests.exceptions.HTTPError as e:
        print(f"Could not fetch rooms: {e}")

    # 8. Get list of Projects
    try:
        print("\n8. Fetching Projects:")
        projects = client.get_projects(params={"pageSize": 3})
        for project in projects.get("data", []):
            print(f"- Project: {project.get('name')}")
    except requests.exceptions.HTTPError as e:
        print(f"Could not fetch projects: {e}")

    # 9. Get list of Badges
    try:
        print("\n9. Fetching Badges:")
        badges = client.get_badges(params={"pageSize": 3})
        for badge in badges.get("data", []):
            print(
                f"- Badge: {badge.get('name')} (Category: {badge.get('category', {}).get('name')})"
            )
    except requests.exceptions.HTTPError as e:
        print(f"Could not fetch badges: {e}")

    # 10. iCal: check the iCal API and fetch a feed snippet
    try:
        print("\n10. Pinging the iCal API:")
        print(f"iCal ping: {client.get_ical_ping()}")
    except requests.exceptions.HTTPError as e:
        print(f"Could not ping the iCal API: {e}")

    try:
        print("\n11. Fetching iCal feed for 'sos' events:")
        feed = client.get_ical_events(params={"kind": "sos"})
        print(f"Feed starts with: {feed[:60]!r}...")
    except requests.exceptions.HTTPError as e:
        print(f"Could not fetch iCal feed: {e}")

    # 12. Pagination helper: iterate over all pages of a list endpoint
    try:
        print("\n12. Iterating over the first events via paginate():")
        for i, event in enumerate(client.paginate("/events/", params={"pageSize": 5})):
            if i >= 5:
                break
            print(f"- Paged Event: {event.get('name')}")
    except requests.exceptions.HTTPError as e:
        print(f"Could not paginate events: {e}")

    # 13. Show the authenticated user (new endpoint in 40C3)
    try:
        print("\n13. Fetching authenticated user:")
        me = client.get_me()
        print(f"Me: {me.get('data', {}).get('display_name', 'Unknown')}")
    except requests.exceptions.HTTPError as e:
        print(f"Could not fetch user info: {e}")


if __name__ == "__main__":
    main()
