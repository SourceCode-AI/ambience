from importlib import resources
from dataclasses import dataclass
import secrets
import time
import typing as t

import flask
from flask_graphql import GraphQLView
import sqlalchemy as sa

from aura.config import get_logger
from aura.output import postgres as sql

from .models import scan, search, pypi, sql as sql_models
from .models.graphql.schema import schema as graphql_schema
from . import api
from . import auth
from . import config



AURA_STATIC_WHITELIST = (
    "aura.data.html_results.components.js",
)
logger = get_logger(__name__)

engine = sql.get_engine(config.CFG["postgres"])
db_session = sql.get_session(engine)
sql.Base.query = db_session.query_property()


app = flask.Flask(__name__)
app.secret_key = config.CFG["flask_secret"]

app.register_blueprint(scan.bp)
app.register_blueprint(search.bp)
app.register_blueprint(pypi.bp)
app.register_blueprint(api.bp)
app.register_blueprint(auth.bp)


@dataclass
class MenuItem:
    endpoint: str
    menu_id : str
    text: str
    icon: t.Optional[str] = None

    @property
    def href(self) -> str:
        if "/" in self.endpoint:
            return self.endpoint
        else:
            return flask.url_for(self.endpoint)

    def __eq__(self, other: str) -> bool:
        return other == self.menu_id


@app.route("/")
def home():
    return flask.render_template("home.html")


@app.route("/aura_static/<fname>")
def aura_static(fname):
    if fname not in AURA_STATIC_WHITELIST:
        return flask.abort(404)

    mod_name, fname, ext = fname.rsplit(".", 2)

    with resources.path(mod_name, f"{fname}.{ext}") as pth:
        return flask.send_from_directory(str(pth.parent), pth.name)



app.add_url_rule(
    "/graphql",
    view_func=GraphQLView.as_view(
        "graphql",
        schema=graphql_schema,
        graphiql=True
    )
)


@app.before_request
def before_request():
    flask.g.start = time.monotonic()
    flask.g.engine = engine
    flask.g.db_session = db_session

    if "user" in flask.session:
        flask.g.user = db_session.query(sql_models.UserModel).filter_by(id=flask.session["user"]).first()
    else:
        flask.g.user = None



@app.teardown_request
def teardown_request(exception=None):
    if not flask.request.path.startswith("/static"):
        diff = time.monotonic() - flask.g.start
        print(f"Request '{flask.request.path}' took {diff:.4f}s")


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


MENU_ITEMS = (
    MenuItem(endpoint="/", menu_id="index", text="Home", icon="fa-home"),
    MenuItem(endpoint="scan.list_scans", menu_id="list_scans", text="Browse scans", icon="fa-list-alt"),
    MenuItem(endpoint="search.search", menu_id="search", text="Search", icon="fa-search"),
    MenuItem(endpoint="pypi.list_packages", menu_id="list_packages", text="Pypi packages", icon="fa-boxes"),
)


@app.context_processor
def inject_menu_items():
    return {"menu_items": MENU_ITEMS}
