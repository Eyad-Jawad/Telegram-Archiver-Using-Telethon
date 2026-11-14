from pathlib import Path

from eralchemy2 import render_er

from . import Base
from .models import *

DB_IMAGE_PATH = Path(__file__).parent.parent / "SQL_schemas.svg"


def generate_db_image():
    render_er(Base, str(DB_IMAGE_PATH))


if __name__ == "__main__":
    generate_db_image()
