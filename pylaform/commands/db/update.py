from datetime import datetime
from tenacity import retry, stop_after_delay
from . import connect, query
from ...utilities.commands import listify, transform_get_id


class Post:
    """
    Collection of queries to run against the local database.
    Actions: INSERT INTO, DELETE FROM, UPDATE
    :return None: None
    """

    @retry(stop=(stop_after_delay(10)))
    def __init__(self) -> None:
        self.conn = connect.db()
        self.cursor = self.conn.cursor()
        self.query = query.Get()

    def update_identification(self, form_data) -> None:
        """
        Updates the identification table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return: None
        """

        # Transform from template.
        form_data = transform_get_id(form_data)
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

    def update_certifications(self, form_data) -> None:
        """
        Updates the certification table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return: list
        """

        # Transform from template.
        form_data = transform_get_id(form_data)
        counter = ""
        for item in form_data:
            if counter != item["id"]:
                counter = item["id"]
                result = {}
                
            # Delete certifications.
            if "delete" in item["attr"]:
                self.cursor.execute(
                    f"""
                    DELETE FROM `certifications`
                    WHERE `id` = {int(item["id"])};
                    """)
                
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
                        INSERT INTO `certifications`
                        (`certification`, `year`, `state`)
                        VALUES ('{result["certification"]}', '{result["year"]}', '{result["state"]}');
                        """)
                    
            # Update certifications.
            else:
                self.cursor.execute(
                    f"""
                    UPDATE `certifications`
                    SET {item["attr"]} = '{item["value"]}',
                    `state` = {item["state"]}
                    WHERE `id` = {item["id"]}
                    """
                )

        # Commit changes.
        self.conn.commit()
        return

    def update_positions(self, form_data) -> None:
        """
        Updates the employment and positions tables.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """
        
        # Transform from template.
        form_data = transform_get_id(form_data)
        counter = ""
        result = {}
        for item in form_data:
            if counter != item["id"]:
                counter = item["id"]
                result = {}
                
            # Delete position, and employer (if necessary).
            if "delete" in item["attr"]:
                get_employer = self.cursor.execute(
                    f"""
                    SELECT `employer`
                    FROM `positions`
                    WHERE `id` = '{item["id"]}';
                    """)
                self.cursor.execute(
                    f"""
                    DELETE FROM `positions`
                    WHERE `id` = {int(item["id"])};
                    """)
                
                # If no other associations to employer.
                if len(get_employer.fetchall()) <= 1:
                    self.cursor.execute(
                    f"""
                    DELETE FROM `employers`
                    WHERE `id` = {int(item["id"])};
                    """)
                self.cursor.execute(
                    f"""
                    DELETE FROM `positions`
                    WHERE `id` = {int(item["id"])};
                    """
                )
            
            # Create employer.
            elif "new" in item["id"] and ("employer" in item["attr"] or "location" in item["attr"]):
                # Create result based on current attribute value.
                match item["attr"]:
                    case "location":
                        result.update({"location": item["value"], "state": int(item["state"])})
                    case "employer":
                        result.update({"employer": item["value"], "state": int(item["state"])})
                # Detect last iteration.
                if len(result) == 3:
                    # Cleanup dates for (hidden) and 'Present' value detection.
                    if "date" in item["attr"]:
                        if item["value"] == "":
                            item["value"] = datetime.strptime("9999-01-01", "%Y-%m-%d")
                        if item["value"] == "hidden":
                            item["value"] = datetime.strptime("0001-01-01", "%Y-%m-%d")
                            
                    # Check for employer.
                    check_employer = self.cursor.execute(
                        f"""
                        SELECT *
                        FROM `employers`
                        WHERE `employer` = '{result["employer"]}'
                        """)
                    if len(check_employer.fetchall()) == 0:  # If no employer.
                        self.cursor.execute(
                            f"""
                                INSERT INTO `employers`
                                (`employer`, `location`, `state`)
                                VALUES ('{result["employer"]}', '{result["location"]}', '{result["state"]}');
                            """)

                        # Commit changes.
                        self.conn.commit()

            # Create position.
            elif "new" in item["id"]:
                # Create result based on current attribute value.
                match item["attr"]:
                    case "employer":
                        if item["attr"] == "employer":
                            item["value"] = self.query.query_id(item["value"], "employer")
                        result.update({"employer": item["value"]})
                    case "position":
                        result.update({"position": item["value"]})
                    case "startdate":
                        result.update({"startdate": item["value"]})
                    case "enddate":
                        result.update({"enddate": item["value"], "state": int(item["state"])})
                # Detect last iteration.
                if len(result) == 6:
                    # Cleanup dates for (hidden) and 'Present' value detection.
                    if "date" in item["attr"]:
                        if item["value"] == "":
                            item["value"] = datetime.strptime("9999-01-01", "%Y-%m-%d")
                        if item["value"] == "hidden":
                            item["value"] = datetime.strptime("0001-01-01", "%Y-%m-%d")
                        result["employer"] = self.query.query_id(result["employer"], "employer")
                    self.cursor.execute(
                        f"""
                        INSERT INTO `positions`
                        (`employer`, `position`, `startdate`, `enddate`, `state`)
                        VALUES ('{result["employer"]}', '{result["position"]}', 
                                '{result["startdate"]}', '{result["enddate"]}', '{result["state"]}');
                        """)

            # Update employer and position.
            else:
                # Detect last iteration.
                if len(result) == 6:
                    # Cleanup dates for (hidden) and 'Present' value detection.
                    if "date" in item['attr']:
                        if item["value"] == "":
                            item["value"] = datetime.strptime("9999-01-01", "%Y-%m-%d")
                        if item["value"] == "hidden":
                            item["value"] = datetime.strptime("0001-01-01", "%Y-%m-%d")
                    if item["attr"] == "employer":
                        # Check for employer.
                        check_employer = self.cursor.execute(
                            f"""
                            SELECT *
                            FROM `employers`
                            WHERE `employer` = '{item["id"]}'
                            """)
                        if len(check_employer.fetchall()) == 0:  # If no employer.
                            self.cursor.execute(
                                f"""
                                INSERT INTO `employers`
                                (`employer`, `location`, `state`)
                                VALUES ('{result["employer"]}', '{result["location"]}', '{result["state"]}');
                                """)
                # Detect if enough data to update employers.
                if "location" in item["attr"] or "employer" in item["attr"]:
                    self.cursor.execute(
                        f"""
                        UPDATE `employers`
                        SET {item["attr"]} = '{item["value"]}',
                        state = {item["state"]}
                        WHERE id = {int(item["id"])}
                        """)
                # Detect if enough data to update positions.
                elif "delete" not in item['attr'] and "new" not in item['attr']:
                    self.cursor.execute(
                        f"""
                         UPDATE `positions`
                         SET {item["attr"]} = '{item["value"]}',
                         state = {item["state"]}
                         WHERE id = {int(item["id"])}
                         """)

        # Commit changes.
        self.conn.commit()
        return

    def update_skills(self, form_data) -> None:
        """
        Updates the skills table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """

        # Transform from template.
        form_data = transform_get_id(form_data)
        counter = ""
        result = {}
        for item in form_data:
            # Get ID from name.
            if item["attr"] == "employer":
                item["value"] = self.query.query_id(item["value"], "employer")
            if item["attr"] == "position":
                item["value"] = self.query.query_id(item["value"], "position")
            if counter != item["id"]:
                counter = item["id"]
                result = {}
            
            # Delete skill.
            if "delete" in item["attr"]:
                self.cursor.execute(
                    f"""
                    DELETE FROM `skills`
                    WHERE `id` = {int(item["id"])};
                    """)
            
            # Create skill.
            elif "new" in item["id"]:
                # Create result based on current attribute value.
                match item["attr"]:
                    case "category":
                        result.update({"category": item["value"]})
                    case "subcategory":
                        result.update({"subcategory": item["value"]})
                    case "employer":
                        result.update({"employer": item["value"]})
                    case "position":
                        result.update({"position": item["value"]})
                    case "shortdesc":
                        result.update({"shortdesc": item["value"]})
                    case "longdesc":
                        result.update({"longdesc": item["value"], "state": int(item["state"])})
                # Detect last iteration.
                if len(result) == 7:
                    # TODO: Implement ordering support.
                    self.cursor.execute(
                        f"""
                        INSERT INTO `skills`
                                    (`employer`, `position`, `shortdesc`,
                                    `longdesc`, `category`, `subcategory`,
                                    `categoryorder`, `skillorder`, `state`)
                        VALUES      ('{result["employer"]}', '{result["position"]}', '{result["shortdesc"]}',
                                    '{result["longdesc"]}', '{result["category"]}', '{result["subcategory"]}',
                                    '1', '1', '{result["state"]}');
                        """)
            # Update skill.
            else:
                self.cursor.execute(
                    f"""
                        UPDATE `skills`
                        SET `{item["attr"]}` = '{item["value"]}',
                        `state` = {item["state"]}
                        WHERE `id` = {int(item["id"])}
                    """)
        
        # Commit changes.
        self.conn.commit()
        return

    def update_summary(self, form_data) -> None:
        """
        Updates the summary table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """

        # Transform from template.
        form_data = transform_get_id(form_data)
        counter = ""
        result = {}
        for item in form_data:
            if counter != item["id"]:
                counter = item["id"]
                result = {}
            
            # Delete summary.
            if "delete" in item["attr"]:
                self.cursor.execute(
                    f"""
                    DELETE FROM `summary`
                    WHERE `id` = {int(item["id"])};
                    """)
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

    def update_education(self, form_data) -> None:
        """
        Updates the education and focus tables.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """

        # Transform from template.
        form_data = transform_get_id(form_data)
        counter = ""
        result = {}
        for item in form_data:
            if counter != item["id"]:
                counter = item["id"]
                result = {}

            # Delete focus, and school (if necessary).
            if "delete" in item["attr"]:
                # Check for school.
                get_school = self.cursor.execute(
                    f"""
                    SELECT `school`
                    FROM `focus`
                    WHERE `id` = '{item["id"]}';
                    """)
                self.cursor.execute(
                    f"""
                    DELETE FROM `focus`
                    WHERE `id` = {int(item["id"])};
                    """)
                if len(get_school.fetchall()) <= 1:
                    self.cursor.execute(
                    f"""
                    DELETE FROM `schools`
                    WHERE `id` = {int(item["id"])};
                    """)
                self.cursor.execute(
                    f"""
                    DELETE FROM `focus`
                    WHERE `id` = {int(item["id"])};
                    """)
                
            # Create school.
            elif "new" in item["id"] and ("school" in item["attr"] or "location" in item["attr"]):
                # Create result based on current attribute value.
                match item["attr"]:
                    case "location":
                        result.update({"location": item["value"], "state": int(item["state"])})
                    case "school":
                        result.update({"school": item["value"], "state": int(item["state"])})
                # Detect last iteration.
                if len(result) == 3:
                    # Cleanup dates for (hidden) and 'Present' value detection.
                    if "date" in item["attr"]:
                        if item["value"] == "":
                            item["value"] = datetime.strptime("9999-01-01", "%Y-%m-%d")
                        if item["value"] == "hidden":
                            item["value"] = datetime.strptime("0001-01-01", "%Y-%m-%d")
                    # Check for school.
                    check_school = self.cursor.execute(
                        f"""
                        SELECT *
                        FROM `schools`
                        WHERE `school` = '{result["school"]}'
                        """)
                    if len(check_school.fetchall()) == 0:  # If no school.
                        self.cursor.execute(
                            f"""
                            INSERT INTO `schools`
                                        (`school`, `location`, `state`)
                            VALUES      ('{result["school"]}', '{result["location"]}', '{result["state"]}');
                            """)

                        # Commit changes.
                        self.conn.commit()
            
            # Create focus.
            elif "new" in item["id"]:
                # Create result based on current attribute value.
                match item["attr"]:
                    case "school":
                        # get ID from name.
                        item["value"] = self.query.query_id(item["value"], "school")
                        result.update({"school": item["value"]})
                    case "focus":
                        result.update({"focus": item["value"]})
                    case "startdate":
                        result.update({"startdate": item["value"]})
                    case "enddate":
                        result.update({"enddate": item["value"], "state": int(item["state"])})
                # Detect last iteration.
                if len(result) == 6:
                    # Cleanup dates for (hidden) and 'Present' value detection.
                    if "date" in item["attr"]:
                        if item["value"] == "":
                            item["value"] = datetime.strptime("9999-01-01", "%Y-%m-%d")
                        if item["value"] == "hidden":
                            item["value"] = datetime.strptime("0001-01-01", "%Y-%m-%d")
                        result["school"] = self.query.query_id(result["school"], "school")
                    self.cursor.execute(
                        f"""
                        INSERT INTO `focus`
                                    (`school`, `focus`,
                                    `startdate`, `enddate`, `state`)
                        VALUES      ('{result["school"]}', '{result["focus"]}',
                                    '{result["startdate"]}', '{result["enddate"]}', '{result["state"]}');
                        """)

            # Update focus.
            else:
                # Cleanup dates for (hidden) and 'Present' value detection.
                if "date" in item['attr']:
                    if item['value'] == '':
                        item['value'] = datetime.strptime('9999-01-01', '%Y-%m-%d')
                    if item['value'] == 'hidden':
                        item['value'] = datetime.strptime('0001-01-01', '%Y-%m-%d')
                # Detect if enough data to update school.
                if "location" in item["attr"] or "school" in item["attr"]:
                    self.cursor.execute(
                        f"""
                                UPDATE `schools`
                                SET {item['attr']} = '{item['value']}',
                                state = {item['state']}
                                WHERE id = {int(item['id'])}
                            """)
                # Detect if enough data to update focus.
                elif "delete" not in item['attr'] and "new" not in item['attr']:
                    self.cursor.execute(
                        f"""
                             UPDATE `focus`
                             SET {item['attr']} = '{item['value']}',
                             state = {item['state']}
                             WHERE id = {int(item['id'])}
                         """)

        # Commit changes.
        self.conn.commit()
        return

    def update_achievements(self, form_data) -> None:
        """
        Updates the achievements table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """

        # Transform from template.
        form_data = transform_get_id(form_data)
        counter = ""
        result = {}
        for item in form_data:
            if counter != item["id"]:
                counter = item["id"]
                result = {}
            
            # Delete achievement.
            if "delete" in item["attr"]:
                self.cursor.execute(
                    f"""
                     DELETE FROM `achievements`
                     WHERE `id` = {int(item["id"])};
                     """)
                
            # Create achievement.
            elif "new" in item["id"]:
                # Create result based on current attribute value.
                match item["attr"]:
                    case "position":
                        item["value"] = self.query.query_id(item["value"], "position")
                        result.update({"position": item["value"], "state": int(item["state"])})
                    case "employer":
                        item["value"] = self.query.query_id(item["value"], "employer")
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
                        INSERT INTO `achievements`
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
                        item["value"] = self.query.query_id(item["value"], "position")
                    case "employer":
                        item["value"] = self.query.query_id(item["value"], "employer")
                self.cursor.execute(
                    f"""
                         UPDATE `achievements`
                         SET {item['attr']} = '{item['value']}',
                         state = {item['state']}
                         WHERE id = {int(item['id'])}
                     """)

        # Commit changes.
        self.conn.commit()
        return

    def update_glossary(self, form_data) -> None:
        """
        Updates the glossary table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """

        # Transform from template.
        form_data = transform_get_id(form_data)
        counter = ""
        result = {}
        for item in form_data:
            if counter != item["id"]:
                counter = item["id"]
                result = {}
                
            # Delete term.
            if "delete" in item["attr"]:
                self.cursor.execute(
                    f"""
                   DELETE FROM `glossary`
                   WHERE `id` = {int(item["id"])};
                   """)
                
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
