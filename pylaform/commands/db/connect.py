import os
import shutil
import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def db(disable_cache=True) -> sqlite3.Connection:
    """
    Connects to the local database resource with improved settings to prevent caching issues.

    Args:
        disable_cache (bool): Whether to disable SQLite caching mechanisms. Default is True.

    Returns:
        sqlite3.Connection: DB connection session with cache optimizations.
    """
    path: str = os.path.abspath(os.curdir)
    db_path = os.path.join(path, "data/resume.db")

    # Check if database exists, if not create it
    if not os.path.exists(db_path):
        try:
            source_db = os.path.join(path, 'pylaform/resources/resume.db')
            logger.info(f"Database not found. Creating from template: {source_db}")
            shutil.copyfile(source_db, db_path)
        except Exception as e:
            raise RuntimeError(f"Do you have write permissions for the container? Error: {e}")

    # Log database information for troubleshooting
    logger.debug(f"Connecting to database at: {db_path}")
    logger.debug(f"Database exists: {os.path.exists(db_path)}")

    # Create connection with isolation_level=None for auto-commit mode
    connection = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)

    # Optimize connection to prevent caching issues
    if disable_cache:
        connection.execute("PRAGMA cache_size = 0")
        connection.execute("PRAGMA temp_store = MEMORY")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = OFF")

    return connection


def get_fresh_connection() -> sqlite3.Connection:
    """
    Get a guaranteed fresh database connection with no caching.
    Use this when you need to ensure you're seeing the latest database state.

    Returns:
        sqlite3.Connection: Fresh DB connection with cache disabled.
    """
    return db(disable_cache=True)