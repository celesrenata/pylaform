import json

import mariadb
from datetime import datetime
from tenacity import retry, stop_after_delay
from .commands import transform_get_id


class Queries:
    """
        Connect to the Database and return basic selections, to be improved for user specifics.
        :return: Dictionary
    """
    @retry(stop=(stop_after_delay(10)))
    def __init__(self):
        try:
            resume_config = {}
            with open("config.json", "r") as json_file:
                resume_config = json.load(json_file)
        except Exception as e:
            raise e
        try:
            conn = mariadb.connect(
                user=resume_config["username"],
                password=resume_config["password"],
                host=resume_config["server"],
                port=resume_config["port"],
                database=resume_config["database"]
            )

        except mariadb.Error as e:
            raise f"Error connecting to MariaDB Platform: {e}"
        self.cursor = conn.cursor()
        self.conn = conn
        self.result_certification = []
        self.result_education = []
        self.result_identification = []
        self.result_skills = []
        self.result_achievements = []
        self.result_glossary = []
        self.result_positions = []
        self.result_summary = []
        self.result_enabled = []
        self.result_enabled_contact = []

    @retry
    def query(self, query):
        try:
            self.cursor.execute(query)
        except mariadb.Error as e:
            print(f"Error querying database: {e}")
            raise
        return self.cursor

    def get_certifications(self):
        """
        Return certification list from database
        :return: list
        """
        if len(self.result_certification) == 0:
            result = self.query(
                """
                    SELECT id, certification, year, state
                    FROM certifications
                """)

            for certification_id, certification, year, state in result:
                self.result_certification.append({
                    "id": certification_id,
                    "attr": "certification",
                    "value": certification,
                    "state": state,
                })
                self.result_certification.append({
                    "id": certification_id,
                    "attr": "year",
                    "value": year,
                    "state": state,
                })

        return self.result_certification

    def get_education(self):
        """
            Return education list objects from database by school, focus, startdate, enddate
            :return: list
        """

        if len(self.result_education) == 0:
            result = self.query(
                """
                    SELECT s.id, s.school, s.state, f.id, f.focus, f.startdate, f.enddate, f.state
                    FROM schools AS s
                    JOIN focus AS f on s.id = f.school
                    ORDER BY f.startdate DESC
                """
            )

            for schoolid, school, schoolstate, focusid, focus, startdate, enddate, focusstate in result:
                self.result_education.append({
                    "id": schoolid,
                    "attr": "school",
                    "value": school,
                    "state": schoolstate,
                })
                self.result_education.append({
                    "id": focusid,
                    "attr": "focus",
                    "value": focus,
                    "state": focusstate,
                })
                self.result_education.append({
                    "id": focusid,
                    "attr": "startdate",
                    "value": startdate,
                    "state": focusstate,
                })
                self.result_education.append({
                    "id": focusid,
                    "attr": "enddate",
                    "value": enddate,
                    "state": focusstate,
                })

        return self.result_education

    def get_identification(self):
        """
            Return identification list from database.
            :return: list
        :return:
        """

        if len(self.result_identification) == 0:
            result = self.query(
                """
                    SELECT id, attr, value, state
                    FROM identification
                """)

            for identification_id, attr, value, state in result:
                self.result_identification.append({
                    "id": identification_id,
                    "attr": attr,
                    "value": value,
                    "state": state,
                })

        return self.result_identification

    def get_summary(self):
        """
            Return glossary list objects from database
            :return: list
        """

        if len(self.result_summary) == 0:
            result = self.query(
                """
                    SELECT id, shortdesc, longdesc, state
                    FROM summary
                    ORDER BY summaryorder ASC
                """
            )

            for summary_id, shortdesc, longdesc, state in result:
                self.result_summary.append({
                    "id": summary_id,
                    "attr": "shortdesc",
                    "value": shortdesc,
                    "state": state,
                })
                self.result_summary.append({
                    "id": summary_id,
                    "attr": "longdesc",
                    "value": longdesc,
                    "state": state,
                })

        return self.result_summary

    def get_skills(self):
        """
            Return unrefined skills list from database
            :return: list
        """

        if len(self.result_skills) == 0:
            result = self.query(
                """
                    SELECT id, category, subcategory, position, shortdesc, longdesc, state
                    FROM skills
                    ORDER BY categoryorder, skillorder ASC
                """
            )

            for skills_id, category, subcategory, position, shortdesc, longdesc, state in result:
                self.result_skills.append({
                    "id": skills_id,
                    "attr": "category",
                    "value": category,
                    "state": state})
                self.result_skills.append({
                    "id": skills_id,
                    "attr": "subcategory",
                    "value": subcategory,
                    "state": state})
                self.result_skills.append({
                    "id": skills_id,
                    "attr": "position",
                    "value": position,
                    "state": state})
                self.result_skills.append({
                    "id": skills_id,
                    "attr": "shortdesc",
                    "value": shortdesc,
                    "state": state})
                self.result_skills.append({
                    "id": skills_id,
                    "attr": "longdesc",
                    "value": longdesc,
                    "state": state})

        return self.result_skills

    def get_glossary(self):
        """
            Return glossary list objects from database
            :return: list
        """

        if len(self.result_glossary) == 0:
            result = self.query(
                """
                    SELECT id, term, url, description, state
                    FROM glossary
                    ORDER BY term ASC
                """
            )

            for glossary_id, term, url, description, state in result:
                self.result_glossary.append({
                    "id": glossary_id,
                    "attr": "term",
                    "value": term,
                    "state": state,
                })
                self.result_glossary.append({
                    "id": glossary_id,
                    "attr": "url",
                    "value": url,
                    "state": state,
                })
                self.result_glossary.append({
                    "id": glossary_id,
                    "attr": "description",
                    "value": description,
                    "state": state,
                })

        return self.result_glossary

    def get_positions(self):
        """
            Return positions list objects from database by employer, position, startdate, enddate
            :return: list
        """

        if len(self.result_positions) == 0:
            result = self.query(
                """
                    SELECT e.id, e.employer, e.state, p.id, p.position, p.startdate, p.enddate, p.state
                    FROM employers AS e
                    JOIN positions AS p on e.id = p.employer
                    ORDER BY p.startdate DESC
                """
            )

            for employer_id, employer, employer_state, position_id, position, start_date, end_date, position_state in result:
                self.result_positions.append({
                    "id": employer_id,
                    "attr": "employer",
                    "value": employer,
                    "state": employer_state})
                self.result_positions.append({
                    "id": position_id,
                    "attr": "position",
                    "value": position,
                    "state": position_state})
                self.result_positions.append({
                    "id": position_id,
                    "attr": "startdate",
                    "value": start_date,
                    "state": position_state})
                self.result_positions.append({
                    "id": position_id,
                    "attr": "enddate",
                    "value": end_date,
                    "state": position_state,
                })

        return self.result_positions

    def get_achievements(self):
        """
            Return achievements list objects from database by employer and position
            :return: list
        """

        if len(self.result_achievements) == 0:
            result = self.query(
                """
                    SELECT e.id, e.employer, e.state as employer_state, p.id as position_id, p.position, p.state as position_state, a.id as achievement_id, a.shortdesc, a.longdesc, a.state as achievement_state
                    FROM achievements a
                    JOIN positions p ON a.position = p.id AND a.employer = p.employer
                    JOIN employers e ON a.employer = e.id;
                """
            )

            for employer_id, employer, employer_state, position_id, position, position_state, achievement_id, shortdesc, longdesc, achievement_state in result:
                self.result_achievements.append({
                    "id": employer_id,
                    "attr": "employer",
                    "value": employer,
                    "state": employer_state,
                })
                self.result_achievements.append({
                    "id": position_id,
                    "attr": "position",
                    "value": position,
                    "state": position_state,
                })
                self.result_achievements.append({
                    "id": achievement_id,
                    "attr": "shortdesc",
                    "value": shortdesc,
                    "state": achievement_state,
                })
                self.result_achievements.append({
                    "id": achievement_id,
                    "attr": "longdesc",
                    "value": longdesc,
                    "state": achievement_state,
                })

        return self.result_achievements

    def get_enabled(self, target_group):
        """
        Return enabled elements for requested group.
        :param str target_group: ['achievements', 'certifications', 'education', 'employment', 'glossary', 'information', 'skills', 'summary']
        :return:
        """

        if len(self.result_enabled) == 0:
            result = self.query(
                """
                    SELECT *
                    FROM enabled
                """
            )

            for group, row_id, state in result:
                if state == 1:
                    state_bool = True
                else:
                    state_bool = False
                self.result_enabled.append({
                    "group": group,
                    "id": row_id,
                    "state": state_bool,
                })

        return self.result_enabled

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
        self.result_identification = []

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
        self.result_certification = []

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
                self.cursor.execute(
                    f"""
                        UPDATE positions
                        SET {item['attr']} = '{item['value']}',
                        state = {item['state']}
                        WHERE id = {item['id']}
                    """
                )

        self.conn.commit()
        self.result_certification = []

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
        self.result_skills = []

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
        self.result_summary = []

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
                self.cursor.execute(
                    f"""
                         UPDATE focus
                         SET {item['attr']} = '{item['value']}',
                         state = {item['state']}
                         WHERE id = {item['id']}
                     """
                )

        self.conn.commit()
        self.result_education = []
