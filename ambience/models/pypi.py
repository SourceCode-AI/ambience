import flask
from packaging.utils import canonicalize_name  # TODO: add to dependencies

from aura import package

from .. import config


bp = flask.Blueprint("pypi", __name__)


@bp.route("/project/<pkg_name>")
@bp.route("/project/<pkg_name>/<release>")
def view_package(pkg_name: str, release: str = "latest"):
    pkg_name = canonicalize_name(pkg_name)
    conn = config.get_db()

    pkg = package.PypiPackage.from_cached(pkg_name)
    ctx = {
        "package_name": pkg_name,
        "pkg": pkg,
        "latest": pkg.info["info"]["version"]
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
