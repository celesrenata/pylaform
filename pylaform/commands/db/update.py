from . import connect, query
from datetime import datetime
from tenacity import retry, stop_after_delay
from ...utilities.commands import listify, transform_get_id


class Post:
    """
        Connect to the Database and return basic selections, to be improved for user specifics.
        :return: Dictionary
    """
    @retry(stop=(stop_after_delay(10)))
    def __init__(self):

        self.conn = connect.db()
        self.cursor = self.conn.cursor()
        self.query = query.Get()

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
        counter = ""
        for item in form_data:
            if counter != item['id']:
                counter = item['id']
                result = {}
            if "delete" in item['attr']:
                self.cursor.execute(
                    f"""
                       DELETE FROM `certifications`
                       WHERE `id` = {int(item['id'])};
                       """
                )
            elif "new" in item['id']:
                match item['attr']:
                    case 'certification':
                        result.update({"certification": item["value"]})
                    case 'year':
                        result.update({"year": item["value"], "state": int(item["state"])})
                if len(result) == 3:
                    self.cursor.execute(
                        f"""
                               INSERT INTO `certifications`
                               (`certification`, `year`, `state`)
                               VALUES ('{result["certification"]}', '{result["year"]}', '{result["state"]}');
                           """)
            else:
                self.cursor.execute(
                    f"""
                        UPDATE `certifications`
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
        counter = ""
        result = {}
        for item in form_data:
            if item["attr"] == "employer":
                item["value"] = self.query.query_id(item["value"], "employer")
            if item["attr"] == "position":
                item["value"] = self.query.query_id(item["value"], "position")
            if counter != item['id']:
                counter = item['id']
                result = {}
            if "delete" in item['attr']:
                self.cursor.execute(
                    f"""
                    DELETE FROM `skills`
                    WHERE `id` = {int(item['id'])};
                    """
                )
            elif "new" in item['id']:
                match item['attr']:
                    case 'category':
                        result.update({"category": item["value"]})
                    case 'subcategory':
                        result.update({"subcategory": item["value"]})
                    case 'employer':
                        result.update({"employer": item["value"]})
                    case 'position':
                        result.update({"position": item["value"]})
                    case 'shortdesc':
                        result.update({"shortdesc": item["value"]})
                    case 'longdesc':
                        result.update({"longdesc": item["value"], "state": int(item["state"])})
                if len(result) == 7:
                    self.cursor.execute(
                        f"""
                            INSERT INTO `skills`
                            (`employer`, `position`, `shortdesc`, `longdesc`, `category`, `subcategory`, `categoryorder`, `skillorder`, `state`)
                            VALUES ('{result["employer"]}', '{result["position"]}', '{result["shortdesc"]}', '{result["longdesc"]}', '{result["category"]}', '{result["subcategory"]}', '1', '1', '{result["state"]}');
                        """)
            else:
                self.cursor.execute(
                    f"""
                        UPDATE `skills`
                        SET `{item['attr']}` = '{item['value']}',
                        `state` = {item['state']}
                        WHERE `id` = {int(item['id'])}
                    """)

        self.conn.commit()
        return

    def update_summary(self, form_data):
        """
        Update skills table
        :return: list
        """

        form_data = transform_get_id(form_data)
        counter = ""
        result = {}
        for item in form_data:
            if counter != item['id']:
                counter = item['id']
                result = {}
            if "delete" in item['attr']:
                self.cursor.execute(
                    f"""
                    DELETE FROM `summary`
                    WHERE `id` = {int(item['id'])};
                    """
                )
            elif "new" in item['id']:
                match item['attr']:
                    case 'shortdesc':
                        result.update({"shortdesc": item["value"]})
                    case 'longdesc':
                        result.update({"longdesc": item["value"], "state": int(item["state"])})
                if len(result) == 3:
                    self.cursor.execute(
                        f"""
                            INSERT INTO `summary`
                            (`shortdesc`, `longdesc`, `summaryorder`, `state`)
                            VALUES ('{result["shortdesc"]}', '{result["longdesc"]}', '1', '{result["state"]}');
                        """)
            else:
                self.cursor.execute(
                    f"""
                        UPDATE summary
                        SET {item['attr']} = '{item['value']}',
                        state = {item['state']}
                        WHERE id = {item['id']}
                    """)

        self.conn.commit()
        return

    def update_education(self, form_data):
        """
        Update school and focus tables
        :return: list
        """

        form_data = transform_get_id(form_data)
        counter = ""
        result = {}
        for item in form_data:
            if counter != item['id']:
                counter = item['id']
                result = {}
            if "delete" in item['attr'] and "school" in item['id']:
                self.cursor.execute(
                    f"""
                    DELETE FROM `school`
                    WHERE `id` = {int(item['id'])};
                    """
                )
            elif "delete" in item['attr'] and "focus" in item['id']:
                self.cursor.execute(
                    f"""
                    DELETE FROM `focus`
                    WHERE `id` = {int(item['id'])};
                    """
                )
            elif "new" in item['id'] and ("school" in item['attr'] or "location" in item['attr']):
                match item['attr']:
                    case 'location':
                        result.update({"location": item["value"], "state": int(item["state"])})
                    case 'school':
                        result.update({"school": item["value"], "state": int(item["state"])})
                if len(result) == 3:
                    if "date" in item['attr']:
                        if item['value'] == '':
                            item['value'] = datetime.strptime('9999-01-01', '%Y-%m-%d')
                        if item['value'] == 'hidden':
                            item['value'] = datetime.strptime('0001-01-01', '%Y-%m-%d')
                    check_school = self.cursor.execute(
                        f"""
                            SELECT *
                            FROM `schools`
                            WHERE `school` = '{result["school"]}'
                        """)
                    if len(check_school.fetchall()) == 0:
                        self.cursor.execute(
                            f"""
                                INSERT INTO `schools`
                                (`school`, `location`, `state`)
                                VALUES ('{result["school"]}', '{result["location"]}', '{result["state"]}');
                            """)
            elif "new" in item['id']:

                match item['attr']:
                    case 'school':
                        if item["attr"] == "school":
                            item["value"] = self.query.query_id(item["value"], "school")
                        result.update({"school": item["value"]})
                    case 'focus':
                        result.update({"focus": item["value"]})
                    case 'startdate':
                        result.update({"startdate": item["value"]})
                    case 'enddate':
                        result.update({"enddate": item["value"], "state": int(item["state"])})
                if len(result) == 6:
                    if "date" in item['attr']:
                        if item['value'] == '':
                            item['value'] = datetime.strptime('9999-01-01', '%Y-%m-%d')
                        if item['value'] == 'hidden':
                            item['value'] = datetime.strptime('0001-01-01', '%Y-%m-%d')
                        result["school"] = self.query.query_id(result["school"], "school")
                    print(
                        f"""
                            INSERT INTO `focus`
                            (`school`, `focus`, `startdate`, `enddate`, `state`)
                            VALUES ('{result["school"]}', '{result["focus"]}', '{result["startdate"]}', '{result["enddate"]}', '{result["state"]}');
                        """)
                    self.cursor.execute(
                        f"""
                            INSERT INTO `focus`
                            (`school`, `focus`, `startdate`, `enddate`, `state`)
                            VALUES ('{result["school"]}', '{result["focus"]}', '{result["startdate"]}', '{result["enddate"]}', '{result["state"]}');
                        """)
            else:
                if "date" in item['attr']:
                    if item['value'] == '':
                        item['value'] = datetime.strptime('9999-01-01', '%Y-%m-%d')
                    if item['value'] == 'hidden':
                        item['value'] = datetime.strptime('0001-01-01', '%Y-%m-%d')
                if "location" in item["attr"] or "school" in item["attr"]:
                    self.cursor.execute(
                        f"""
                                UPDATE `schools`
                                SET {item['attr']} = '{item['value']}',
                                state = {item['state']}
                                WHERE id = {int(item['id'])}
                            """)
                elif "delete" not in item['attr'] and "new" not in item['attr']:
                    self.cursor.execute(
                        f"""
                             UPDATE `focus`
                             SET {item['attr']} = '{item['value']}',
                             state = {item['state']}
                             WHERE id = {int(item['id'])}
                         """)

        self.conn.commit()
        return

    def update_glossary(self, form_data):
        """
        Update glossary table
        :return: list
        """

        form_data = transform_get_id(form_data)
        counter = ""
        result = {}
        for item in form_data:
            if counter != item['id']:
                counter = item['id']
                result = {}
            if "delete" in item['attr']:
                self.cursor.execute(
                    f"""
                       DELETE FROM `glossary`
                       WHERE `id` = {int(item['id'])};
                       """
                )
            elif "new" in item['id']:
                match item['attr']:
                    case 'term':
                        result.update({"term": item["value"]})
                    case 'url':
                        result.update({"url": item["value"]})
                    case "description":
                        result.update({"description": item["value"], "state": int(item["state"])})
                if len(result) == 4:
                    self.cursor.execute(
                        f"""
                               INSERT INTO `glossary`
                               (`term`, `url`, `description`, `state`)
                               VALUES ('{result["term"]}', '{result["url"]}', '{result["description"]}', '{result["state"]}');
                           """)
            else:
                self.cursor.execute(
                    f"""
                           UPDATE `glossary`
                           SET {item['attr']} = '{item['value']}',
                           state = {item['state']}
                           WHERE id = {item['id']}
                       """)

        self.conn.commit()
        return
