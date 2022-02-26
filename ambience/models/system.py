import datetime

import flask
import sqlalchemy as sa

bp = flask.Blueprint("system", __name__)


def get_cron_jobs():
    if not flask.g.user:
        return flask.abort(403)
    elif not flask.g.user.is_admin:
        return flask.abort(403)

    jobs = []
    stmt = """
    SELECT jobid, schedule, command, active
    FROM cron.job
    ORDER BY jobid
    """

    for row in flask.g.db_session.execute(sa.text(stmt)):
        jobs.append({
            "jobid": row[0],
            "schedule": row[1],
            "command": row[2],
            "active": row[3],
        })

    return jobs


@bp.route("/api/v1.0/system/cron_log")
def system_cron_log_api():
    if not flask.g.user:
        return flask.abort(403)
    elif not flask.g.user.is_admin:
        return flask.abort(403)

    job_log = []

    stmt = """
    SELECT jobid, runid, command, status, start_time, end_time 
    FROM cron.job_run_details
    ORDER BY start_time DESC
    LIMIT 100
    """

    for row in flask.g.db_session.execute(stmt):
        job_log.append({
            "jobid": row[0],
            "runid": row[1],
            "command": row[2],
            "status": row[3],
            "start_time": row[4],
            "end_time": row[5]
        })

    return flask.jsonify(job_log)


@bp.route("/api/v1.0/system/running_scans")
def system_running_scans_api():
    if not flask.g.user:
        return flask.abort(403)
    elif not flask.g.user.is_admin:
        return flask.abort(403)

    now = datetime.datetime.utcnow()
    scans = []
    stmt = "SELECT queue_id, updated, uri FROM pending_scans WHERE status=1 ORDER BY updated DESC"

    for row in flask.g.db_session.execute(stmt):
        scans.append({
            "queue_id": row[0],
            "updated": row[1],
            "uri": row[2],
            "runtime": (now - row[1]).seconds
        })

    return flask.jsonify(scans)



@bp.route("/system/cron")
def system_cron():
    if not flask.g.user:
        return flask.abort(403)
    elif not flask.g.user.is_admin:
        return flask.abort(403)

    return flask.render_template(
        "system/cron.html",
        cron_jobs=get_cron_jobs()
    )


@bp.route("/system/queue")
def system_queue():
    if not flask.g.user:
        return flask.abort(403)
    elif not flask.g.user.is_admin:
        return flask.abort(403)

    return flask.render_template("system/queue.html")
