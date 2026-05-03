import json
import logging
import os
from contextlib import closing

import database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STATS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "stats.json")


def migrate() -> None:
    if not os.path.exists(STATS_FILE):
        logger.info("No stats.json found. Skipping migration.")
        return

    logger.info("Found stats.json. Initializing database...")
    database.init_db()

    try:
        with open(STATS_FILE, 'r') as f:
            data = json.load(f)

        history = data.get('history', [])
        offset = data.get('offset', 0)

        if 'count' in data and 'history' not in data:
            offset = data['count']
            history = []

        logger.info("Migrating %d logs and offset %d...", len(history), offset)

        database.set_offset(offset)

        with closing(database.get_db_connection()) as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM logs')
            count = cursor.fetchone()[0]

            if count == 0:
                for timestamp in history:
                    cursor.execute('INSERT INTO logs (timestamp) VALUES (?)', (timestamp,))
                conn.commit()
                logger.info("Migration complete.")
            else:
                logger.info("Database not empty. Skipping history migration to avoid duplicates.")

        os.rename(STATS_FILE, STATS_FILE + ".bak")
        logger.info("Renamed stats.json to stats.json.bak")

    except (OSError, json.JSONDecodeError, ValueError) as e:
        logger.error("Migration failed: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    migrate()
