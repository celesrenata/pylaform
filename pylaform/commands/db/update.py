from sqlite3 import Cursor, Connection
from tenacity import retry, stop_after_delay
from werkzeug.datastructures.structures import ImmutableMultiDict

from . import connect, delete, query
from ...utilities.commands import transform_get_id, unique


class Post:
    """
    Collection of queries to run against the local database.
    Actions: INSERT INTO, DELETE FROM, UPDATE
    :return None: None
    """

    @retry(stop=(stop_after_delay(10)))
    def __init__(self) -> None:
        self.conn: Connection = connect.db()
        self.cursor: Cursor = self.conn.cursor()
        self.query = query.Get()
        self.delete = delete.Delete()

    def update_identification(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the identification table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return: None
        """

        # Transform from template.
        form_data: list[dict[str, str | bool]] = transform_get_id(form_data)
        for item in form_data:
            self.cursor.execute(
                f"""
                UPDATE `identification`
                SET `value` = '{item["value"]}',
                `state` = {int(item["state"])}
                WHERE `id` = {item["id"]};
                """)
            
        # Commit changes.
        self.conn.commit()
        return

    def update_certifications(self, transform_form_data: ImmutableMultiDict) -> None:
        """
        Updates the certification table.
        :param ImmutableMultiDict transform_form_data: Form data from template.
        :return: list
        """

        # Transform from template.
        transform_form_data: list[dict[str, str | bool]] = transform_get_id(transform_form_data)
        counter: str = ""
        result: dict[str, str | int] = {}
        for item in transform_form_data:
            if counter != str(item["id"]):
                counter = str(item["id"])
                result = {}
                
            # Delete certifications.
            if "delete" in item["attr"]:
                self.delete.delete_target(item["id"], "certification")

            # Create certifications.
            elif "new" in item["id"]:
                # Create result based on current attribute value.
                match item["attr"]:
                    case "certification":
                        result.update({"certification": item["value"]})
                    case "year":
                        result.update({"year": item["value"], "state": int(item["state"])})
                    
                # Detect last iteration.
                if len(result) == 3:
                    self.cursor.execute(
                        f"""
                        INSERT INTO `certification`
                        (`certification`, `year`, `state`)
                        VALUES ('{result["certification"]}', '{result["year"]}', '{result["state"]}');
                        """)
                    
            # Update certifications.
            else:
                self.cursor.execute(
                    f"""
                    UPDATE `certification`
                    SET {item["attr"]} = '{item["value"]}',
                    `state` = {item["state"]}
                    WHERE `id` = {item["id"]}
                    """
                )

        # Commit changes.
        self.conn.commit()
        return

    def update_positions(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the employment and positions tables.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """

        # Get item count.
        attrs: list[str] = list(form_data.keys())
        attrs_per_id: int = 0

        # Transform from template.
        transform_form_data: list[dict[str, str | bool]] = transform_get_id(form_data)
        counter: str = ""
        result: dict[str, str | int] = {}
        for item in transform_form_data:
            if counter != str(item["id"]):
                counter = str(item["id"])
                result = {}

            # Build attrs to expect per ID.
            attrs_per_id = len(unique(transform_form_data))

            # Delete position, and employer (if necessary).
            if "delete" in item["attr"]:
                self.delete.delete_association(item["id"], "employer", "position")

            # Create position, and employer if necessary.
            elif "new" in item["id"]:
                # Create result based on current attribute value.
                match item["attr"]:
                    case "employer_dropdown":
                        if item["value"] != "EDIT" and item["value"] != "ADD":
                            result.update({"employerid": int(item["value"])})
                    case "position_dropdown":
                        if item["value"] not in ["EDIT", "ADD"]:
                            result.update({"positionid": int(item["value"])})
                    case "location":
                        result.update({"location": item["value"]})
                    case "employer":
                        result.update({"employername": item["value"], "state": int(item["state"])})
                    case "position":
                        result.update({"positionname": item["value"], "state": int(item["state"])})
                    case "startdate":
                        result.update({"startdate": item["value"]})
                    case "enddate":
                        result.update({"enddate": item["value"]})

                # Cleanup dates for (hidden) and 'Present' value detection.
                if "date" in item["attr"]:
                    if item["value"] == "":
                        item["value"] = "9999-01-01"
                    if item["value"] == "hidden":
                        item["value"] = "0001-01-01"
                if all(key in result for key in ["location", "employername", "positionname", "startdate", "enddate", "state"]):
                    if "employerid" not in result:
                        result.update({"employerid": self.query.query_id(result["employername"], "employer")})

                    # Check for employer.
                    if result["employerid"] == 0:
                        check_employer = self.cursor.execute(
                            f"""
                            SELECT *
                            FROM `employer`
                            WHERE `employer` = '{result["employername"]}'
                            """)
                        if len(check_employer.fetchall()) == 0:  # If no employer.
                            self.cursor.execute(
                                f"""
                                INSERT INTO `employer`
                                            (`employer`, `location`, `state`)
                                VALUES      ('{result["employername"]}', '{result["location"]}', '{result["state"]}');
                                """)

                            # Commit changes.
                            self.conn.commit()
                            result.update({"employerid": self.query.query_id(result["employername"], "employer")})
                    self.cursor.execute(
                        f"""
                        INSERT INTO `position`
                                    (`employer`, `position`,
                                    `startdate`, `enddate`, `state`)
                        VALUES      ('{result["employerid"]}', '{result["positionname"]}',
                                    '{result["startdate"]}', '{result["enddate"]}', '{result["state"]}');
                        """)

            # Update employer and position.
            else:
                # Cleanup dates for (hidden) and "Present" value detection.
                if "date" in item["attr"]:
                    if item["value"] == "":
                        item["value"] = "9999-01-01"
                    if item["value"] == "hidden":
                        item["value"] = "0001-01-01"

                if "delete" not in item["attr"] and "new" not in item["attr"]:
                    # Detect if enough data to update employer.
                    if item["attr"] == "location" or item["attr"] == "employer":
                        self.update_target_table(item, "employer")
                    # Detect if enough data to update position.
                    if "position" in item["attr"]:
                        if item["attr"] == "position":
                            self.update_target_table(item, "position")

        # Commit changes.
        self.conn.commit()
        return

    def update_skills(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the skills table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """

        # Transform from template.
        transform_form_data: list[dict[str, str | bool]] = transform_get_id(form_data)
        counter: str = ""
        result: dict[str, str | int] = {}
        for item in transform_form_data:
            # Get ID from name.
            if item["attr"] == "employer":
                item["value"] = str(self.query.query_id(item["value"], "employer"))
            if item["attr"] == "position":
                item["value"] = str(self.query.query_id(item["value"], "position"))
            if counter != str(item["id"]):
                counter = str(item["id"])
                result = {}
            
            # Delete skill.
            if "delete" in item["attr"]:
                self.delete.delete_target(item["id"], "skill")

            # Create skill.
            elif "new" in item["id"]:
                # Create result based on current attribute value.
                match item["attr"]:
                    case "category":
                        result.update({"category": item["value"], "state": int(item["state"])})
                    case "subcategory":
                        result.update({"subcategory": item["value"]})
                    case "employer_dropdown":
                        result.update({"employer": item["value"]})
                    case "position_dropdown":
                        result.update({"position": item["value"]})
                    case "shortdesc":
                        result.update({"shortdesc": item["value"]})
                    case "longdesc":
                        result.update({"longdesc": item["value"]})

                # Detect last iteration.
                if len(result) == 7:
                    # TODO: Implement ordering support.
                    self.cursor.execute(
                        f"""
                        INSERT INTO `skill`
                                    (`employer`, `position`, `shortdesc`,
                                    `longdesc`, `category`, `subcategory`,
                                    `categoryorder`, `skillorder`, `state`)
                        VALUES      ('{result["employer"]}', '{result["position"]}', '{result["shortdesc"]}',
                                    '{result["longdesc"]}', '{result["category"]}', '{result["subcategory"]}',
                                    '1', '1', '{result["state"]}');
                        """)
            # Update skill.
            else:
                if "dropdown" not in item["attr"]:
                    self.cursor.execute(
                        f"""
                            UPDATE `skill`
                            SET `{item["attr"]}` = '{item["value"]}',
                            `state` = {item["state"]}
                            WHERE `id` = {int(item["id"])}
                        """)
        
        # Commit changes.
        self.conn.commit()
        return

    def update_summary(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the summary table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """

        # Transform from template.
        transform_form_data: list[dict[str, str | bool]] = transform_get_id(form_data)
        counter: str = ""
        result: dict[str, str | int] = {}
        for item in transform_form_data:
            if counter != str(item["id"]):
                counter = str(item["id"])
                result = {}
            
            # Delete summary.
            if "delete" in item["attr"]:
                self.delete.delete_target(item["id"], "summary")

            # Create summary.
            elif "new" in item["id"]:
                # Create result based on current attribute value.
                match item["attr"]:
                    case "shortdesc":
                        result.update({"shortdesc": item["value"]})
                    case "longdesc":
                        result.update({"longdesc": item["value"], "state": int(item["state"])})
                # Detect last iteration.
                if len(result) == 3:
                    self.cursor.execute(
                        f"""
                        INSERT INTO `summary`
                        (`shortdesc`, `longdesc`, `summaryorder`, `state`)
                        VALUES ('{result["shortdesc"]}', '{result["longdesc"]}', '1', '{result["state"]}');
                        """)
            # Update summary.
            else:
                self.cursor.execute(
                    f"""
                    UPDATE `summary`
                    SET `{item['attr']}` = '{item['value']}',
                    `state` = {item['state']}
                    WHERE `id` = {item['id']}
                    """)

        # Commit changes.
        self.conn.commit()
        return

    def update_education(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the education and focus tables.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """

        # Get item count.
        attrs: list[str] = list(form_data.keys())
        attrs_per_id: int = 0

        # Transform from template.
        transform_form_data: list[dict[str, str | bool]] = transform_get_id(form_data)
        counter: str = ""
        result: dict[str, str | int] = {}
        for item in transform_form_data:
            if counter != str(item["id"]):
                counter = str(item["id"])
                result = {}

            # Build attrs to expect per ID.
            attrs_per_id = len(unique(transform_form_data))

            # Delete focus, and school (if necessary).
            if "delete" in item["attr"]:
                self.delete.delete_association(item["id"], "school", "focus")

            # Create focus, and school if necessary.
            elif "new" in item["id"]:
                # Create result based on current attribute value.
                match item["attr"]:
                    case "school_dropdown":
                        if item["value"] != "EDIT" and item["value"] != "ADD":
                            result.update({"schoolid": int(item["value"])})
                    case "focus_dropdown":
                        if item["value"] not in ["EDIT", "ADD"]:
                            result.update({"focusid": int(item["value"])})
                    case "location":
                        result.update({"location": item["value"]})
                    case "school":
                        result.update({"schoolname": item["value"], "state": int(item["state"])})
                    case "focus":
                        result.update({"focusname": item["value"], "state": int(item["state"])})
                    case "startdate":
                        result.update({"startdate": item["value"]})
                    case "enddate":
                        result.update({"enddate": item["value"]})

                # Cleanup dates for (hidden) and 'Present' value detection.
                if "date" in item["attr"]:
                    if item["value"] == "":
                        item["value"] = "9999-01-01"
                    if item["value"] == "hidden":
                        item["value"] = "0001-01-01"
                if all(key in result for key in ["location", "schoolname", "focusname", "startdate", "enddate", "state"]):
                    if "schoolid" not in result:
                        result.update({"schoolid": self.query.query_id(result["schoolname"], "school")})

                    # Check for school.
                    if result["schoolid"] == 0:
                        check_school = self.cursor.execute(
                            f"""
                            SELECT *
                            FROM `school`
                            WHERE `school` = '{result["schoolname"]}'
                            """)
                        if len(check_school.fetchall()) == 0:  # If no school.
                            self.cursor.execute(
                                f"""
                                INSERT INTO `school`
                                            (`school`, `location`, `state`)
                                VALUES      ('{result["schoolname"]}', '{result["location"]}', '{result["state"]}');
                                """)

                            # Commit changes.
                            self.conn.commit()
                            result.update({"schoolid": self.query.query_id(result["schoolname"], "school")})
                    self.cursor.execute(
                        f"""
                        INSERT INTO `focus`
                                    (`school`, `focus`,
                                    `startdate`, `enddate`, `state`)
                        VALUES      ('{result["schoolid"]}', '{result["focusname"]}',
                                    '{result["startdate"]}', '{result["enddate"]}', '{result["state"]}');
                        """)

            # Update school and focus.
            else:
                # Cleanup dates for (hidden) and "Present" value detection.
                if "date" in item["attr"]:
                    if item["value"] == "":
                        item["value"] = "9999-01-01"
                    if item["value"] == "hidden":
                        item["value"] = "0001-01-01"

                if "delete" not in item["attr"] and "new" not in item["attr"]:
                    # Detect if enough data to update school.
                    if item["attr"] == "location" or item["attr"] == "school":
                        self.update_target_table(item, "school")
                    # Detect if enough data to update focus.
                    if "focus" in item["attr"]:
                        if item["attr"] == "focus":
                            self.update_target_table(item, "focus")

        # Commit changes.
        self.conn.commit()
        return

    def update_achievements(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the achievements table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """

        # Transform from template.
        transform_form_data: list[dict[str, str | bool]] = transform_get_id(form_data)
        counter: str = ""
        result: dict[str, str | int] = {}
        for item in transform_form_data:
            if counter != str(item["id"]):
                counter = str(item["id"])
                result = {}
            
            # Delete achievement.
            if "delete" in item["attr"]:
                self.delete.delete_target(item["id"], "achievement")

            # Create achievement.
            elif "new" in item["id"]:
                # Create result based on current attribute value.
                match item["attr"]:
                    case "position":
                        item["value"] = str(self.query.query_id(item["value"], "position"))
                        result.update({"position": item["value"], "state": int(item["state"])})
                    case "employer":
                        item["value"] = str(self.query.query_id(item["value"], "employer"))
                        result.update({"employer": item["value"], "state": int(item["state"])})
                    case "achievement":
                        result.update({"achievement": item["value"]})
                    case "shortdesc":
                        result.update({"shortdesc": item["value"]})
                    case "longdesc":
                        result.update({"longdesc": item["value"], "state": int(item["state"])})
                # Detect last iteration.
                if len(result) == 5:
                    self.cursor.execute(
                        f"""
                        INSERT INTO `achievement`
                                    (`position`, `employer`, 
                                    `shortdesc`, `longdesc`, `state`)
                        VALUES      ('{result["employer"]}', '{result["position"]}',
                                    '{result["shortdesc"]}', '{result["longdesc"]}', '{result["state"]}');
                        """)
                    
            # Update achievement.
            else:
                # Get ID from name.
                match item["attr"]:
                    case "position":
                        item["value"] = str(self.query.query_id(item["value"], "position"))
                    case "employer":
                        item["value"] = str(self.query.query_id(item["value"], "employer"))
                self.cursor.execute(
                    f"""
                         UPDATE `achievement`
                         SET {item['attr']} = '{item['value']}',
                         state = {item['state']}
                         WHERE id = {int(item['id'])}
                     """)

        # Commit changes.
        self.conn.commit()
        return

    def update_glossary(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the glossary table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """

        # Transform from template.
        transform_form_data: list[dict[str, str | bool]] = transform_get_id(form_data)
        counter: str = ""
        result: dict[str, str | int] = {}
        for item in transform_form_data:
            if counter != item["id"]:
                counter = item["id"]
                result = {}
                
            # Delete term.
            if "delete" in item["attr"]:
                self.delete.delete_target(item["id"], "glossary")

            # Create term.
            elif "new" in item["id"]:
                # Create result based on current attribute value.
                match item["attr"]:
                    case "term":
                        result.update({"term": item["value"]})
                    case "url":
                        result.update({"url": item["value"]})
                    case "description":
                        result.update({"description": item["value"], "state": int(item["state"])})
                # Detect last iteration.
                if len(result) == 4:
                    self.cursor.execute(
                        f"""
                       INSERT INTO `glossary`
                                   (`term`, `url`,
                                   `description`, `state`)
                       VALUES      ('{result["term"]}', '{result["url"]}',
                                   '{result["description"]}', '{result["state"]}');
                       """)
                    
            # Update term.
            else:
                self.cursor.execute(
                    f"""
                    UPDATE `glossary`
                    SET `{item["attr"]}` = '{item["value"]}',
                    `state` = {item["state"]}
                    WHERE id = {item["id"]}
                    """)
        
        # Commit changes.
        self.conn.commit()
        return

    def update_target_table(self, item: dict[str, str | bool], table: str):
        """
        :param dict[str, str | bool] item: Decompiled attribute pack.
        :param str table: table to update.
        :return:
        """

        try:
            item["value"] = int(item["value"])
            self.cursor.execute(
                f"""
                UPDATE `{table}`
                SET    `id` = {item["value"]},
                       `state` = {item["state"]}
                WHERE  `id` = {int(item["id"])}
                """
            )
        except ValueError:
            self.cursor.execute(
                f"""
                 UPDATE `{table}`
                 SET    `{item["attr"]}` = '{item["value"]}',
                        `state` = {item["state"]}
                 WHERE  `id` = {int(item["id"])}
                 """)
            pass

        # Commit changes.
        self.conn.commit()
        return
