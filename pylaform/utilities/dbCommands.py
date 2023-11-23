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
                    SELECT c.certification, c.year, en.state
                    FROM certifications AS c
                    JOIN enabled AS en on c.id = en.id
                    WHERE en.group_name = "certification"
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
                    SELECT s.school, s.focus, f.start_date, f.end_date
                    FROM schools AS s
                    JOIN focus AS f on s.id = f.school
                    JOIN enabled AS en on s.id = en.id
                    WHERE en.gruop_name = "education"
                    ORDER BY f.start_date DESC
                """
            )

            for school, focus, start_date, end_date, enabled in result:
                self.result_positions.append({
                    "school": school,
                    "focus": focus,
                    "start_date": start_date,
                    "end_date": end_date,
                    "enabled": enabled,
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
                    SELECT i.attr, i.value, en.state
                    FROM identification AS i
                    JOIN enabled AS en on i.id = en.id
                    WHERE en.group_name = "identification"
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
                    SELECT s.short_desc, s.long_desc, en.state
                    FROM summary AS s
                    JOIN enabled AS en on s.id = en.id
                    WHERE en.group_name = "summary"
                    ORDER BY s.order ASC
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
                    SELECT s.category, s.subcategory, s.position, s.short_description, s.long_description, en.state
                    FROM skills AS s
                    JOIN enabled AS en on s.id = en.id
                    WHERE en.group_name = "skills"
                    ORDER BY s.categoryorder, s.skillorder ASC
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
                    SELECT g.term, g.url, g.description, en.state
                    FROM glossary AS g
                    JOIN enabled AS en on g.id = en.id
                    WHERE en.group_name = "glossary"
                    ORDER BY g.term ASC
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
                    SELECT e.employer, p.position, p.start_date, p.end_date, en.state
                    FROM employers AS e
                    JOIN positions AS p on e.id = p.employer
                    JOIN enabled as en on p.id = en.id
                    WHERE en.group_name = "positions"
                    ORDER BY p.start_date DESC
                """
            )

            for employer, position, start_date, end_date, state in result:
                self.result_positions.append({
                    "employer": employer,
                    "position": position,
                    "start_date": start_date,
                    "end_date": end_date,
                    "state": state,
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
                    SELECT e.employer, p.position, a.short_description, a.long_description, en.state
                    FROM employers AS e
                    JOIN positions AS p ON e.id = p.employer
                    JOIN achievements AS a ON p.id = a.position
                    JOIN enabled AS en ON a.id = en.id
                    WHERE en.group_name = "achievements"
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
                self.result_enabled.append({
                    "group": group,
                    "id": row_id,
                    "state": state,
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
