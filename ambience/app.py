from importlib import resources
from dataclasses import dataclass
import time
import typing as t

import flask
from flask_graphql import GraphQLView
import sqlalchemy as sa
from sqlalchemy.orm import scoped_session, sessionmaker

from aura.config import get_logger
from aura.output import postgres as sql

from .models import scan, search, pypi
from .models.graphql.schema import schema as graphql_schema
from . import api
from . import config



AURA_STATIC_WHITELIST = (
    "aura.data.html_results.components.js",
)
logger = get_logger(__name__)

engine = sql.create_engine(config.CFG["postgres"])
db_session = scoped_session(sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
))
sql.Base.query = db_session.query_property()


app = flask.Flask(__name__)
app.register_blueprint(scan.bp)
app.register_blueprint(search.bp)
app.register_blueprint(pypi.bp)
app.register_blueprint(api.bp)


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
    sus_pkgs_stmt = sa.text("""
        SELECT * FROM (
            SELECT DISTINCT ON (package) id, input, score, package
            FROM scans
            ORDER BY package, score DESC
        ) AS subq
        ORDER BY subq.score DESC
        LIMIT :limit;
    """)


    suspicious_pkgs = []
    for row in db_session.execute(sus_pkgs_stmt, {"limit": 10}):
        suspicious_pkgs.append({
            "id": row[0],
            "name": row[1],
            "score": row[2],
            "package": row[3]
        })


    num_scans = db_session.query(sql.ScanModel).count()
    num_queue = db_session.execute(sa.text("SELECT COUNT(*) FROM pending_scans WHERE status!=2")).first()[0]
    num_detections = db_session.query(sql.DetectionModel).count()
    num_files = db_session.query(
        sa.func.sum(sa.cast(sql.ScanModel.metadata_col["files_processed"], sa.INTEGER))
    ).first()[0] or 0
    data_size = db_session.query(
        sa.func.sum(sa.cast(sql.ScanModel.metadata_col["data_processed"], sa.INTEGER))
    ).first()[0] or 0

    num_data = f"{data_size} b"

    for x in ("b", "Kb", "Mb", "Gb", "Tb", "Pb", "Eb"):
        if data_size > 1024:
            data_size /= 1024
        else:
            num_data = f"{data_size:.2f} {x}"
            break

    stat_cards = (
        (num_scans, "Scans"),
        (num_queue, "Scans in a queue"),
        (num_detections, "Detections"),
        (num_files, "Files scanned"),
        (num_data, "Data processed")
    )


    return flask.render_template(
        "home.html",
        stat_cards=stat_cards,
        suspicious_pkgs=suspicious_pkgs,
    )


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
    MenuItem(endpoint="/graphql", menu_id="graphql", text="GraphQL API", icon="fa-project-diagram")
)


@app.context_processor
def inject_menu_items():
    return {"menu_items": MENU_ITEMS}
