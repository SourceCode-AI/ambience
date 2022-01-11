import flask
import sqlalchemy as sa
from graphene import ObjectType, String, Schema, relay, Int, List
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField
from graphene_sqlalchemy.converter import convert_sqlalchemy_type

from aura.output import postgres as sql


class Detection(SQLAlchemyObjectType):
    class Meta:
        model = sql.DetectionModel
        interfaces = (relay.Node,)


class Scan(SQLAlchemyObjectType):
    class Meta:
        model = sql.ScanModel
        interfaces = (relay.Node, )


class Location(SQLAlchemyObjectType):
    class Meta:
        model = sql.ScanModel
        interfaces = (relay.Node, )


class Tags(SQLAlchemyObjectType):
    class Meta:
        model = sql.TagsModel
        interfaces = (relay.Node, )


class BehavioralIndicator(SQLAlchemyObjectType):
    class Meta:
        model = sql.BehavioralIndicator
        interfaces = (relay.Node,)


class Query(ObjectType):
    node = relay.Node.Field()
    echo = String(data=String(default_value="not data"))

    all_detections = SQLAlchemyConnectionField(Detection.connection)
    all_scans = SQLAlchemyConnectionField(Scan.connection)
    all_locations = SQLAlchemyConnectionField(Location.connection)
    all_tags = SQLAlchemyConnectionField(Tags.connection)
    all_behavioral_indicators = SQLAlchemyConnectionField(BehavioralIndicator.connection)

    all_detection_types = List(of_type=String)

    def resolve_echo(root, info, data: str="no data"):
        return f"Echo reply: {data}"

    def resolve_all_detection_types(root, info):
        values = []

        for row in flask.g.db_session.execute(sa.text("SELECT DISTINCT slug FROM detections ORDER BY slug DESC")).all():
            values.append(row[0])

        return values



@convert_sqlalchemy_type.register(sql.sa.INTEGER)
@convert_sqlalchemy_type.register(sql.sa.BIGINT)
@convert_sqlalchemy_type.register(sql.sa.SMALLINT)
def convert_sql_id(type, column, registry=None):
    return Int


schema = Schema(Query)
