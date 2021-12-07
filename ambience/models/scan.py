from importlib import resources
from base64 import b64encode

import flask
from aura.json_proxy import dumps

from .. import config


bp = flask.Blueprint("scan", __name__)


def get_scan(scan_id: int, conn=None) -> dict:
    conn = conn or config.get_db()

    with conn.cursor() as cur:
        cur.execute("SELECT scan_data, metadata FROM scans WHERE id=%s", (scan_id,))
        data = cur.fetchone()

        if data is None:
            return flask.abort(404)

        scan: dict = data[0]
        scan["metadata"] = data[1]
        scan.setdefault("detections", [])

        cur.execute("SELECT data FROM detections WHERE scan_id=%s", (scan_id,))

        scan["detections"] = list(x[0] for x in cur.fetchall())

    return scan


@bp.route("/api/v1.0/scans")
def list_scans_api():
    scans = []
    conn = config.get_db()

    with conn.cursor() as cur:
        cur.execute("SELECT id, input, reference FROM scans LIMIT 100")
        for row in cur.fetchall():
            scans.append({
                "id": row[0],
                "input": row[1],
                "reference": row[2]
            })

    return {"scans": scans}


@bp.route("/api/v1.0/scans/<int:scan_id>")
def get_scan_data(scan_id):
    return get_scan(scan_id)


@bp.route("/scans")
def list_scans():
    last_scans = []
    conn = config.get_db()

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, (scan_data->'name'), created
            FROM scans
            ORDER BY CREATED DESC
            LIMIT 250
        """)

        for row in cur.fetchall():
            last_scans.append({
                "id": row[0],
                "name": row[1],
                "created": row[2]
            })

    return flask.render_template("scans.html", last_scans=last_scans)


@bp.route("/scans/<int:scan_id>")
def show_scan(scan_id):
    return flask.render_template("scan.html", scan_id=scan_id)

@bp.route("/scans/<int:scan_id>/html")
def export_html_scan(scan_id):
    scan = {"scans":[get_scan(scan_id)]}
    scan_data = b64encode(dumps(scan).encode()).decode()
    app_js = resources.read_text("aura.data.html_results", "app.js")
    components_js = resources.read_text("aura.data.html_results", "components.js")
    aura_css = resources.read_text("aura.data.html_results", "aura.css")

    tpl = flask.current_app.jinja_env.from_string(
        resources.read_text("aura.data.html_results", "template.html")
    )

    js_renderer = components_js + "\n" + app_js

    return tpl.render(
        scan_data=scan_data,
        js_renderer=js_renderer,
        custom_css=aura_css
    )
