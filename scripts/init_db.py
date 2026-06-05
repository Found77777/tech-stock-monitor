"""Initialize local SQLite database tables."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import Base, engine
from app import models  # noqa: F401

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    from scripts.migrate_capital_flow_defaults import migrate as migrate_capital_flow_defaults
    migrate_capital_flow_defaults()
    print("Database initialized.")
