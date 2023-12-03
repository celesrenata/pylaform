import sqlite3
from sqlite3 import Cursor, Connection

from tenacity import retry, stop_after_delay

from . import connect


class Get:
    """
    Collection of queries to run against the local database.
    Actions: SELECT
    :return None: None
    """

    @retry(stop=(stop_after_delay(10)))
    def __init__(self) -> None:
        self.conn: Connection = connect.db()
        self.cursor: Cursor = self.conn.cursor()
        self.result_certifications: list[dict[str, str | int | bool]] = []
        self.result_education: list[dict[str, str | int | bool]] = []
        self.result_identification: list[dict[str, str | int | bool]] = []
        self.result_skills: list[dict[str, str | int | bool]] = []
        self.result_achievements: list[dict[str, str | int | bool]] = []
        self.result_glossary: list[dict[str, str | int | bool]] = []
        self.result_positions: list[dict[str, str | int | bool]] = []
        self.result_summary: list[dict[str, str | int | bool]] = []

    def purge_cache(self, table: str) -> None:
        """
        Purges local cache from python application for associated table
        :param str table:  Name of table to purge.
        :return None: None
        """

        match table:
            case "certifications":
                self.result_certifications = []
            case "education":
                self.result_education = []
            case "identification":
                self.result_identification = []
            case "skills":
                self.result_skills = []
            case "achievements":
                self.result_achievements = []
            case "glossary":
                self.result_glossary = []
            case "positions":
                self.result_positions = []
            case "summary":
                self.result_summary = []

    @retry
    def query(self, query: str) -> sqlite3.Cursor:
        """
        Query worker that handles all main SELECT requests.
        :param str query: Query String.
        :return sqlite3.Cursor: Iterable cursor.
        """

        try:
            self.cursor.execute(query)
        except sqlite3.Error as e:
            print(f"Error querying database: {e}")
            raise
        return self.cursor

    def query_id(self, value: str, attr: str) -> int:
        # TODO: Consider refactoring to use the attribute as the FROM/WHERE as "attr + 's'"
        """
        Queries the associated name to return the ID in order to detect if new or not.
        :param str value: Name to search.
        :param str attr: Attribute to search.
        :return int: ID associated with Name.
        """

        sub_result: sqlite3.Cursor = self.query()
        if attr == "employer":
            sub_result = self.query(
                f"""
                SELECT `id`
                FROM `employer`
                WHERE `employer` = '{value}';
                """)
        if attr == "position":
            sub_result = self.query(
                f"""
                SELECT `id`
                FROM `position`
                WHERE `position` = '{value}'
                """)
        if attr == "school":
            sub_result = self.query(
                f"""
                SELECT `id`
                FROM `school`
                WHERE `school` = '{value}'
                """)
        result: int = 0
        for item in sub_result:
            result = int(item[0])
        return result

    def query_name(self, value: int, attr: str) -> str:
        # TODO: Consider refactoring to use the attribute as the FROM/WHERE as "attr + 's'"
        """
        Queries the associated ID to return the name for display.
        :param int value: ID to search.
        :param str attr: Attribute to search.
        :return str: Name associated with ID.
        """

        result: str = ""
        sub_result: sqlite3.Cursor = self.query()
        if attr == "employer":
            sub_result = self.query(
                f"""
                SELECT `employer`
                FROM `employer`
                WHERE `id` = '{value}';
                """)
        if attr == "position":
            sub_result = self.query(
                f"""
                SELECT `position`
                FROM `position`
                WHERE `id` = '{value}'
                """)
        for item in sub_result:
            result = str(item[0])
        return result

    def get_certifications(self) -> list[dict[str, str | int | bool]]:
        """
        Return certification list from database.
        :return list[dict[str, str | int | bool]]: Raw return grouped by 'id/attr/value/state.'
        """

        if len(self.result_certifications) == 0:
            result = self.query(
                """
                SELECT `id`, `certification`, `year`, `state`
                FROM `certification`
                """)

            # Create raw list based on id/attr/value/state
            for certification_id, certification, year, state in result:
                self.result_certifications.append({
                    "id": certification_id,
                    "attr": "certification",
                    "value": certification,
                    "state": state,
                })
                self.result_certifications.append({
                    "id": certification_id,
                    "attr": "year",
                    "value": year,
                    "state": state,
                })

        return self.result_certifications

    def get_education(self) -> list[dict[str, str | int | bool]]:
        """
        Return education NESTED list objects from database by school.
        :return list[dict[str, str | int | bool]]: Raw return grouped by 'id/attr/value/state.'
        """

        if len(self.result_education) == 0:
            result: Cursor = self.query(
                """
                SELECT f.id, f.focus, f.startdate, f.enddate, f.state,
                       s.id, s.school, s.location, s.state
                FROM `school` AS s
                JOIN `focus` AS f on s.id = f.school
                ORDER BY f.startdate DESC
                """)

            # Create raw NESTED list based on 'origin_ + id/attr/value/state.'
            for (focusid, focus, startdate, enddate, focusstate,
                 schoolid, school, location, schoolstate) in result:
                self.result_education.append({
                    "id": "school_" + str(schoolid),
                    "attr": "schoolname",
                    "value": school,
                    "state": schoolstate,
                })
                self.result_education.append({
                    "id": "school_" + str(schoolid),
                    "attr": "location",
                    "value": location,
                    "state": schoolstate,
                })
                self.result_education.append({
                    "id": "focusid_" + str(focusid),
                    "attr": "focus",
                    "value": focus,
                    "state": focusstate,
                })
                self.result_education.append({
                    "id": "focusid_" + str(focusid),
                    "attr": "startdate",
                    "value": startdate,
                    "state": focusstate,
                })
                self.result_education.append({
                    "id": "focusid_" + str(focusid),
                    "attr": "enddate",
                    "value": enddate,
                    "state": focusstate,
                })
                self.result_education.append({
                    "id": "focusid_" + str(focusid),
                    "attr": "enddate",
                    "value": enddate,
                    "state": focusstate,
                })

        return self.result_education

    def get_identification(self) -> list[dict[str, str | int | bool]]:
        """
        Return identification list objects from database.
        :return list[dict[str, str | int | bool]]: Raw return grouped by 'id/attr/value/state.'
        """

        if len(self.result_identification) == 0:
            result: Cursor = self.query(
                """
                SELECT `id`, `attr`, `value`, `state`
                FROM `identification`
                """)

            # Create raw list based on 'id/attr/value/state.'
            for identification_id, attr, value, state in result:
                if state == 1:
                    state = True
                else:
                    state = False

                self.result_identification.append({
                    "id": identification_id,
                    "attr": attr,
                    "value": value,
                    "state": state,
                })
                self.result_identification.append({
                    "id": identification_id,
                    "attr": "contacttype",
                    "value": attr,
                    "state": state,
                })

        return self.result_identification

    def get_summary(self) -> list[dict[str, str | int | bool]]:
        """
        Return summary list objects from database.
        :return list[dict[str, str | int | bool]]: Raw return grouped by 'id/attr/value/state.'
        """

        if len(self.result_summary) == 0:
            result: Cursor = self.query(
                """
                SELECT `id`, `shortdesc`, `longdesc`, `state`
                FROM `summary`
                ORDER BY `summaryorder`
                """)

            # Create raw list based on 'id/attr/value/state.'
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

    def get_skills(self) -> list[dict[str, str | int | bool]]:
        """
        Return skills list objects from database.
        :return list[dict[str, str | int | bool]]: Raw return grouped by 'id/attr/value/state.'
        """

        if len(self.result_skills) == 0:
            result: Cursor = self.query(
                """
                SELECT s.id, s.category, s.subcategory, e.employer, p.position, s.shortdesc, s.longdesc, s.state
                FROM `skill` s, `position` p, `employer` e
                WHERE p.id = s.position and e.id = s.employer
                ORDER BY `categoryorder`, `skillorder`;
                """)

            # Create raw list based on 'id/attr/value/state.'
            for skills_id, category, subcategory, employer, position, shortdesc, longdesc, state in result:
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
                    "attr": "employer",
                    "value": employer,
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

    def get_glossary(self) -> list[dict[str, str | int | bool]]:
        """
        Return glossary list objects from database.
        :return list[dict[str, str | int | bool]]: Raw return grouped by 'id/attr/value/state.'
        """

        if len(self.result_glossary) == 0:
            result: Cursor = self.query(
                """
                SELECT `id`, `term`, `url`, `description`, `state`
                FROM `glossary`
                ORDER BY `term`;
                """)

            # Create raw list based on 'id/attr/value/state.'
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

    def get_positions(self) -> list[dict[str, str | int | bool]]:
        """
        Return positions NESTED list objects from database by school.
        :return list[dict[str, str | int | bool]]: Raw return grouped by 'id/attr/value/state.'
        """

        if len(self.result_positions) == 0:
            result: Cursor = self.query(
                """
                SELECT e.id, e.employer, e.location, e.state,
                       p.id, p.position, p.startdate, p.enddate, p.state
                FROM `employer` AS e
                JOIN `position` AS p on e.id = p.employer
                ORDER BY p.startdate DESC
                """)

            # Create raw NESTED list based on 'origin_ + id/attr/value/state.'
            for (employer_id, employer, location, employer_state,
                 position_id, position, start_date, end_date, position_state) in result:
                self.result_positions.append({
                    "id": "employer_" + str(employer_id),
                    "attr": "employername",
                    "value": employer,
                    "state": employer_state})
                self.result_positions.append({
                    "id": "employer_" + str(employer_id),
                    "attr": "location",
                    "value": location,
                    "state": employer_state})
                self.result_positions.append({
                    "id": "position_" + str(position_id),
                    "attr": "positionname",
                    "value": position,
                    "state": position_state})
                self.result_positions.append({
                    "id": "position_" + str(position_id),
                    "attr": "startdate",
                    "value": start_date,
                    "state": position_state})
                self.result_positions.append({
                    "id": "position_" + str(position_id),
                    "attr": "enddate",
                    "value": end_date,
                    "state": position_state,
                })

        return self.result_positions

    def get_achievements(self) -> list[dict[str, str | int | bool]]:
        """
        Return achievements NESTED list objects from database by school.
        :return list[dict[str, str | int | bool]]: Raw return grouped by 'id/attr/value/state.'
        """

        if len(self.result_achievements) == 0:
            result: Cursor = self.query(
                """
                SELECT e.id, e.employer, e.state as employer_state,
                       p.id as position_id, p.position, p.state as position_state,
                       a.id as achievement_id, a.shortdesc, a.longdesc, a.state as achievement_state
                FROM `achievement` a
                JOIN `position` p ON a.position = p.id AND a.employer = p.employer
                JOIN `employer` e ON a.employer = e.id;
                """)

            # Create raw NESTED list based on 'origin_ + id/attr/value/state.'
            for (employer_id, employer, employer_state,
                 position_id, position, position_state,
                 achievement_id, shortdesc, longdesc, achievement_state) in result:
                self.result_achievements.append({
                    "id": "employer_" + str(employer_id),
                    "attr": "employername",
                    "value": employer,
                    "state": employer_state,
                })
                self.result_achievements.append({
                    "id": "position_" + str(position_id),
                    "attr": "positionname",
                    "value": position,
                    "state": position_state,
                })
                self.result_achievements.append({
                    "id": "achievement_" + str(achievement_id),
                    "attr": "shortdesc",
                    "value": shortdesc,
                    "state": achievement_state,
                })
                self.result_achievements.append({
                    "id": "achievement_" + str(achievement_id),
                    "attr": "longdesc",
                    "value": longdesc,
                    "state": achievement_state,
                })

        return self.result_achievements
