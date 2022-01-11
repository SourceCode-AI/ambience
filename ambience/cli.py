import getpass

import click

from aura.output import postgres as pg

from . import config
from .models import sql as sql_models


@click.group()
def cli():
    pass


@cli.command()
def init():
    sql_models.init_data()


@cli.command()
def add_user():
    username = input("Username/email: ")
    passwd = getpass.getpass("Password: ")

    user_obj = sql_models.UserModel.create_new_user(username, passwd)
    session = pg.get_session(config.CFG["postgres"])
    session.add(user_obj)
    session.commit()


if __name__ == "__main__":
    cli()
