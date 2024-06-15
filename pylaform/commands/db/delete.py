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
