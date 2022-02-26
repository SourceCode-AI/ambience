import datetime

import flask
import sqlalchemy as sa

from aura.output import postgres as pg

from . import sql


bp = flask.Blueprint("audit", __name__)


VERDICTS = {
    "unknown": 1,
    "whitelist": 2,
    "blacklist": 3
}


def do_audit_scan(scan_id, verdict):
    if not flask.g.user:
        return flask.abort(403)
    elif not flask.g.user.is_admin:
        return flask.abort(403)

    scan = pg.ScanModel.query.get(scan_id)

    if not scan:
        return flask.abort(404)
    elif not scan.package:
        return flask.abort(404)

    pkg = sql.PackageModel.from_name(scan.package)

    if not pkg:
        pkg = sql.PackageModel(
            name = scan.package
        )
        flask.g.db_session.add(pkg)
        flask.g.db_session.commit()
    else:
        pkg = pkg

    pkg_dist = sql.PackageDistribution.query.filter(sql.PackageDistribution.filename == scan.pkg_filename).first()
    if not pkg_dist:
        pkg_dist = sql.PackageDistribution()
    else:
        pkg_dist = pkg_dist

    now = datetime.datetime.utcnow()
    pkg_dist.package_id = pkg.id
    pkg_dist.filename = scan.pkg_filename
    pkg_dist.audit = sql.AuditResolution(verdict)
    pkg_dist.md5 = scan.metadata_col.get("md5")
    pkg_dist.version = scan.package_release
    pkg_dist.audit_ts = now

    flask.g.db_session.add(pkg_dist)
    flask.g.db_session.commit()
    return {"package_distribution": pkg_dist.id, "package": pkg.id}


@bp.route("/api/v1.0/audit/scan_verdict", methods=["POST"])
def audit_scan_verdict_api():
    data = flask.request.json
    return do_audit_scan(data["scan_id"], data["verdict"])


@bp.route("/audit/scan/<int:scan_id>", methods=["GET", "POST"])
def audit_scan(scan_id):
    if flask.request.method == "POST":
        confirm = flask.request.form.get("confirm")
        if confirm != "on":
            return flask.abort(400)  # TODO

        verdict = flask.request.form["verdict"]
        if verdict not in VERDICTS:
            return flask.abort(400)  # TODO

        verdict = VERDICTS[verdict]
        resp = do_audit_scan(scan_id=scan_id, verdict=verdict)
        if resp:
            flask.flash("Audit verdict has been saved")
            return flask.redirect("/")
        else:
            return flask.abort(400)

    return flask.render_template("audit/scan.html", scan_id=scan_id)
