import os
from pathlib import Path
from typing import Optional

import ruamel.yaml
import psycopg2



CFG: Optional[dict] = None
CFG_PATH: Optional[Path] = None


def find_configuration() -> Path:
    pth = Path(os.environ.get("AMBIENCE_CFG", "ambience_config.yaml"))
    return pth

    # TODO
    if pth.is_absolute():
        return pth




def load_configuration():
    global CFG, CFG_PATH

    CFG_PATH = find_configuration()
    CFG = ruamel.yaml.safe_load(CFG_PATH.read_text())


def get_db():
    return psycopg2.connect(**CFG["postgres"])


load_configuration()
