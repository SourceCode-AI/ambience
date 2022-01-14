from __future__ import annotations

import enum
import secrets
import hashlib

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


def init_data(engine=None):
    if engine is None:
        engine = pg.get_engine(config.CFG["postgres"])

    pg.Base.metadata.create_all(engine)
    Base.metadata.create_all(engine)
