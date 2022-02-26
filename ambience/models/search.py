import flask
import time
import string
import xmlrpc.client

import sqlalchemy as sa
from psycopg2.errors import SyntaxError

from .. import config


bp = flask.Blueprint("search", __name__)


class SearchError(RuntimeError):
    pass


def search_detections(query):
    query = normalize_query(query)
    detections = []
    conn = config.get_db()

    try:
        with conn.cursor() as cur:
            start = time.monotonic()
            cur.execute("""
                    SELECT * FROM (
                        SELECT
                            distinct on (detections.score, scans.package, detections.slug)
                            detections.scan_id as scan_id, (scans.scan_data->'name') as name, detections.data as data, detections.score as score
                        FROM detections
                        INNER JOIN scans ON scans.id=detections.scan_id
                        WHERE idx_vector @@ to_tsquery('english', %s)
                        ORDER BY detections.score, scans.package, detections.slug DESC
                    ) AS subq
                    ORDER BY subq.score DESC
                    LIMIT 100
                """, (query,))

            for row in cur.fetchall():
                detections.append({
                    "scan_id": row[0],
                    "scan_name": row[1],
                    "detection": row[2]
                })
            end = time.monotonic()
        return detections
    except SyntaxError as exc:
        if "syntax error in tsquery" in exc.args[0]:
            raise SearchError("There is a syntax error in your search query") from exc
        else:
            raise SearchError("An error occured while searching the database") from exc


def search_filepaths(query):
    query = normalize_query(query)
    filepaths = []
    conn = config.get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM (
                    SELECT
                        DISTINCT ON (scans.package)
                        locations.name, locations.scan_id, locations.metadata, (scans.scan_data->'name'), scans.score as score
                    FROM locations
                    INNER JOIN scans ON scans.id=locations.scan_id
                    WHERE idx_path @@ to_tsquery('english', %s)
                    ORDER BY scans.package
                ) AS subq
                ORDER BY subq.score DESC
                LIMIT 100
                """, (query,))
            for row in cur:
                filepaths.append({
                    "name": row[0],
                    "scan_id": row[1],
                    "metadata": row[2],
                    "scan_name": row[3]
                })

        return filepaths
    except SyntaxError as exc:
        if "syntax error in tsquery" in exc.args[0]:
            raise SearchError("There is a syntax error in your search query")
        else:
            raise SearchError("An error occured while searching the database")



@bp.route("/search")
def search():
    return flask.render_template("search.html")


@bp.route("/api/v1.0/search", methods=["GET", "POST"])
def search_all():
    query = flask.request.args["q"]
    try:
        detections = search_detections(query)
        filepaths = search_filepaths(query)
        return {"detections": detections, "filepaths": filepaths}
    except SearchError as exc:
        return {"error": exc.args[0]}


@bp.route("/api/v1.0/search/detections", methods=["GET", "POST"])
def search_detections_api():
    try:
        detections = search_detections(flask.request.args["q"])
        return {"detections": detections, "count": len(detections)}
    except SearchError as exc:
        return {"error": exc.args[0]}


@bp.route("/api/v1.0/search/filepaths", methods=["GET", "POST"])
def search_filepaths_api():
    try:
        filepaths = search_filepaths(flask.request.args["q"])
        return {"filepaths": filepaths, "count": len(filepaths)}
    except SearchError as exc:
        return {"error": exc.args[0]}


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
