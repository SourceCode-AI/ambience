import flask
import sqlalchemy as sa

from aura.output import postgres as sql


bp = flask.Blueprint("api", __name__)

@bp.route("/api/v1.0/latest_scans")
def latest_scans_api():
    values = []

    stmt = sa.select(
        sql.ScanModel.scan_id, sql.ScanModel.input, sql.ScanModel.package
    ).order_by(sql.ScanModel.created.desc()).limit(5)

    for row in flask.g.db_session.execute(stmt):
        values.append(dict(zip(
            ("scan_id", "name", "package"), row
        )))

    return flask.jsonify(values)


@bp.route("/api/v1.0/stats")
def stats():
    data = {}

    data["scans"] = flask.g.db_session.query(sql.ScanModel).count()
    data["queue"] = flask.g.db_session.execute(sa.text("SELECT COUNT(*) FROM pending_scans WHERE status!=2")).first()[0]
    data["detections"] = flask.g.db_session.query(sql.DetectionModel).count()
    data["files"] = flask.g.db_session.query(
        sa.func.sum(sa.cast(sql.ScanModel.metadata_col["files_processed"], sa.INTEGER))
    ).first()[0] or 0
    data["size"] = flask.g.db_session.query(
        sa.func.sum(sa.cast(sql.ScanModel.metadata_col["data_processed"], sa.INTEGER))
    ).first()[0] or 0

    dsize = data['size']
    num_data = f"{dsize} b"

    for x in ("b", "Kb", "Mb", "Gb", "Tb", "Pb", "Eb"):
        if dsize > 1024:
            dsize /= 1024
        else:
            num_data = f"{dsize:.2f} {x}"
            break

    data["size_human"] = num_data

    return data


@bp.route("/api/v1.0/suspicious_packages")
def suspicious_packages():
    stmt = sa.text("""
        SELECT * FROM (
            SELECT DISTINCT ON (package) id, input, score, package
            FROM scans
            ORDER BY package, score DESC
        ) AS subq
        ORDER BY subq.score DESC
        LIMIT :limit;
    """)

    sus_pkgs = []
    for row in flask.g.db_session.execute(stmt, {"limit": 10}):
        sus_pkgs.append({
            "id": row[0],
            "name": row[1],
            "score": row[2],
            "package": row[3]
        })

    return flask.jsonify(sus_pkgs)


@bp.route("/api/v1.0/submit_scan")
def submit_scan():
    if not flask.g.user:
        return flask.abort(403)
    elif not flask.g.user.is_admin:
        return flask.abort(403)

    # TODO: add json schema and csrf protection
    uri = flask.request.args["uri"]
    scan = sql.PendingScans(uri=uri)
    flask.g.db_session.add(scan)
    flask.g.db_session.commit()

    return flask.redirect(flask.url_for("scan.queued_scan_view", scan_id=scan.queue_id))

