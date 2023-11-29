from . import connect
from datetime import datetime
from tenacity import retry, stop_after_delay
from ...utilities.commands import transform_get_id


class Post:
    """
        Connect to the Database and return basic selections, to be improved for user specifics.
        :return: Dictionary
    """
    @retry(stop=(stop_after_delay(10)))
    def __init__(self):

        self.conn = connect.db()
        self.cursor = self.conn.cursor()

    def update_identification(self, form_data) -> None:
        """
        Updates identification table
        :param any form_data: post data
        :return: None
        """

        form_data = transform_get_id(form_data)
        for item in form_data:
            self.cursor.execute(
                f"""
                    UPDATE identification
                    SET value = '{item['value']}',
                    state = {item['state']}
                    WHERE id = {item['id']}
                """)
        self.conn.commit()
        return

    def update_certifications(self, form_data):
        """
        Update certification table
        :return: list
        """

        form_data = transform_get_id(form_data)
        for item in form_data:
            if "is_new" in item:
                self.cursor.execute(
                    f"""INSERT INTO certifications (id, certification, year, state)
                    VALUES (item['id'], item['certification'], item['year'], item['state'])"""
                )
            else:
                self.cursor.execute(
                    f"""
                        UPDATE certifications
                        SET {item['attr']} = '{item['value']}',
                        state = {item['state']}
                        WHERE id = {item['id']}
                    """
                )

        self.conn.commit()
        return

    def update_positions(self, form_data):
        """
        Update employment table
        :return: list
        """

        form_data = transform_get_id(form_data)
        for item in form_data:
            if item['attr'] == "employer":
                self.cursor.execute(
                    f"""
                           UPDATE employers
                           SET {item['attr']} = '{item['value']}',
                           state = {item['state']}
                           WHERE id = {item['id']}
                       """
                )

            else:
                if "date" in item['attr']:
                    if item['value'] == '':
                        item['value'] = datetime.strptime('9999-01-01', '%Y-%m-%d')
                    if item['value'] == 'hidden':
                        item['value'] = datetime.strptime('0001-01-01', '%Y-%m-%d')
                self.cursor.execute(
                    f"""
                        UPDATE positions
                        SET {item['attr']} = '{item['value']}',
                        state = {item['state']}
                        WHERE id = {item['id']}
                    """
                )

        self.conn.commit()
        return

    def update_skills(self, form_data):
        """
        Update skills table
        :return: list
        """

        form_data = transform_get_id(form_data)
        for item in form_data:
            self.cursor.execute(
                f"""
                    UPDATE skills
                    SET {item['attr']} = '{item['value']}',
                    state = {item['state']}
                    WHERE id = {item['id']}
                """
            )

        self.conn.commit()
        return

    def update_summary(self, form_data):
        """
        Update skills table
        :return: list
        """

        form_data = transform_get_id(form_data)
        for item in form_data:
            self.cursor.execute(
                f"""
                    UPDATE summary
                    SET {item['attr']} = '{item['value']}',
                    state = {item['state']}
                    WHERE id = {item['id']}
                """
            )

        self.conn.commit()
        return

    def update_education(self, form_data):
        """
        Update school and focus tables
        :return: list
        """

        form_data = transform_get_id(form_data)
        for item in form_data:
            if item['attr'] == "school":
                self.cursor.execute(
                    f"""
                            UPDATE schools
                            SET {item['attr']} = '{item['value']}',
                            state = {item['state']}
                            WHERE id = {item['id']}
                        """
                )

            else:
                if "date" in item['attr']:
                    if item['value'] == '':
                        item['value'] = datetime.strptime('9999-01-01', '%Y-%m-%d')
                    if item['value'] == 'hidden':
                        item['value'] = datetime.strptime('0001-01-01', '%Y-%m-%d')

                self.cursor.execute(
                    f"""
                         UPDATE focus
                         SET {item['attr']} = '{item['value']}',
                         state = {item['state']}
                         WHERE id = {item['id']}
                     """
                )

        self.conn.commit()
        return
