import json
import mariadb
from tenacity import retry, stop_after_delay


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
        self.result_identification = {}
        self.result_skills = []
        self.result_achievements = []
        self.result_glossary = []
        self.result_positions = []
        self.result_summary = []

    @retry
    def query(self, query):
        try:
            self.cursor.execute(query)
        except mariadb.Error as e:
            print(f"Error querying database: {e}")
            raise
        return self.cursor

    def identification(self):
        """
            Return identification dictionary from database.
            :return: dict
        :return:
        """

        if len(self.result_identification) == 0:
            result = self.query(
                """
                    SELECT *
                    FROM identification
                """)

            for name, phone, www, description, email, location in result:
                self.result_identification.update({
                    "name": name,
                    "phone": phone,
                    "www": www,
                    "description": description,
                    "email": email,
                    "location": location,
                })

        return self.result_identification

    def summary(self):
        """
            Return glossary list objects from database
            :return: list
        """

        if len(self.result_summary) == 0:
            result = self.query(
                """
                    SELECT short_desc, long_desc
                    FROM summary
                    ORDER BY id ASC
                """
            )

            for short_desc, long_desc in result:
                self.result_summary.append({
                    "short_desc": short_desc,
                    "long_desc": long_desc,
                })

        return self.result_summary

    def skills(self):
        """
            Return unrefined skills list from database
            :return: list
        """

        if len(self.result_skills) == 0:
            result = self.query(
                """
                    SELECT category, subcategory, position, short_description, long_description
                    FROM skills
                    ORDER BY category, short_description ASC
                """
            )

            for category, subcategory, position, short_desc, long_desc in result:
                self.result_skills.append({
                    "subcategory": subcategory,
                    "category": category,
                    "position": position,
                    "short_desc": short_desc,
                    "long_desc": long_desc,
                })

        return self.result_skills

    def glossary(self):
        """
            Return glossary list objects from database
            :return: list
        """

        if len(self.result_glossary) == 0:
            result = self.query(
                """
                    SELECT term, url, description
                    FROM glossary
                """
            )

            for term, url, description in result:
                self.result_glossary.append({
                    "term": term,
                    "url": url,
                    "description": description,
                })

        return self.result_glossary

    def positions(self):
        """
            Return positions list objects from database by employer, position, start_date, end_date
            :return: list
        """

        if len(self.result_positions) == 0:
            result = self.query(
                """
                    SELECT e.employer, p.position, p.start_date, p.end_date
                    FROM employers AS e
                    JOIN positions AS p on e.id = p.employer
                    ORDER BY p.start_date DESC
                """
            )

            for employer, position, start_date, end_date in result:
                self.result_positions.append({
                    "employer": employer,
                    "position": position,
                    "start_date": start_date,
                    "end_date": end_date,
                })

        return self.result_positions

    def achievements(self):
        """
            Return achievements list objects from database by employer and position
            :return: list
        """

        if len(self.result_achievements) == 0:
            result = self.query(
                """
                    SELECT e.employer, p.position, a.short_description, a.long_description
                    FROM employers AS e
                    JOIN positions AS p ON e.id = p.employer
                    JOIN achievements AS a ON p.id = a.position
                    ORDER BY p.start_date DESC
                """
            )

            for employer, position, short_desc, long_desc in result:
                self.result_achievements.append({
                    "employer": employer,
                    "position": position,
                    "short_desc": short_desc,
                    "long_desc": long_desc,
                })

        return self.result_achievements
