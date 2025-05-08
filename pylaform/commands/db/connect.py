import os
import shutil
import sqlite3
import logging
import time
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def db(disable_cache=True, read_only=False) -> sqlite3.Connection:
    """
    Connects to the local database with journal mode set to DELETE instead of WAL.

    Args:
        disable_cache (bool): Whether to disable SQLite caching. Default is True.
        read_only (bool): Whether to open in read-only mode. Default is False.

    Returns:
        sqlite3.Connection: Database connection
    """
    path = os.path.abspath(os.curdir)
    db_path = os.path.join(path, "data/resume.db")
    db_dir = os.path.dirname(db_path)

    # Ensure the data directory exists
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        try:
            os.chmod(db_dir, 0o777)  # Full permissions
        except Exception as e:
            logger.warning(f"Could not set directory permissions: {e}")

    # Create database from template if it doesn't exist
    if not os.path.exists(db_path):
        try:
            source_db = os.path.join(path, 'pylaform/resources/resume.db')
            logger.info(f"Database not found. Creating from template: {source_db}")
            shutil.copyfile(source_db, db_path)
            try:
                os.chmod(db_path, 0o666)  # Make writable
            except Exception as e:
                logger.warning(f"Could not set file permissions: {e}")
        except Exception as e:
            logger.error(f"Could not create database: {e}")
            if not read_only:
                logger.warning("Falling back to read-only mode")
                read_only = True

    # Check for WAL files and remove them
    wal_files = [db_path + "-shm", db_path + "-wal"]
    for wal_file in wal_files:
        if os.path.exists(wal_file):
            try:
                os.remove(wal_file)
                logger.info(f"Removed WAL file: {wal_file}")
            except Exception as e:
                logger.warning(f"Could not remove WAL file: {e}")

    # Connect to database
    try:
        if read_only:
            # Use URI mode for read-only connection
            uri = f"file:{db_path}?mode=ro"
            logger.info("Opening database in READ-ONLY mode")
            conn = sqlite3.connect(uri, uri=True, timeout=30.0, check_same_thread=False)
        else:
            # Use normal connection for read-write
            conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)

            # Set pragmas to ensure DELETE journal mode
            try:
                # Force DELETE journal mode instead of WAL
                conn.execute("PRAGMA journal_mode = DELETE")
                conn.execute("PRAGMA synchronous = NORMAL")
                conn.execute("PRAGMA foreign_keys = ON")
                conn.commit()  # Commit these settings immediately

                # Verify journal mode
                cursor = conn.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]
                logger.info(f"Database journal mode: {journal_mode}")

                # If we get WAL mode despite our settings, try one more time with explicit reset
                if journal_mode.upper() == "WAL":
                    logger.warning("Database is still in WAL mode, attempting to reset")
                    conn.close()

                    # Connect with URI parameter to force a specific journal mode
                    uri = f"file:{db_path}?journal_mode=delete"
                    conn = sqlite3.connect(uri, uri=True, timeout=30.0, check_same_thread=False)
                    conn.execute("PRAGMA synchronous = NORMAL")
                    conn.execute("PRAGMA foreign_keys = ON")
                    conn.commit()
            except sqlite3.OperationalError as e:
                logger.error(f"Failed to set PRAGMA settings: {e}")
                # If we can't set pragmas, database might be read-only
                conn.close()
                return db(disable_cache, read_only=True)

        return conn
    except sqlite3.OperationalError as e:
        logger.error(f"Failed to connect to database: {e}")
        if not read_only and "readonly database" in str(e):
            logger.warning("Database is read-only, retrying in read-only mode")
            return db(disable_cache, read_only=True)
        raise


def get_fresh_connection(read_only=False) -> sqlite3.Connection:
    """
    Get a fresh database connection.

    Args:
        read_only (bool): Whether to use read-only mode

    Returns:
        sqlite3.Connection: Database connection
    """
    return db(disable_cache=True, read_only=read_only)


@contextmanager
def transaction_context(read_only=False):
    """
    Context manager for database transactions.

    Args:
        read_only (bool): Whether to use read-only mode

    Yields:
        sqlite3.Connection: Database connection
    """
    conn = None
    try:
        conn = get_fresh_connection(read_only=read_only)
        if not read_only:
            conn.execute("BEGIN TRANSACTION")
        yield conn
        if not read_only:
            conn.execute("COMMIT")
    except Exception as e:
        if conn and not read_only:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass  # Ignore rollback errors
        raise
    finally:
        if conn:
            conn.close()