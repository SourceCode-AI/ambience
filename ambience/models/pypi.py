import flask
from packaging.utils import canonicalize_name  # TODO: add to dependencies
import sqlalchemy as sa
from sqlalchemy.orm import load_only
from sqlalchemy.dialects.postgresql import JSONB

from aura import package
from aura.output import postgres as sql

from .. import config


bp = flask.Blueprint("pypi", __name__)


@bp.route("/packages")
def list_packages():
    return flask.render_template("list_packages.html")


@bp.route("/packages/filter", methods=["GET", "POST"])
def filter_packages():
    # TODO: add json schema validation
    results = []
    q = flask.request.get_json() or {}

    print(q)

    scan_ids = None
    filter_scans = False

    stmt = sa.select(sql.ScanModel).join(sql.ScanModel.tags)
    stmt = stmt.options(load_only("id", "input", "scan_score", "metadata_col"))\
            .where(sql.ScanModel.metadata_col["uri_scheme"] == sa.cast("pypi", JSONB))\
            .group_by(sql.ScanModel.id)

    if (tags:=q.get("tags")):
        rows = flask.g.db_session.execute("""
        SELECT scan_tags.scan_id
        FROM scan_tags
        JOIN tags t on scan_tags.tag_id = t.id
        GROUP BY (scan_tags.scan_id)
        HAVING array_agg(t.tag)::varchar(255)[] @> (:tags)::varchar(255)[]  -- Does the left array contain right array?
        """, {"tags": tags})
        filtered_ids = {x[0] for x in rows}
        filter_scans = True
        if scan_ids is None:
            scan_ids = filtered_ids
        else:
            scan_ids &= filtered_ids

    if (detections:=q.get("detection_types")):
        rows = flask.g.db_session.execute("""
        SELECT detections.scan_id
        FROM detections
        GROUP BY (detections.scan_id)
        HAVING array_agg(detections.slug)::varchar(255)[] @> (:detections)::varchar(255)[]
        """, {"detections": detections})
        filtered_ids = {x[0] for x in rows}
        filter_scans = True
        if scan_ids is None:
            scan_ids = filtered_ids
        else:
            scan_ids &= filtered_ids

    if indicators:=q.get("indicators"):
        indicators = list(map(int, indicators))

        rows = flask.g.db_session.execute("""
        SELECT scan_indicators.scan_id
        FROM scan_indicators
        GROUP BY (scan_indicators.scan_id)
        HAVING array_agg(scan_indicators.indicator_id)::bigint[] @> (:indicators)::bigint[]
        """, {"indicators": indicators})
        filtered_ids = {x[0] for x in rows}
        filter_scans = True
        if scan_ids is None:
            scan_ids = filtered_ids
        else:
            scan_ids &= filtered_ids

    stmt = stmt.limit(100).order_by(sql.ScanModel.scan_score.desc())

    if filter_scans:
        print(f"Filtered ids: {scan_ids}")
        stmt = stmt.filter(sql.ScanModel.id.in_(list(scan_ids)))

    print(stmt)

    for row in flask.g.db_session.execute(stmt).scalars().all():
        results.append({
            "id": row.id,
            "name": row.input,
            "tags": [x.tag for x in row.tags],
            "package": row.metadata_col["package_name"],
            "release": row.metadata_col["package_release"],
            "score": row.scan_score
        })

    return flask.jsonify({"packages": results, "count": len(results)})



@bp.route("/project/<pkg_name>")
@bp.route("/project/<pkg_name>/<release>")
def view_package(pkg_name: str, release: str = "latest"):
    pkg_name = canonicalize_name(pkg_name)
    conn = config.get_db()

    pkg = package.PypiPackage.from_cached(pkg_name)
    ctx = {
        "package_name": pkg_name,
        "pkg": pkg,
        "latest": pkg.info["info"]["version"],
        "reverse_dependencies": package.get_reverse_dependencies(pkg_name),
        "score_matrix": pkg.score,
        "total_score": sum(int(x) for x in pkg.score.get_score_entries()),
        "active_tab": flask.request.args.get("active_tab", "Overview")
    }

    releases = [{"release": x} for x in pkg.info["releases"].keys()]
    releases.sort(key=package.sort_by_version, reverse=True)
    ctx["releases"] = [x["release"] for x in releases]

    if release == "latest":
        release = ctx["latest"]

    ctx["release"] = release
    ctx["scans"] = {}
    ctx["release_scores"] = {}

    with conn.cursor() as cur:
        cur.execute("""
        SELECT id, scan_data, metadata, pkg_filename
        FROM scans
        WHERE package=%s AND package_release=%s AND pkg_filename IS NOT NULL
        """, (pkg_name, release))

        for row in cur:
            scan = {
                "scan_id": row[0],
                "data": row[1],
                "metadata": row[2]
            }
            ctx["scans"][row[3]] = scan

        cur.execute("""
        SELECT package_release, MAX((scan_data->'score')::int)
        FROM scans
        WHERE package_release IS NOT NULL AND package=%s
        GROUP BY package_release;
        """, (pkg_name,))

        for row in cur:
            ctx["release_scores"][row[0]] = row[1]


    return flask.render_template("pypi_package.html", **ctx)
