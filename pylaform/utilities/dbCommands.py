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
            Return education list objects from database by school, focus, start_date, end_date
            :return: list
        """

        if len(self.result_positions) == 0:
            result = self.query(
                """
                    SELECT s.id, s.school, s.state, f.id, f.focus, f.start_date, f.end_date, f.state
                    FROM schools AS s
                    JOIN focus AS f on s.id = f.school
                    ORDER BY f.start_date DESC
                """
            )

            for school_id, school, focus_id, focus, start_date, end_date, state in result:
                self.result_positions.append({
                    "school_id": school_id,
                    "school": school,
                    "focus_id": focus_id,
                    "focus": focus,
                    "start_date": start_date,
                    "end_date": end_date,
                    "state": state,
                })

        return self.result_positions

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
                    SELECT id, category, subcategory, position, shortdescription, longdescription, state
                    FROM skills
                    ORDER BY categoryorder, skillorder ASC
                """
            )

            for skills_id, category, subcategory, position, shortdesc, longdesc, state in result:
                self.result_skills.append({
                    "id": skills_id,
                    "subcategory": subcategory,
                    "category": category,
                    "position": position,
                    "shortdesc": shortdesc,
                    "longdesc": longdesc,
                    "state": state
                })

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
            Return positions list objects from database by employer, position, start_date, end_date
            :return: list
        """

        if len(self.result_positions) == 0:
            result = self.query(
                """
                    SELECT e.id, e.employer, e.state, p.id, p.position, p.start_date, p.end_date, p.state
                    FROM employers AS e
                    JOIN positions AS p on e.id = p.employer
                    ORDER BY p.start_date DESC
                """
            )

            for employer_id, employer, employer_state, position_id, position, start_date, end_date, position_state in result:
                self.result_positions.append({
                    "employer_id": employer_id,
                    "employer": employer,
                    "employer_state": employer_state,
                    "position_id": position_id,
                    "position": position,
                    "start_date": start_date,
                    "end_date": end_date,
                    "position_state": position_state,
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
                    SELECT e.id, e.employer, p.id, p.position, a.id, a.shortdesc, a.longdesc, a.state
                    FROM employers AS e
                    JOIN positions AS p ON e.id = p.employer
                    JOIN achievements AS a ON p.id = a.position
                    ORDER BY p.start_date DESC
                """
            )

            for employer_id, employer, position_id, position, achievment_id, shortdesc, longdesc, state in result:
                self.result_achievements.append({
                    "employer_id": employer_id,
                    "employer": employer,
                    "position_id": position_id,
                    "position": position,
                    "achievement_id": achievment_id,
                    "shortdesc": shortdesc,
                    "longdesc": longdesc,
                    "state": state,
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
        certifications = [{sub['id']: {"certification": sub['certification'], "year": datetime(sub['year']).isoformat(), "state": sub['state'], "is_new": sub['is_new']}} for sub in form_data]
        for certification in certifications:
            if cert['is_new']:
                self.cursor.execute(
                    f"""INSERT INTO certifications (id, certification, year, state)
                    VALUES (cert['id'], cert['certification'], cert['year'], cert['state'])"""
                )
            else:
                self.cursor.execute(
                    f"""
                        UPDATE certifications
                        SET certification = '{cert['certification']}',
                        year = '{cert['year']}',
                        state = {sub['state']}
                        WHERE id = {cert['id']}
                    """
                )

        self.conn.commit()
        self.result_certification = []
