from sqlite3 import Cursor, Connection
from tenacity import retry, stop_after_delay
from werkzeug.datastructures.structures import ImmutableMultiDict

from . import connect, delete, query
from ...utilities.commands import date_adapter, transform_get_id, unique


class Updates:
    """
    Collection of queries to run against the local database.
    Actions: UPDATE
    :return None: None
    """

    @retry(stop=(stop_after_delay(10)))
    def __init__(self) -> None:
        """
        Initializes classes and values for update tasks.
        :return None: None
        """

        self.conn: Connection = connect.db()
        self.cursor: Cursor = self.conn.cursor()
        self.query = query.Queries()
        self.delete = delete.Deletes()

    @retry(stop=(stop_after_delay(10)))
    def single_attr(self, table: str, row: int, attr: str, value: str | int | bool) -> None:
        """
        Updates a table based on a single value for basic Select From Where clauses
        :param str table: Table name.
        :param int row: Id number.
        :param str attr: Column name.
        :param str | int | bool value: Value to update.
        :return None: None
        """

        try:
            value = int(value)
            response: Cursor = self.cursor.execute(
                f"""
                UPDATE {table}
                SET    `{attr}` = {value}
                WHERE  `id` = {row}
                """)
        except ValueError:
            response: Cursor = self.cursor.execute(
            f"""
            UPDATE {table}
            SET    `{attr}` = '{value}'
            WHERE  `id` = {row}
            """)

        # Commit changes.
        self.conn.commit()
        return

    @retry(stop=(stop_after_delay(10)))
    @retry(stop=(stop_after_delay(10)))
    def single_item(self, table: str, item: dict[str, str | int | bool], nested: bool = False) -> None:
        """
        Updates a table based on a single value group for basic Select From Where clauses.
        :param str table: Table name.
        :param dict[str, str | int | bool] item: iterated chunk from transform_get_id.
        :param bool nested: override current attr values and target last item id to unpack.
        :return None: None
        """

        if "_dropdown" in item["attr"] or "_enabled" in item["attr"]:
            return

        # Detect nested.
        if nested:
            item["attr"] = str(item["attr"]).split("_")[-1]

        try:
            value = int(item["value"])
            response: Cursor = self.cursor.execute(
                f"""
                UPDATE {table}
                SET    `{item["attr"]}` = ?,
                       `state` = ?
                WHERE  `id` = ?
                """, (value, int(item["state"]), int(item["id"])))
        except ValueError:
            # Properly escape the string value by using parameterized queries
            response: Cursor = self.cursor.execute(
                f"""
                UPDATE {table}
                SET    `{item["attr"]}` = ?,
                       `state` = ?
                WHERE  `id` = ?
                """, (item["value"], int(item["state"]), int(item["id"])))

        # Commit changes.
        self.conn.commit()
        return

    @retry(stop=(stop_after_delay(10)))
    def inverted_single_item(self, table: str, item: dict[str, str | int | bool]) -> None:
        """
        Updates raw form data tables.
        :param str table: Table name.
        :param dict[str, str | int | bool] item: iterated chunk from transform_get_id.
        :return None: None
        """

        if "_dropdown" in item["attr"] or "_enabled" in item["attr"]:
            return

        # No print statement - remove debugging output entirely

        try:
            value = int(item["value"])
            response: Cursor = self.cursor.execute(
                f"""
                           UPDATE `{table}`
                           SET    `value` = {item["value"]},
                                  `state` = {int(item["state"])}
                           WHERE  `attr` = '{item["attr"]}';
                           """)
        except ValueError:
            response: Cursor = self.cursor.execute(
                f"""
                           UPDATE `{table}`
                           SET    `value` = '{item["value"]}',
                                  `state` = {int(item["state"])}
                           WHERE  `attr` = '{item["attr"]}';
                           """)

        # Commit changes
        self.conn.commit()
        return

    def multi_column(self, table: str, **kwargs) -> None:
        """
        Updates multiple columns at once for a specific record.
        Improved version that avoids repeated execution.

        :param str table: Table to update.
        :param kwargs: Column names and values to update.
        :return None: None
        """
        # Extract ID from kwargs
        record_id = kwargs.get('id')
        if record_id is None:
            print("Error: ID is required for multi_column update")
            return

        # Build SET clause and parameter list
        set_parts = []
        params = []

        for key, value in kwargs.items():
            if key != 'id':  # Skip ID for SET clause
                if value is None:
                    set_parts.append(f"`{key}` = NULL")
                else:
                    set_parts.append(f"`{key}` = ?")
                    params.append(value)

        # No columns to update
        if not set_parts:
            print(f"Warning: No columns to update for {table} with ID {record_id}")
            return

        # Add ID to parameters for WHERE clause
        params.append(record_id)

        # Construct and execute the query
        query = f"""
            UPDATE `{table}`
            SET    {", ".join(set_parts)}
            WHERE  `id` = ?;
        """

        try:
            # Execute the query once (no retry)
            self.cursor.execute(query, params)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"SQLite error in multi_column update: {e}")
            raise