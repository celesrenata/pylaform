from sqlite3 import Connection, Cursor, DatabaseError, ProgrammingError

from tenacity import retry, stop_after_delay

from . import connect


class Deletes:
    """
    Collection of queries to run against the local database.
    Actions: DELETE FROM
    :return None: None
    """
    
    @retry(stop=(stop_after_delay(10)))
    def __init__(self) -> None:
        self.conn: Connection = connect.db()
        self.cursor: Cursor = self.conn.cursor()

    @retry(stop=(stop_after_delay(10)))
    def single_association(self, associated_id: str, associated_table: str, target_table: str) -> None:
        """
        Dynamically find a resource and delete its association.
        :param str associated_id: Find target by associated ID.
        :param str associated_table: Associated table.
        :param str target_table: Target table.
        :return None: None
        """
        if "new" not in associated_id:
            try:
                find_target = self.cursor.execute(
                    f"""
                    SELECT `name`
                    FROM {associated_table}
                    WHERE `id` = {int(associated_id)};
                    """)
            except (DatabaseError, ProgrammingError):
                find_target = self.cursor.execute(
                    f"""
                        SELECT `{associated_table}`
                        FROM {associated_table}
                        WHERE `id` = {int(associated_id)};
                    """)

                # If no other associations to target.
            if len(find_target.fetchall()) <= 1:
                self.cursor.execute(
                    f"""
                    DELETE FROM {target_table}
                    WHERE `id` = {int(associated_id)};
                    """)

            # Delete association
            self.cursor.execute(
                f"""
                DELETE FROM {associated_table}
                WHERE `id` = {int(associated_id)};
                """)

            # Commit changes.
            self.conn.commit()
        return

    @retry(stop=(stop_after_delay(10)))
    def row(self, target_table: str, target_id: int) -> None:
        """
        Deletes a row from the specified table with the given ID.

        :param target_table: The table to delete from
        :param target_id: The ID of the row to delete
        :return: None
        """
        self.cursor.execute(
            f"""
            DELETE FROM {target_table}
            WHERE `id` = ?
            """, (target_id,)
        )

        # Commit changes
        self.conn.commit()

        return None

    @retry(stop=(stop_after_delay(10)))
    def delete_target(self, target_id: str, target_table: str) -> None:
        """
        Deletes target.
        :param str target_id: Target ID to find and delete.
        :param str target_table: Target table.
        :return None: None
        """

        if "new" not in target_id:
            self.cursor.execute(
                f"""
                DELETE FROM {target_table}
                WHERE `id` = {int(target_id)};
                """)

            # Commit changes.
            self.conn.commit()

        return

    @retry(stop=(stop_after_delay(10)))
    def delete_entry(self, table, entry_id, hard_delete=True):
        """
        Delete an entry from the database.

        :param str table: Table name to delete from
        :param int entry_id: ID of the entry to delete
        :param bool hard_delete: If True, permanently delete; if False, mark as disabled
        :return: True if successful, False otherwise
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Validate the entry exists
            self.cursor.execute(f"SELECT * FROM {table} WHERE id = ?", (entry_id,))
            if not self.cursor.fetchone():
                logger.warning(f"Entry {entry_id} not found in {table}")
                return False

            if hard_delete:
                # First, check for dependencies if there are foreign key relationships
                foreign_keys = self._check_dependencies(table, entry_id)

                if foreign_keys:
                    logger.warning(f"Entry {entry_id} in {table} has dependencies: {foreign_keys}")
                    # If there are dependencies, soft delete instead
                    self.cursor.execute(f"UPDATE {table} SET state = 0 WHERE id = ?", (entry_id,))
                else:
                    # Hard delete if no dependencies
                    self.cursor.execute(f"DELETE FROM {table} WHERE id = ?", (entry_id,))
            else:
                # Soft delete - just update state to 0
                self.cursor.execute(f"UPDATE {table} SET state = 0 WHERE id = ?", (entry_id,))

            self.conn.commit()
            return True

        except Exception as e:
            logger.error(f"Error deleting entry {entry_id} from {table}: {e}")
            return False

    @retry(stop=(stop_after_delay(10)))
    def _check_dependencies(self, table, entry_id):
        """
        Check if an entry has dependent records in other tables

        :param str table: Table name
        :param int entry_id: ID of the entry to check
        :return: List of tables with dependencies
        """
        import sqlite3

        # Define known relationships
        relationships = {
            "school": ["focus", "achievement"],
            "employer": ["position", "achievement"],
            "position": ["achievement"],
            # Add other relationships as needed
        }

        if table not in relationships:
            return []

        dependent_tables = []

        for related_table in relationships.get(table, []):
            try:
                # For each related table, check if it references this entry
                self.cursor.execute(
                    f"SELECT COUNT(*) FROM {related_table} WHERE {table} = ?",
                    (entry_id,)
                )
                count = self.cursor.fetchone()[0]

                if count > 0:
                    dependent_tables.append(f"{related_table} ({count})")
            except sqlite3.Error:
                # If the column doesn't exist in this table, skip it
                pass

        return dependent_tables

    @retry(stop=(stop_after_delay(10)))
    def cleanup_disabled_entries(self, tables=None):
        """
        Automatically clean up disabled entries from specified tables
        If no tables are specified, clean up all supported tables

        :param tables: List of table names to clean up, or None for all tables
        :return: Dictionary with counts of removed entries per table
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Running automatic database cleanup")

        # Define all supported tables and their ID/name columns
        all_tables = {
            "summary": ("id", "shortdesc"),
            "school": ("id", "name"),
            "focus": ("id", "focus"),
            "employer": ("id", "employer"),
            "position": ("id", "position"),
            "skill": ("id", "shortdesc"),
            "certification": ("id", "certification"),
            "glossary": ("id", "term"),
            # Add other tables as needed
        }

        # Use specified tables or all tables
        tables_to_clean = tables if tables else all_tables.keys()

        cleanup_results = {}
        total_removed = 0

        # Process each table
        for table in tables_to_clean:
            if table not in all_tables:
                logger.warning(f"Skipping unsupported table: {table}")
                continue

            id_col, name_col = all_tables[table]

            try:
                # Find disabled entries (state = 0)
                self.cursor.execute(
                    f"""
                    SELECT {id_col}, {name_col} FROM {table} 
                    WHERE state = 0
                    """
                )
                disabled_entries = self.cursor.fetchall()

                logger.info(f"Found {len(disabled_entries)} disabled {table} entries")

                # Delete each disabled entry
                for entry in disabled_entries:
                    entry_id = entry[0]
                    entry_name = entry[1]

                    logger.info(f"Deleting {table} #{entry_id}: {entry_name}")
                    self.row(table, entry_id)
                    total_removed += 1

                cleanup_results[table] = len(disabled_entries)
            except Exception as e:
                logger.error(f"Error cleaning up {table} entries: {e}")
                cleanup_results[table] = f"Error: {str(e)}"

        # Commit all changes
        self.conn.commit()

        logger.info(f"Cleanup complete - removed {total_removed} entries")
        return cleanup_results