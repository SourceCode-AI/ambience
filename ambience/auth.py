import hashlib

import flask
import sqlalchemy as sa

from .models import sql


bp = flask.Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if flask.request.method == "POST":
        username = flask.request.form["email"]
        user_obj = flask.g.db_session.query(sql.UserModel).filter_by(email=username).first()

        if user_obj:
            password = flask.request.form["password"]
            check = hashlib.sha256((user_obj.salt + password).encode()).hexdigest() == user_obj.passwd

            if check:
                flask.session["user"] = user_obj.id
                return flask.redirect("/")

        flask.flash("Username or password is invalid")

    return flask.render_template("login.html")


@bp.route("/logout")
def logout():
    if "user" in flask.session:
        del flask.session["user"]

    return flask.redirect("/")
