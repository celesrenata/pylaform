import sqlite3
import time
from sqlite3 import Cursor, Connection
import logging

from . import connect

# Set up logger
logger = logging.getLogger(__name__)

class Queries:
    """
    Collection of queries to run against the local database.
    Actions: SELECT
    :return None: None
    """

    def __init__(self) -> None:
        """Initialize the query class with a fresh database connection."""
        # Initialize cache variables first
        self.result_dropdown = []
        self.result_certifications: list[dict[str, str | int | bool]] = []
        self.result_education: list[dict[str, str | int | bool]] = []
        self.result_employers: list[dict[str, str | int | bool]] = []
        self.result_identification: list[dict[str, str | int | bool]] = []
        self.result_skills: list[dict[str, str | int | bool]] = []
        self.result_achievements: list[dict[str, str | int | bool]] = []
        self.result_glossary: list[dict[str, str | int | bool]] = []
        self.result_positions: list[dict[str, str | int | bool]] = []
        self.result_summary: list[dict[str, str | int | bool]] = []
        self.read_only = False

        # Establish database connection
        try:
            self.conn: Connection = connect.db()
            self.cursor: Cursor = self.conn.cursor()
        except sqlite3.OperationalError as e:
            if "readonly database" in str(e):
                logger.warning("Opening database in read-only mode")
                self.conn: Connection = connect.db(read_only=True)
                self.cursor: Cursor = self.conn.cursor()
                self.read_only = True
            else:
                logger.error(f"Failed to initialize database connection: {str(e)}")
                # Initialize with None values to prevent attribute errors
                self.conn = None
                self.cursor = None
                raise


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
            case "dropdown":
                self.result_dropdown = []

    def query(self, query: str) -> sqlite3.Cursor:
        """
        Query worker that handles all main SELECT requests.
        :param str query: Query String.
        :return sqlite3.Cursor: Iterable cursor.
        """
        max_attempts = 3
        attempt = 0
        last_error = None

        while attempt < max_attempts:
            try:
                # Ensure we have a valid connection
                if not self.conn or not self.cursor:
                    self.conn = connect.get_fresh_connection()
                    self.cursor = self.conn.cursor()

                # Execute the query
                self.cursor.execute(query)
                return self.cursor

            except sqlite3.Error as e:
                last_error = e
                attempt += 1
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Database error (attempt {attempt}/{max_attempts}): {str(e)}")

                # Brief delay before retry
                time.sleep(0.5)

                # Try to refresh the connection
                try:
                    if self.conn:
                        self.conn.close()
                    self.conn = connect.get_fresh_connection()
                    self.cursor = self.conn.cursor()
                except Exception as conn_error:
                    logger.error(f"Failed to refresh connection: {str(conn_error)}")

        # If we get here, all attempts failed
        print(f"Error querying database after {max_attempts} attempts: {last_error}")
        raise last_error if last_error else sqlite3.Error("Unknown database error")

    def query_id(self, value: str, attr: str) -> int:
        # TODO: Consider refactoring to use the attribute as the FROM/WHERE as "attr + 's'"
        """
        Queries the associated name to return the ID in order to detect if new or not.
        :param str value: Name to search.
        :param str attr: Attribute to search.
        :return int: ID associated with Name.
        """

        sub_result: Cursor = self.query("")
        if attr == "employer":
            sub_result = self.query(
                f"""
                SELECT `id`
                FROM `employer`
                WHERE employer = '{value}';
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
                FROM school
                WHERE `name` = '{value}'
                """ )
        if attr == "focus":
            sub_result = self.query(
                f"""
                SELECT `id`
                FROM `focus`
                WHERE `name` = '{value}'
                """)
        result: int = 0
        for item in sub_result:
            result = int(item[0])
        return result

    def query_name(self, value: int | str, attr: str) -> str:
        """
        Queries the associated ID to return the name for display.
        :param value: ID to search (can be integer or string with ID).
        :param str attr: Attribute to search.
        :return str: Name associated with ID.
        """
        # Handle IDs in format like "employer_1" by extracting the numeric part
        if isinstance(value, str) and "_" in value:
            try:
                value = int(value.split("_")[1])
            except (IndexError, ValueError):
                print(f"WARNING: Could not extract ID from '{value}', using as is")

        sub_result = None
        result = ""

        if attr == "employer":
            sub_result = self.query(
                f"""
                SELECT `employer`
                FROM `employer`
                WHERE `id` = {value};
                """)
        elif attr == "position":
            sub_result = self.query(
                f"""
                SELECT `position`
                FROM `position`
                WHERE `id` = {value}
                """)
        elif attr == "school":
            sub_result = self.query(
                f"""
                SELECT `name`
                FROM `school`
                WHERE `id` = {value}
                """)
        elif attr == "focus":
            sub_result = self.query(
                f"""
                SELECT `name`
                FROM `focus`
                WHERE `id` = {value}
                """)

        if sub_result:
            for item in sub_result:
                result = str(item[0])

        return result

    def row_count(self, table: str, column: str, value: str | int) -> int:
        """
        returns row count for basic Select From Where clauses.
        :param str table: Table name.
        :param str column: Column name.
        :param str | int value: Value to search.
        :return int: Row count.
        """

        try:
            value = int(value)
            response = self.cursor.execute(
                f"""
                SELECT * 
                FROM `{table}`
                WHERE `{column}` = {value}
                """)

        except ValueError:
            response = self.cursor.execute(
                f"""
                SELECT * 
                FROM `{table}`
                WHERE `{column}` = '{value}'
                """)

        return len(response.fetchall())

    def get_options(self, tables: list[str], columns: list[str]) -> dict[str, list[dict[int, str]]]:
        """
        Returns all results under given column.
        :param list[str] tables: Table name.
        :param list[str] columns: Column name.
        :return dict[str, list[dict[int, str]]]: List of all values under column.
        """
        result: dict = {}
        for i, table in enumerate(tables):
            # Skip special case 'achievement' which is just a hint for employer-position mapping
            if table == "achievement":
                continue

            if table == "position" and columns[i] == "position":
                # For positions, include employer ID information
                response = self.query(
                    """
                    SELECT p.id, p.position, p.employer
                    FROM position p
                    ORDER BY p.position
                    """)
                result.update({
                    tables[i]: [
                        {"id": int(item[0]), "name": item[1], "employer": item[2]}
                        for item in response.fetchall()
                    ]
                })
            else:
                response = self.query(
                    f"""
                    SELECT `id`, `{columns[i]}`
                    FROM `{tables[i]}`
                    ORDER BY `{columns[i]}`""")
                result.update({tables[i]: [{"id": int(item[0]), "name": item[1]} for item in response.fetchall()]})

            # If we're getting position data for achievements, also add employer-position mappings
            if table == "position" and "achievement" in tables:
                # Create an employer-position mapping
                employer_positions = {}
                for position in result[table]:
                    employer_id = position.get("employer")
                    if employer_id:
                        if employer_id not in employer_positions:
                            employer_positions[employer_id] = []
                        employer_positions[employer_id].append(position["id"])

                # Add to result
                result["employer_positions"] = employer_positions

        return result

    def debug_certifications(self):
        """Debug the certifications data flow through fatten and listify"""

        # Get raw certifications data
        raw_certs = self.get_certifications()

        # Print raw data
        print("\n--- Raw Certifications Data ---")
        for cert in raw_certs:
            print(cert)

        # Check the attrs calculated by listify
        from ..utilities.commands import unique
        attrs = unique([sub["attr"] for sub in raw_certs])
        print(f"\n--- Unique Attributes: {attrs} ---")

        # Check the attrs_per_id calculation
        for cert_id in unique([sub["id"] for sub in raw_certs]):
            attrs_per_id = len(unique([sub["attr"] if sub["id"] == cert_id else "" for sub in raw_certs]))
            print(f"ID {cert_id}: {attrs_per_id} attributes per ID")

        # Return the raw data for further processing
        return raw_certs

    def get_certifications(self) -> list[dict[str, str | int | bool]]:
        """
        Return certification list from database.
        :return list[dict[str, str | int | bool]]: Properly formatted certification data
        """

        # Clear cache if needed
        if len(self.result_certifications) == 0:
            result = self.query(
                """
                SELECT `id`, name, `year`, `state`
                FROM `certification`
                ORDER BY `id`
                """)

            # Create a list to hold the transformed data
            certifications = []

            # Process each row into the format expected by fatten() function
            for certification_id, certification, year, state in result:
                # Create one entry for certification
                certifications.append({
                    "id": certification_id,
                    "attr": "certification",
                    "value": certification,
                    "state": bool(state)
                })

                # Create another entry for year
                certifications.append({
                    "id": certification_id,
                    "attr": "year",
                    "value": year,
                    "state": bool(state)
                })

            # Store the result
            self.result_certifications = certifications

        return self.result_certifications

    # In your Query class, replace the current get_education method with this:
    def get_education(self) -> list[dict[str, str | int | bool]]:
        """
        Return education NESTED list objects from database by school.
        :return list[dict[str, str | int | bool]]: Raw return grouped by 'id/attr/value/state.'
        """
        print("\n--- DEBUG: Fetching education data ---")

        if len(self.result_education) == 0:
            # Clear the result array just to be sure
            self.result_education = []

            # Execute the query and fetch all results - modified to ensure schools with no focus are correctly handled
            result = self.query(
                """
                SELECT f.id,
                       f.name,
                       f.startdate,
                       f.enddate,
                       f.state,
                       s.id,
                       s.name,
                       s.location,
                       s.state
                FROM `school` AS s
                         LEFT JOIN `focus` AS f on s.id = f.school
                ORDER BY f.startdate DESC
                """)

            # Store all rows in a list since we can't seek in SQLite cursor
            rows = list(result)

            # Debug: print raw query results
            print("\n--- DEBUG: Raw education query results ---")
            for row in rows:
                print(row)

            # Track schools that actually have focuses
            schools_with_focuses = set()

            # Create raw NESTED list based on 'origin_ + id/attr/value/state.'
            for (focusid, focusname, startdate, enddate, focusstate,
                 schoolid, schoolname, location, schoolstate) in rows:
                print(f"\n--- Processing school {schoolid}: {schoolname} (state: {schoolstate}) ---")
                print(f"    Focus {focusid}: {focusname} (state: {focusstate})")
                print(f"    Dates: {startdate} - {enddate}")

                # Add school data - always add for processing
                self.result_education.append({
                    "id": "school_" + str(schoolid),
                    "attr": "schoolname",
                    "value": schoolname,
                    "state": schoolstate,
                })
                self.result_education.append({
                    "id": "school_" + str(schoolid),
                    "attr": "location",
                    "value": location,
                    "state": schoolstate,
                })

                # Add a has_focus attribute to track whether this school has any focuses
                self.result_education.append({
                    "id": "school_" + str(schoolid),
                    "attr": "has_focus",
                    "value": "false",  # Default to false
                    "state": schoolstate,
                })

                # Add focus data - only if focus is not None
                if focusid is not None:
                    # Track that this school has a focus
                    schools_with_focuses.add(schoolid)

                    self.result_education.append({
                        "id": "focus_" + str(focusid),
                        "attr": "focusname",
                        "value": focusname,
                        "state": focusstate,
                    })
                    self.result_education.append({
                        "id": "focus_" + str(focusid),
                        "attr": "startdate",
                        "value": startdate,
                        "state": focusstate,
                    })
                    self.result_education.append({
                        "id": "focus_" + str(focusid),
                        "attr": "enddate",
                        "value": enddate,
                        "state": focusstate,
                    })
                    # Add the school ID for each focus
                    self.result_education.append({
                        "id": "focus_" + str(focusid),
                        "attr": "school",
                        "value": "school_" + str(schoolid),
                        "state": focusstate,
                    })

            # Update has_focus attribute for schools that actually have focuses
            for i, entry in enumerate(self.result_education):
                if entry["attr"] == "has_focus" and int(entry["id"].split("_")[1]) in schools_with_focuses:
                    self.result_education[i]["value"] = "true"

            # Debug: print processed data
            print("\n--- DEBUG: Processed education data ---")
            print(f"Total entries: {len(self.result_education)}")
            for entry in self.result_education:
                print(entry)

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
                SELECT s.id, s.category, s.subcategory, e.id, e.employer, p.id, p.position, s.shortdesc, s.longdesc, s.state
                FROM `skill` s
                LEFT JOIN `position` p ON s.position = p.id AND s.employer = p.employer
                LEFT JOIN `employer` e ON s.employer = e.id
                WHERE p.id = s.position and e.id = s.employer
                ORDER BY `categoryorder`, `skillorder`;
                """)

            # Create raw list based on 'id/attr/value/state.'
            for skills_id, category, subcategory, employer, employername, position, positionname, shortdesc, longdesc, state in result:
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
                    "attr": "employername",
                    "value": employername,
                    "state": state})
                self.result_skills.append({
                    "id": skills_id,
                    "attr": "position",
                    "value": position,
                    "state": state})
                self.result_skills.append({
                    "id": skills_id,
                    "attr": "positionname",
                    "value": positionname,
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
            # Let's add some logging to see what's coming from the database
            import logging
            logger = logging.getLogger('query')

            result: Cursor = self.query(
                """
                SELECT e.id,
                       e.employer,
                       e.location,
                       e.state,
                       p.id,
                       p.position,
                       p.startdate,
                       p.enddate,
                       p.state,
                       p.selected_position
                FROM `employer` AS e
                         LEFT JOIN `position` AS p on e.id = p.employer
                ORDER BY p.startdate DESC
                """)

            # Track employers with positions
            employers_with_positions = set()

            # Create raw NESTED list based on 'origin_ + id/attr/value/state.'
            for (employer_id, employer, location, employer_state,
                 position_id, positionname, start_date, end_date, position_state, selected_position) in result:

                # Add a flag to track employers with positions
                self.result_positions.append({
                    "id": "employer_" + str(employer_id),
                    "attr": "has_positions",
                    "value": "false" if position_id is None else "true",
                    "state": employer_state})

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

                # Only add position data if it exists
                if position_id is not None:
                    # Track that this employer has positions
                    employers_with_positions.add(employer_id)

                    self.result_positions.append({
                        "id": "position_" + str(position_id),
                        "attr": "positionname",
                        "value": positionname,
                        "state": position_state})
                    self.result_positions.append({
                        "id": "position_" + str(position_id),
                        "attr": "startdate",
                        "value": start_date})
                    self.result_positions.append({
                        "id": "position_" + str(position_id),
                        "attr": "enddate",
                        "value": end_date})
                    self.result_positions.append({
                        "id": "position_" + str(position_id),
                        "attr": "selected_position",
                        "value": selected_position if selected_position else position_id})

            # Update has_positions attribute based on actual positions
            for i, entry in enumerate(self.result_positions):
                if entry["attr"] == "has_positions":
                    emp_id = int(entry["id"].split("_")[1])
                    if emp_id in employers_with_positions:
                        self.result_positions[i]["value"] = "true"

        return self.result_positions

    def get_achievements(self) -> list[dict[str, str | int | bool]]:
        """
        Return achievements NESTED list objects from database by achievement.
        :return list[dict[str, str | int | bool]]: Raw return grouped by 'id/attr/value/state.'
        """

        if len(self.result_achievements) == 0:
            result: Cursor = self.query(
                """
                SELECT e.id     as employer_id,
                       e.employer,
                       e.state  as employer_state,
                       p.id     as position_id,
                       p.position,
                       p.state  as position_state,
                       a.id     as achievement_id,
                       a.shortdesc,
                       a.longdesc,
                       a.state  as achievement_state,
                       a.school as school_id,
                       s.name   as school_name,
                       s.state  as school_state
                FROM `achievement` a
                         LEFT JOIN `position` p ON a.position = p.id
                         LEFT JOIN `employer` e ON a.employer = e.id
                         LEFT JOIN `school` s ON a.school = s.id;
                """)

            # Create raw NESTED list based on 'id/attr/value/state.'
            for (employer_id, employername, employer_state,
                 position_id, positionname, position_state,
                 achievement_id, shortdesc, longdesc, achievement_state,
                 school_id, school_name, school_state) in result:
                self.result_achievements.append({
                    "id": str(achievement_id),
                    "attr": "employer",
                    "value": str(employer_id) if employer_id is not None else "",
                    "state": employer_state if employer_state is not None else 0,
                })
                self.result_achievements.append({
                    "id": str(achievement_id),
                    "attr": "employername",
                    "value": employername if employername is not None else "",
                    "state": employer_state if employer_state is not None else 0,
                })
                self.result_achievements.append({
                    "id": str(achievement_id),
                    "attr": "position",
                    "value": str(position_id) if position_id is not None else "",
                    "state": position_state if position_state is not None else 0,
                })
                self.result_achievements.append({
                    "id": str(achievement_id),
                    "attr": "positionname",
                    "value": positionname if positionname is not None else "",
                    "state": position_state if position_state is not None else 0,
                })
                # Add school information
                self.result_achievements.append({
                    "id": str(achievement_id),
                    "attr": "school",
                    "value": str(school_id) if school_id is not None else "",
                    "state": school_state if school_state is not None else 0,
                })
                self.result_achievements.append({
                    "id": str(achievement_id),
                    "attr": "schoolname",
                    "value": school_name if school_name is not None else "",
                    "state": school_state if school_state is not None else 0,
                })
                self.result_achievements.append({
                    "id": str(achievement_id),
                    "attr": "achievement",
                    "value": str(achievement_id),
                    "state": achievement_state,
                })
                self.result_achievements.append({
                    "id": str(achievement_id),
                    "attr": "shortdesc",
                    "value": shortdesc,
                    "state": achievement_state,
                })
                self.result_achievements.append({
                    "id": str(achievement_id),
                    "attr": "longdesc",
                    "value": longdesc,
                    "state": achievement_state,
                })
                self.result_achievements.append({
                    "id": str(achievement_id),
                    "attr": "employerstate",
                    "value": employer_state if employer_state is not None else 0,
                    "state": employer_state if employer_state is not None else 0,
                })
                self.result_achievements.append({
                    "id": str(achievement_id),
                    "attr": "positionstate",
                    "value": position_state if position_state is not None else 0,
                    "state": position_state if position_state is not None else 0,
                })
                self.result_achievements.append({
                    "id": str(achievement_id),
                    "attr": "schoolstate",
                    "value": school_state if school_state is not None else 0,
                    "state": school_state if school_state is not None else 0,
                })
                self.result_achievements.append({
                    "id": str(achievement_id),
                    "attr": "achievementstate",
                    "value": achievement_state,
                    "state": achievement_state,
                })

        return self.result_achievements