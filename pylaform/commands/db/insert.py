from sqlite3 import Cursor, Connection
from tenacity import retry, stop_after_delay
from werkzeug.datastructures.structures import ImmutableMultiDict

from . import connect, delete, query
from ...utilities.commands import date_adapter, transform_get_id, unique


class Inserts:
    """
    Complete insert for adapter.
    Actions: INSERT INTO

    :return None: None
    """

    @retry(stop=(stop_after_delay(10)))
    def __init__(self) -> None:
        self.conn: Connection = connect.db()
        self.cursor: Cursor = self.conn.cursor()
        self.query = query.Queries()
        self.delete = delete.Deletes()

    # In insert.py - Replace the multi_column method with this version
    @retry(stop=(stop_after_delay(10)))
    def multi_column(self, table: str, **kwargs) -> None:
        """
        Takes kwargs and injects them into the database, supports nesting automatically.
        :param str table: Table name.
        :param kwargs: Key/Val pairs of column/values.
        :return None: None
        """

        # Remove any values that are None to avoid insertion issues
        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}

        # Build the query parts
        columns = []
        params = []
        values = []

        for key, value in filtered_kwargs.items():
            # Extract column name (handle nested keys)
            col_name = key.split('_')[-1]
            columns.append(f"`{col_name}`")
            params.append("?")
            values.append(value)

        # Create and execute the parameterized query
        query = f"""
        INSERT INTO `{table}` ({', '.join(columns)})
        VALUES ({', '.join(params)})
        """

        print(f"Insert query: {query}")
        print(f"Values: {values}")

        try:
            response = self.cursor.execute(query, values)
            self.conn.commit()
            print(f"Successfully inserted into {table}. Last row ID: {self.cursor.lastrowid}")
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Error inserting into {table}: {e}")
            raise

    def single_item(self, table: str, item: dict[str, str | int | bool], nested: bool = False) -> None:
        """
        Updates a table based on a single value for basic Select From Where clauses.
        :param str table: Table name.
        :param dict[str, str | int | bool] item: iterated chunk from transform_get_id.
        :param bool nested: override current attr values and target last item id to unpack.
        :return None: None
        """

        if "_dropdown" in item["attr"] or "_enabled" in item["attr"]:
            return
        if nested:
            item["attr"] = str(item["attr"]).split("_")[-1]
        print(
            f"""
                UPDATE {table}
                SET    `{item["attr"]}` = {item["value"]},
                       `state` = {int(item["state"])}
                WHERE  `id` = {int(item["id"])}
                """)
        try:
            value = int(item["value"])
            response: Cursor = self.cursor.execute(
                f"""
                UPDATE {table}
                SET    `{item["attr"]}` = {item["value"]},
                       `state` = {int(item["state"])}
                WHERE  `id` = {int(item["id"])}
                """)
        except ValueError:
            response: Cursor = self.cursor.execute(
                f"""
                UPDATE {table}
                SET    `{item["attr"]}` = '{item["value"]}',
                       `state` = {int(item["state"])}
                WHERE  `id` = {int(item["id"])}
                """)

        # Commit changes.
        self.conn.commit()
        return