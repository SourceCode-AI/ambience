import flask
import time
import string
import xmlrpc.client

import sqlalchemy as sa
from psycopg2.errors import SyntaxError

from .. import config


bp = flask.Blueprint("search", __name__)



@bp.route("/search")
def search():
    return flask.render_template("search.html")


@bp.route("/api/v1.0/search/detections", methods=["GET", "POST"])
def search_detections_api():
    query = normalize_query(flask.request.args["q"])
    detections = []
    conn = config.get_db()

    try:
        with conn.cursor() as cur:
            start = time.monotonic()

            cur.execute("""
                SELECT detections.scan_id, (scans.scan_data->'name'), detections.data
                FROM detections
                INNER JOIN scans ON scans.id=detections.scan_id
                WHERE idx_vector @@ to_tsquery('english', %s)
                ORDER BY detections.score DESC
                LIMIT 250;
            """, (query,))

            for row in cur.fetchall():
                detections.append({
                    "scan_id": row[0],
                    "scan_name": row[1],
                    "detection": row[2]
                })

            end = time.monotonic()

        print(f"Search completed in {(end-start):.4f}s")  # FIXME: convert to logger
        return {"detections": detections, "count": len(detections)}
    except SyntaxError as exc:
        print(exc.args)

        if "syntax error in tsquery" in exc.args[0]:
            return {"error": "There is a syntax error in your search query"}
        else:
            return {"error": "An error occured while searching the database"}


@bp.route("/api/v1.0/search/filepaths", methods=["GET", "POST"])
def search_filepaths_api():
    query = normalize_query(flask.request.args["q"])
    filepaths = []
    conn = config.get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT locations.name, locations.scan_id, locations.metadata, (scans.scan_data->'name')
                FROM locations
                INNER JOIN scans ON scans.id=locations.scan_id
                WHERE idx_path @@ to_tsquery('english', %s)
                LIMIT 250;
            """, (query,))
            for row in cur:
                filepaths.append({
                    "name": row[0],
                    "scan_id": row[1],
                    "metadata": row[2],
                    "scan_name": row[3]
                })

        return {"filepaths": filepaths, "count": len(filepaths)}
    except SyntaxError as exc:
        if "syntax error in tsquery" in exc.args[0]:
            return {"error": "There is a syntax error in your search query"}
        else:
            return {"error": "An error occured while searching the database"}


@bp.route("/api/v1.0/search/packages", methods=["GET", "POST"])
def search_packages_api():  # FIXME: xmlrpc is not working and disabled on pypi
    query = flask.request.args["q"]
    repo = xmlrpc.client.ServerProxy("https://pypi.python.org/pypi", use_builtin_types=True)
    results = list(repo.search({"name": query}))

    return {"packages": results}


@bp.route("/api/v1.0/search/md5", methods=["GET", "POST"])
def search_md5_api():
    query = normalize_query(flask.request.args["q"])
    results = []

    rows = flask.g.db_session.execute(sa.text("""
    SELECT id, scan_id, name
    FROM locations
    WHERE (metadata->>'md5') = :md5
    """), {"md5": query}).all()

    for row in rows:
        results.append({
            "type": "location",
            "id": row[0],
            "scan_id": row[1],
            "label": row[2]
        })

    return {"results": results, "count": len(results)}


def normalize_query(query: str) -> str:
    if all(x in string.ascii_letters + string.digits + " " for x in query) and " " in query:
        return f"'{query}'"
    query = query.replace('"', "'")
    return query
