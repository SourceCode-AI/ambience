"""
Blueprint for exposing Ambience scans as pypi package index

related peps:
- https://www.python.org/dev/peps/pep-0503/ -- Simple Repository API

"""
import flask

from aura import package

bp = flask.Blueprint("pypi_mirror", __name__)


@bp.route("/simple")
@bp.route("/simple/")
def simple_index():
    pkgs = ["wheel", "django", "flask"]
    return flask.render_template("pypi_mirror/index.html", packages=pkgs)


@bp.route("/simple/<pkg_name>/")
def project_links(pkg_name):
    pkg = package.PypiPackage.from_cached(pkg_name)
    return flask.render_template("pypi_mirror/project.html", pkg=pkg)


@bp.route("/pypi/<pkg_name>/json")
def package_json(pkg_name):
    pkg = package.PypiPackage.from_cached(pkg_name)
    return flask.jsonify(pkg.info)
