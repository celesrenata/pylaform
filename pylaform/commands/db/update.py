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

        print(
            f"""
           UPDATE `{table}`
           SET    `value` = {item["value"]},
                  `state` = {int(item["state"])}
           WHERE  `attr` = '{item["attr"]}';
           """)
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

            # Commit changes.
        self.conn.commit()
        return

    @retry(stop=(stop_after_delay(10)))
    def multi_column(self, table: str, **kwargs) -> None:
        """
        Takes kwargs and injects them into the database, supports nesting automatically.
        :param str table: Table name.
        :param kwargs: Key/Val pairs of column/values.
        :return None: None
        """

        # Build the query.
        set_group: str = ""
        for key, value in kwargs.items():
            try:
                set_group = set_group + f"`{key.split('_')[-1]}` = {int(value)}, "
            except ValueError:
                set_group = set_group + f"`{key.split('_')[-1]}` = '{value}', "

        print(
            f"""
            UPDATE `{table}`
            SET    {set_group[:-2]}
            WHERE  `id` = {kwargs["id"]};
            """)
        response: Cursor = self.cursor.execute(
            f"""
            UPDATE `{table}`
            SET {set_group[:-2]}
            WHERE `id` = {kwargs["id"]};
            """)

        # Commit changes.
        self.conn.commit()
        return
