import json
import mariadb
from tenacity import retry, stop_after_delay
from werkzeug.datastructures import ImmutableMultiDict


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
                    SELECT certification, year, state
                    FROM certifications
                """)

            for certification, year, state in result:
                self.result_certification.append({
                    "certification": certification,
                    "year": year,
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
                    SELECT s.school, s.state, f.focus, f.start_date, f.end_date, f.state
                    FROM schools AS s
                    JOIN focus AS f on s.id = f.school
                    ORDER BY f.start_date DESC
                """
            )

            for school, focus, start_date, end_date, state in result:
                self.result_positions.append({
                    "school": school,
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
                    SELECT attr, value, state
                    FROM identification
                """)

            for attr, value, state in result:
                self.result_identification.append({
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
                    SELECT short_desc, long_desc, state
                    FROM summary
                    ORDER BY summaryorder ASC
                """
            )

            for short_desc, long_desc, state in result:
                self.result_summary.append({
                    "short_desc": short_desc,
                    "long_desc": long_desc,
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
                    SELECT category, subcategory, position, short_description, long_description, state
                    FROM skills
                    ORDER BY categoryorder, skillorder ASC
                """
            )

            for category, subcategory, position, short_desc, long_desc, state in result:
                self.result_skills.append({
                    "subcategory": subcategory,
                    "category": category,
                    "position": position,
                    "short_desc": short_desc,
                    "long_desc": long_desc,
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
                    SELECT term, url, description, state
                    FROM glossary
                    ORDER BY term ASC
                """
            )

            for term, url, description, state in result:
                self.result_glossary.append({
                    "term": term,
                    "url": url,
                    "description": description,
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
                    SELECT e.employer, e.state, p.position, p.start_date, p.end_date, p.state
                    FROM employers AS e
                    JOIN positions AS p on e.id = p.employer
                    ORDER BY p.start_date DESC
                """
            )

            for employer, employer_state, position, start_date, end_date, position_state in result:
                self.result_positions.append({
                    "employer": employer,
                    "employer_state": employer_state,
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
                    SELECT e.employer, p.position, a.short_description, a.long_description, a.state
                    FROM employers AS e
                    JOIN positions AS p ON e.id = p.employer
                    JOIN achievements AS a ON p.id = a.position
                    ORDER BY p.start_date DESC
                """
            )

            for employer, position, short_desc, long_desc, state in result:
                self.result_achievements.append({
                    "employer": employer,
                    "position": position,
                    "short_desc": short_desc,
                    "long_desc": long_desc,
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

        for i, name in enumerate(form_data):
            if "_enabled" not in name:
                self.cursor.execute(
                    f"""
                    UPDATE `identification`
                    SET `value` = '{self.conn.escape_string(list(form_data.listvalues())[i][0])}'
                    WHERE `attr` = '{name}';""")
                self.result_identification = []
