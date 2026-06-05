"""SQLite-safe migration for enhanced capital-flow metadata defaults."""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.database import Base, engine
from app import models  # noqa: F401

NEW_COLUMNS = {
    "capital_flow_confidence": "FLOAT NOT NULL DEFAULT 0.0",
    "capital_flow_reason": "TEXT",
    "capital_flow_is_real": "BOOLEAN NOT NULL DEFAULT 0",
    "capital_flow_is_estimated": "BOOLEAN NOT NULL DEFAULT 0",
}


def migrate() -> None:
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    if not settings.database_url.startswith("sqlite"):
        return
    db_path = settings.database_url.replace("sqlite:///", "", 1)
    conn = sqlite3.connect(db_path)
    try:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(enhanced_stock_scores)").fetchall()}
        for column, ddl in NEW_COLUMNS.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE enhanced_stock_scores ADD COLUMN {column} {ddl}")
        conn.execute("UPDATE enhanced_stock_scores SET capital_flow_source='not_verified', capital_flow_adjustment=0 WHERE capital_flow_source IN ('proxy','proxy_fallback','proxy_estimated')")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
    print("Capital-flow defaults migrated.")
