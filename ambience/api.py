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
