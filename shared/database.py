"""One SQLite location shared by account, restaurant, and meal modules."""

import os
from pathlib import Path

from dotenv import load_dotenv
import sqlalchemy as db

load_dotenv()
DATABASE_PATH = Path(os.getenv("PREPRN_DATABASE_PATH") or Path(__file__).resolve().parents[1] / "preprn.db").expanduser().resolve()
engine = db.create_engine(db.URL.create("sqlite", database=str(DATABASE_PATH)))
