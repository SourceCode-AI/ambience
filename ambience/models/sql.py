from __future__ import annotations

import enum
import secrets
import hashlib
import datetime
import typing as t

import sqlalchemy as sa
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

from aura.output import postgres as pg

from .. import config


Base = declarative_base()

# TODO: ambience specific models

class UserType(enum.Enum):
    user = 1
    admin = 2


class AuditResolution(enum.Enum):
    unknown = 1
    whitelist = 2
    blacklist = 3


class UserModel(Base):
    __tablename__ = "users"

    id = sa.Column(sa.BIGINT, primary_key=True)
    username = sa.Column(sa.VARCHAR(32), unique=True)
    email = sa.Column(sa.VARCHAR(255), unique=True)
    salt = sa.Column(sa.CHAR(32), nullable=False)
    passwd = sa.Column(sa.CHAR(64), nullable=False)
    acc_type = sa.Column(sa.Enum(UserType), default=UserType.user, nullable=False)

    @classmethod
    def create_new_user(cls, email, passwd) -> UserModel:
        salt = secrets.token_hex(16)
        hashed_passwd = hashlib.sha256((salt + passwd).encode()).hexdigest()
        return UserModel(
            email=email,
            salt=salt,
            passwd=hashed_passwd
        )

    @hybrid_property
    def is_admin(self) -> bool:
        return self.acc_type == UserType.admin

    def check_password(self, passwd) -> bool:
        return hashlib.sha256((self.salt + passwd)).hexdigest() == self.passwd


class PackageModel(Base):
    __tablename__ = "packages"

    id = sa.Column(sa.BIGINT, primary_key=True)
    name = sa.Column(sa.VARCHAR(255), nullable=False, unique=True)
    downloads = sa.Column(sa.BIGINT, nullable=True)
    updated = sa.Column(sa.TIMESTAMP, default=datetime.datetime.utcnow)
    audit = sa.Column(sa.Enum(AuditResolution), default=AuditResolution.unknown, nullable=False)
    audit_ts = sa.Column(sa.TIMESTAMP, default=datetime.datetime.utcnow)

    @classmethod
    def from_name(cls, name: str) -> PackageModel:
        pkg = PackageModel.query.filter(PackageModel.name == name).first()
        return pkg


class PackageDistribution(Base):
    __tablename__ = "package_dists"

    id = sa.Column(sa.BIGINT, primary_key=True)
    package_id = sa.Column(sa.BIGINT, sa.ForeignKey("packages.id"), nullable=False)
    updated = sa.Column(sa.TIMESTAMP, default=datetime.datetime.utcnow)
    audit = sa.Column(sa.Enum(AuditResolution), default=AuditResolution.unknown, nullable=False)
    audit_ts = sa.Column(sa.TIMESTAMP, default=datetime.datetime.utcnow)
    md5 = sa.Column(sa.CHAR(32), nullable=True)
    filename = sa.Column(sa.VARCHAR(512), nullable=False)
    version = sa.Column(sa.VARCHAR(128), nullable=False)

    @classmethod
    def from_package(cls, pkg: PackageModel) -> t.Iterable[PackageDistribution]:
        return tuple(PackageDistribution.query.filter(PackageDistribution.package_id == pkg.id).all())

    def is_allowed(self, release: dict) -> bool:
        if self.audit == AuditResolution.blacklist:
            return False
        elif self.md5 and self.md5 != release.get("digests", {}).get("md5"):
            return False

        if self.filename != release.get("filename"):
            return False

        return True


sa.event.listen(
    PackageDistribution.__table__,
    "after_create",
    sa.DDL("""
    CREATE MATERIALIZED VIEW ambience_stats AS
    (
        SELECT
               'files' as label,
               SUM((scans.metadata->'files_processed')::bigint) as value
        FROM scans
    ) UNION (
        SELECT
               'size' as label,
               SUM((scans.metadata->'data_processed')::bigint) as value
        FROM scans
    ) UNION (
        SELECT
               'scans' as label,
               COUNT(*) as value
        FROM scans
    ) UNION (
        SELECT
            'queue' as label,
            COUNT(*) as value
        FROM pending_scans
        WHERE status < 2
    ) UNION (
        SELECT
            'detections' as label,
            COUNT(*) as value
        FROM detections
    );
    """)
)

sa.event.listen(
    PackageDistribution.__table__,
    "after_create",
    sa.DDL("CREATE UNIQUE INDEX stats_idx ON ambience_stats(label DESC);")
)

sa.event.listen(
    PackageDistribution.__table__,
    "after_create",
    sa.DDL("SELECT cron.schedule('*/5 * * * *', $$REFRESH MATERIALIZED VIEW ambience_stats$$);")
)

sa.event.listen(
    PackageDistribution.__table__,
    "after_create",
    sa.DDL("""
    SELECT cron.schedule(
        '0 0 * * *',
        $$DELETE FROM cron.job_run_details WHERE end_time < now() – interval '7 days'$$
    );
    """)
)



def init_data(engine=None):
    if engine is None:
        engine = pg.get_engine(config.CFG["postgres"])

    pg.Base.metadata.create_all(engine)
    Base.metadata.create_all(engine)
