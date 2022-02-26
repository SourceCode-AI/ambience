"""
Blueprint for exposing Ambience scans as pypi package index

related peps:
- https://www.python.org/dev/peps/pep-0503/ -- Simple Repository API

"""
import itertools
import flask

from aura import package

from .sql import PackageModel, PackageDistribution, AuditResolution

bp = flask.Blueprint("pypi_mirror", __name__)



def get_allowed_packages() -> set[str]:
    stmt = """
    SELECT
        DISTINCT ON (packages.name)
        packages.name
    FROM package_dists
    JOIN packages ON packages.id = package_dists.package_id
    WHERE package_dists.audit = 'whitelist'
    ORDER BY packages.name DESC;
    """
    pkgs = set()

    for row in flask.g.db_session.execute(stmt):
        pkgs.add(row[0])

    return pkgs



@bp.route("/simple")
@bp.route("/simple/")
def simple_index():
    pkgs = get_allowed_packages()
    return flask.render_template("pypi_mirror/index.html", packages=pkgs)


@bp.route("/simple/<pkg_name>/")
def project_links(pkg_name):
    audit_pkg = PackageModel.from_name(pkg_name)

    if audit_pkg is None:
        return flask.abort(403)
    elif audit_pkg.audit == AuditResolution.blacklist:
        return flask.abort(403)

    audited_dists = PackageDistribution.from_package(audit_pkg)

    print(audited_dists)

    pkg = package.PypiPackage.from_cached(pkg_name)
    serial = pkg["last_serial"]
    dists = []

    for release in pkg["releases"].values():
        for dist in release:
            if any(audit.is_allowed(dist) for audit in audited_dists):
                dists.append(dist)

    return flask.render_template(
        "pypi_mirror/project.html",
        pkg=pkg,
        pkg_name=pkg_name,
        dists=dists,
        serial=serial
    )


@bp.route("/pypi/<pkg_name>/json")
def package_json(pkg_name):
    pkg = package.PypiPackage.from_cached(pkg_name)
    return flask.jsonify(pkg.info)
