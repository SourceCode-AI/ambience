from importlib import resources

import flask

from .models import scan, search, pypi
from . import config


AURA_STATIC_WHITELIST = (
    "aura.data.html_results.components.js",
)


app = flask.Flask(__name__)
app.register_blueprint(scan.bp)
app.register_blueprint(search.bp)
app.register_blueprint(pypi.bp)


@app.route("/")
def home():
    last_scans = []
    conn = config.get_db()

    with conn.cursor() as cur:
        cur.execute("SELECT id, input FROM scans ORDER BY created DESC LIMIT 25")
        for row in cur.fetchall():
            last_scans.append({"id": row[0], "name": row[1]})

        cur.execute("SELECT COUNT(*) FROM scans")
        num_scans = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM pending_scans WHERE status!=2")
        num_queue = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM detections")
        num_detections = cur.fetchone()[0]

        cur.execute("SELECT SUM((metadata->'files_processed')::int) FROM scans;")
        num_files = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM((metadata->'data_processed')::int) FROM scans;")
        data_size = cur.fetchone()[0] or 0

        num_data = f"{data_size} b"

        for x in ("b", "Kb", "Mb", "Gb", "Tb", "Pb", "Eb"):
            if data_size > 1024:
                data_size /= 1024
            else:
                num_data = f"{data_size:.2f} {x}"
                break

        cur.execute("SELECT id, input, (scan_data->'score') as score from scans ORDER BY score DESC LIMIT 10;")
        suspicious_pkgs = cur.fetchall()

    stat_cards = (
        (num_scans, "Scans"),
        (num_queue, "Scans in a queue"),
        (num_detections, "Detections"),
        (num_files, "Files scanned"),
        (num_data, "Data processed")
    )


    return flask.render_template(
        "home.html",
        last_scans=last_scans,
        stat_cards=stat_cards,
        suspicious_pkgs=suspicious_pkgs,
    )


@app.route("/aura_static/<fname>")
def aura_static(fname):
    if fname not in AURA_STATIC_WHITELIST:
        return flask.abort(404)

    mod_name, fname, ext = fname.rsplit(".", 2)

    with resources.path(mod_name, f"{fname}.{ext}") as pth:
        return flask.send_from_directory(str(pth.parent), pth.name)
