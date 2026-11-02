import os
from io import StringIO
from flask import Flask, request, jsonify, render_template_string
from c3hub import C3HubClient, default_year
from cdc_program import fetch_cdc_program

app = Flask(__name__)


def get_year():
    """Congress year to query, configurable via C3HUB_YEAR (default: 2026 / 40C3)."""
    return default_year()


# Basic HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>C3 Hub Client Web</title>
    <style>
        body { font-family: sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: auto; }
        pre { background: #eee; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>C3 Hub Client</h1>

        <h2>CDC Program</h2>
        <form method="GET" action="/cdc_program">
            <label for="date">Date (YYYY-MM-DD):</label>
            <input type="text" id="date" name="date" placeholder="YYYY-MM-DD" required>
            <button type="submit">View Program</button>
        </form>

        {% if cdc_output is not none %}
            <h3>Program Output</h3>
            <pre>{{ cdc_output }}</pre>
        {% endif %}

        <h2>API Status</h2>
        <p>Ping: <span id="ping-status">{{ ping_status }}</span></p>
    </div>
</body>
</html>
"""


def get_ping_status():
    client = C3HubClient(year=get_year())
    try:
        return client.ping()
    except Exception as e:
        return f"Error: {e}"


@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE, ping_status=get_ping_status(), cdc_output=None
    )


@app.route("/cdc_program")
def web_cdc_program():
    date_str = request.args.get("date")
    if not date_str:
        return index()

    # Capture the output of fetch_cdc_program using an explicit output
    # stream (thread-safe, unlike redirecting sys.stdout). The client
    # resolves the API token from the environment itself.
    captured_output = StringIO()
    try:
        fetch_cdc_program(date_str, year=get_year(), out=captured_output)
    except (ValueError, SystemExit) as e:
        print(f"Error: {e}", file=captured_output)
    except Exception as e:
        print(f"Error executing fetch_cdc_program: {e}", file=captured_output)

    return render_template_string(
        HTML_TEMPLATE,
        ping_status=get_ping_status(),
        cdc_output=captured_output.getvalue(),
    )


@app.route("/api/ping")
def api_ping():
    client = C3HubClient(year=get_year())
    try:
        return jsonify({"status": "success", "data": client.ping()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def main():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
