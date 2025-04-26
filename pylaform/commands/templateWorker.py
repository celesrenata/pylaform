from sqlite3 import Cursor, Connection
from tenacity import retry, stop_after_delay
from werkzeug.datastructures.structures import ImmutableMultiDict

from .db import connect
from .db.query import Queries
from .db.update import Updates
from .db.insert import Inserts
from .db.delete import Deletes
from ..utilities.commands import date_adapter, transform_get_id, unique


class Worker:
    """
    Collection of queries to run against the local database.
    Actions: INSERT INTO, DELETE FROM, UPDATE
    :return None: None
    """

    @retry(stop=(stop_after_delay(10)))
    def __init__(self) -> None:
        self.conn: Connection = connect.db()
        self.cursor: Cursor = self.conn.cursor()
        self.query = Queries()
        self.insert = Inserts()
        self.update = Updates()
        self.delete = Deletes()

    def dropdowns(self, template: str) -> list[dict[str, int]]:
        """
        Takes list of column names and returns a list of dictionaries with column values.
        :param str template: Target template.
        :return list[str]: list of dictionaries with column values.
        """

        match template:
            case "education":
                return self.query.get_options(["school", "focus"], ["name", "name"])
            case "employment":
                return self.query.get_options(["employer", "position"], ["employer", "position"])
            case "achievements":
                return self.query.get_options(["employer", "position"], ["employer", "position"])
            case "skills":
                return self.query.get_options(["skills", "skills", "employer", "position"],
                                              ["category", "subcategory", "employer", "position"])

    def identification(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the identification table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return: None
        """

        # Transform from template.
        form_data: list[dict[str, str | bool]] = transform_get_id(form_data)
        for item in form_data:
            self.update.inverted_single_item("identification", item)

        return

    def certifications(self, transform_form_data: ImmutableMultiDict) -> None:
        """
        Updates the certification table.
        :param ImmutableMultiDict transform_form_data: Form data from template.
        :return: list
        """

        # Transform from template.
        certification_keys = ["id", "name", "year", "state"]
        transform_form_data: list[dict[str, str | bool]] = transform_get_id(transform_form_data)
        counter: str = ""
        result: dict[str, str | int] = {}
        for item in transform_form_data:
            if counter != str(item["id"]):
                counter = str(item["id"])

            # Delete certifications.
            if "delete" in item["attr"]:
                self.delete.delete_target(item["id"], "certification")
                continue

            # Create result based on current attribute value.
            match item["attr"]:
                case "certification":
                    result.update({"id": item["id"], "name": item["value"], "state": int(item["state"])})
                case "year":
                    result.update({"year": item["value"]})

            # Detect last iteration.
            if all(key in result for key in certification_keys):
                # Create certifications.
                if "new" in str(result["id"]):
                    # For new records, we don't need the ID in the insert
                    insert_data = {k: v for k, v in result.items() if k != "id" or not str(v).startswith("new")}
                    self.insert.multi_column("certification", **insert_data)
                # Update certifications.
                else:
                    # For updates, convert the ID to int
                    update_data = dict(result)
                    update_data["id"] = int(update_data["id"])
                    self.update.multi_column("certification", **update_data)

        return

    def update_positions(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the employer and position tables.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """
        import logging
        import sys
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('positions_debug.log', mode='w')
            ]
        )
        logger = logging.getLogger('update_positions')

        logger.debug("Start update_positions - Form data received: %s", dict(form_data))

        # Direct DB updates based on form data structure
        regular_employer_ids = set()
        regular_position_ids = set()
        new_entries = set()

        # Process field names to identify regular and new entries
        for key in form_data.keys():
            parts = key.split('_')
            if len(parts) >= 2:
                id_val = parts[0]
                if id_val == 'new':
                    new_entries.add('new')
                elif id_val.isdigit():  # Regular ID
                    if 'employer' in key or 'location' in key:
                        regular_employer_ids.add(id_val)
                    if 'position' in key or 'startdate' in key or 'enddate' in key:
                        regular_position_ids.add(id_val)

        logger.debug(f"Found regular employer IDs: {regular_employer_ids}")
        logger.debug(f"Found regular position IDs: {regular_position_ids}")
        logger.debug(f"Found new entries: {new_entries}")

        # Process existing record updates first
        for employer_id in regular_employer_ids:
            # Update existing employer
            employer_name = form_data.get(f"{employer_id}_employer", "")
            employer_location = form_data.get(f"{employer_id}_location", "")
            employer_state = 1 if form_data.get(f"{employer_id}_employer_enabled") else 0

            logger.debug(f"Updating employer ID {employer_id}: {employer_name}, {employer_location}, {employer_state}")

            if employer_name:  # Only update if name is not empty
                self.cursor.execute(
                    "UPDATE employer SET employer = ?, location = ?, state = ? WHERE id = ?",
                    (employer_name, employer_location, employer_state, employer_id)
                )

        for position_id in regular_position_ids:
            # Update existing position
            position_name = form_data.get(f"{position_id}_position", "")
            position_state = 1 if form_data.get(f"{position_id}_position_enabled") else 0
            start_date = form_data.get(f"{position_id}_startdate", "")
            end_date = form_data.get(f"{position_id}_enddate", "")

            if start_date:
                start_date = date_adapter(start_date)
            if end_date:
                end_date = date_adapter(end_date)

            # Use employer_dropdown if provided, otherwise keep existing relationship
            employer_dropdown = form_data.get(f"{position_id}_employer_dropdown")

            if employer_dropdown and employer_dropdown not in ["EDIT", "ADD"] and employer_dropdown.isdigit():
                employer_id = employer_dropdown
                logger.debug(f"Using employer ID from dropdown: {employer_id}")
            else:
                # Get current employer from DB
                self.cursor.execute("SELECT employer FROM position WHERE id = ?", (position_id,))
                result = self.cursor.fetchone()
                employer_id = result[0] if result else None
                logger.debug(f"Using existing employer ID: {employer_id}")

            logger.debug(
                f"Updating position ID {position_id}: {position_name}, {start_date}, {end_date}, state={position_state}, employer={employer_id}")

            if position_name and employer_id:  # Only update if name and employer are not empty
                self.cursor.execute(
                    "UPDATE position SET position = ?, startdate = ?, enddate = ?, state = ?, employer = ? WHERE id = ?",
                    (position_name, start_date, end_date, position_state, employer_id, position_id)
                )

        # Process new entries
        if 'new' in new_entries:
            # Handle new employer
            new_employer_name = form_data.get("new_employer", "")
            new_employer_location = form_data.get("new_location", "")
            new_employer_state = 1 if form_data.get("new_employer_enabled") else 0

            # Handle employer dropdown for new positions
            new_employer_dropdown = form_data.get("new_employer_dropdown")
            logger.debug(f"New entry employer dropdown: {new_employer_dropdown}")

            employer_id = None

            # Check if we need to create a new employer or use an existing one from dropdown
            if new_employer_dropdown and new_employer_dropdown not in ["EDIT",
                                                                       "ADD"] and new_employer_dropdown.isdigit():
                # Use existing employer from dropdown
                employer_id = int(new_employer_dropdown)
                logger.debug(f"Using existing employer ID from dropdown for new position: {employer_id}")
            elif new_employer_name:
                # Create new employer
                logger.debug(
                    f"Inserting new employer: {new_employer_name}, {new_employer_location}, {new_employer_state}")
                self.cursor.execute(
                    "INSERT INTO employer (employer, location, state) VALUES (?, ?, ?)",
                    (new_employer_name, new_employer_location, new_employer_state)
                )
                # Get the newly inserted ID
                self.cursor.execute("SELECT last_insert_rowid()")
                employer_id = self.cursor.fetchone()[0]
                logger.debug(f"Inserted new employer with ID: {employer_id}")

            # Handle new position if employer was created or selected
            if employer_id:
                new_position_name = form_data.get("new_position", "")
                new_position_state = 1 if form_data.get("new_position_enabled") else 0
                new_start_date = form_data.get("new_startdate", "")
                new_end_date = form_data.get("new_enddate", "")

                if new_start_date:
                    new_start_date = date_adapter(new_start_date)
                if new_end_date:
                    new_end_date = date_adapter(new_end_date)

                if new_position_name:  # Only insert if there's a position name
                    logger.debug(
                        f"Inserting new position: {new_position_name}, {new_start_date}, {new_end_date}, state={new_position_state}, employer={employer_id}")
                    self.cursor.execute(
                        "INSERT INTO position (position, startdate, enddate, state, employer) VALUES (?, ?, ?, ?, ?)",
                        (new_position_name, new_start_date, new_end_date, new_position_state, employer_id)
                    )
                    logger.debug("Inserted new position")

        # Handle deletions - look for _delete in form keys
        for key in form_data.keys():
            if "_delete" in key:
                id_to_delete = key.split("_")[0]
                if id_to_delete.isdigit():
                    logger.debug(f"Deleting position ID {id_to_delete}")
                    self.cursor.execute("DELETE FROM position WHERE id = ?", (id_to_delete,))
                    # Also check if this employer is used by other positions before deleting
                    self.cursor.execute("SELECT employer FROM position WHERE id = ?", (id_to_delete,))
                    employer_id = self.cursor.fetchone()
                    if employer_id:
                        self.cursor.execute("SELECT COUNT(*) FROM position WHERE employer = ?", (employer_id[0],))
                        position_count = self.cursor.fetchone()[0]
                        if position_count == 0:
                            logger.debug(f"Deleting unused employer ID {employer_id[0]}")
                            self.cursor.execute("DELETE FROM employer WHERE id = ?", (employer_id[0],))

        self.conn.commit()
        logger.debug("Finished update_positions - committed all changes")
        return

    def update_skills(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the skills table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """
        # Get item count.
        attrs: list[str] = list(form_data.keys())

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
                continue

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
                case "categoryorder":
                    result.update({"categoryorder": item["value"]})
                case "skillorder":
                    result.update({"skillorder": item["value"]})

            # Create skill.
            if "new" in item["id"]:
                # Detect last iteration.
                if all(key in result for key in
                       ["employer", "position", "shortdesc", "longdesc", "category", "subcategory", "state"]):
                    # TODO: Implement ordering support.
                    self.insert.multi_column("skill", **result)

            # Update skill.
            else:
                if "dropdown" not in item["attr"]:
                    self.update.single_item("skill", item)

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
            # Get ID from name.
            if item["attr"] == "school":
                item["value"] = str(self.query.query_id(item["value"], "school"))
            if item["attr"] == "focus":
                item["value"] = str(self.query.query_id(item["value"], "focus"))
            if counter != str(item["id"]):
                counter = str(item["id"])
                result = {}

            # Build attrs to expect per ID.
            attrs_per_id = len(unique(transform_form_data))

            # Delete summary.
            if "delete" in item["attr"]:
                self.delete.delete_target(item["id"], "summary")
                continue

            # Create summary.
            if "new" in item["id"]:
                # Create result based on current attribute value.
                match item["attr"]:
                    case "shortdesc":
                        result.update({"shortdesc": item["value"]})
                    case "longdesc":
                        result.update({"longdesc": item["value"]})
                    case "summaryorder":
                        result.update({"summaryorder": item["value"], "state": int(item["state"])})
                # Detect last iteration.
                if all(key in result for key in ["shortdesc", "longdesc", "summaryorder", "state"]):
                    self.insert.multi_column("summary", **result)

            # Update summary.
            else:
                self.update.single_item("summary", item)

        return

    def update_education(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the education and focus tables.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """

        attrs: list[str] = list(form_data.keys())

        transform_form_data: list[dict[str, str | bool]] = transform_get_id(form_data)
        counter: str = ""
        school_query_builder: dict[str, str | int] = {}
        school_queries: list[dict[str, str | int]] = []
        focus_query_builder: dict[str, str | int] = {}
        focus_queries: list[dict[str, str]] = []
        school_keys = ["school_location", "school_name", "school_state"]
        focus_keys = ["focus_name", "focus_state", "focus_startdate", "focus_enddate", "focus_school"]

        attrs_per_id = len(unique(transform_form_data))
        school_dropdown_id = None  # Changed to None for clarity
        focus_dropdown_id = None
        school_name = ""

        # First pass - collect row_ids to ensure we maintain them for updates
        row_ids = {}
        for item in transform_form_data:
            if item["attr"] == "rowid":
                row_ids[item["id"]] = item["value"]

        for i, item in enumerate(transform_form_data):
            focus_school_value = None

            if counter != str(item["id"]):
                counter = str(item["id"])

            if "delete" in item["attr"]:
                self.delete.single_association(item["id"], "school", "focus")
                continue

            if "date" in item["attr"]:
                item["value"] = date_adapter(item["value"])

            match item["attr"]:
                case "school_dropdown":
                    school_dropdown_id = {"id": item["id"], "value": item["value"]}
                    # If the row_id exists, keep the original school ID for updating
                    if item["id"] in row_ids:
                        original_school_id = row_ids[item["id"]]
                        if original_school_id and original_school_id.isdigit():
                            school_query_builder["id"] = int(original_school_id)
                case "school_location":
                    school_query_builder.update({"school_location": item["value"]})
                case "school_name":
                    # Get the original ID from the row_id field, not the dropdown value
                    is_new = False
                    if item["id"] in row_ids:
                        original_id = row_ids[item["id"]]
                        is_new = original_id == "new"

                    if is_new:
                        school_query_builder.update({"school_name": item["value"], "school_state": int(item["state"])})
                    else:
                        try:
                            # If we already have an ID in the builder (from rowid), use that
                            if "id" not in school_query_builder and item["id"] in row_ids:
                                original_id = row_ids[item["id"]]
                                if original_id and original_id.isdigit():
                                    school_query_builder["id"] = int(original_id)

                            # Now update the name and state
                            school_query_builder.update({
                                "school_name": item["value"],
                                "school_state": int(item["state"])
                            })
                        except ValueError:
                            pass
                case "focus_dropdown":
                    focus_dropdown_id = {"id": item["id"], "value": item["value"]}
                    # If the row_id exists and it's not new, set the focus ID directly
                    if item["id"] in row_ids:
                        focus_id = item["id"]  # This is the focus ID, not the school ID
                        if focus_id and focus_id.isdigit():
                            focus_query_builder["id"] = int(focus_id)
                case "focus_name":
                    # Use the actual focus_id as the ID for updates
                    if item["id"] not in row_ids or row_ids[item["id"]] == "new":
                        focus_query_builder.update({"focus_name": item["value"], "focus_state": int(item["state"])})
                    else:
                        try:
                            if "id" not in focus_query_builder:
                                focus_query_builder["id"] = int(item["id"])
                            focus_query_builder.update({
                                "focus_name": item["value"],
                                "focus_state": int(item["state"])
                            })
                        except ValueError:
                            pass
                case "focus_startdate":
                    focus_query_builder.update({"focus_startdate": item["value"]})
                case "focus_enddate":
                    focus_query_builder.update({"focus_enddate": item["value"]})

            if all(key in school_query_builder for key in school_keys):
                # Key fix: Maintain the existing school ID from rowid if it's not new
                if "id" not in school_query_builder and item["id"] in row_ids:
                    original_id = row_ids[item["id"]]
                    if original_id != "new" and original_id.isdigit():
                        school_query_builder["id"] = int(original_id)

                # But allow the school to be changed if a different one is selected
                if isinstance(school_dropdown_id, dict) and "value" in school_dropdown_id:
                    if school_dropdown_id["value"] not in ["EDIT", "ADD"]:
                        # Use the selected school ID from the dropdown instead
                        selected_school_id = int(school_dropdown_id["value"])
                        # Don't update the ID, just query for name to use in focus relationship
                        school_name = self.query.query_name(selected_school_id, "school")
                        focus_query_builder.update({"focus_school": selected_school_id})

                        # We'll still update the existing school record, but we'll link the focus to a different school
                        if "id" in school_query_builder:
                            school_queries.append(school_query_builder)
                        school_query_builder = {}
                        continue

                # Regular processing when not changing schools
                if "id" not in school_query_builder:
                    school_query_builder.update(
                        {"id": self.query.query_id(school_query_builder["school_name"], "school")})
                if school_query_builder["id"] == 0:
                    school_query_builder.pop("id")
                school_queries.append(school_query_builder)
                if "school_name" in school_query_builder and "id" in school_query_builder:
                    if school_query_builder["school_name"] == "":
                        school_query_builder["school_name"] = self.query.query_name(school_query_builder["id"],
                                                                                    "school")
                focus_query_builder.update(
                    {"focus_school": self.query.query_id(school_query_builder["school_name"], "school")})
                school_name = school_query_builder["school_name"]
                school_query_builder = {}

            if len(school_queries) > 0:
                for school_i, query in enumerate(school_queries):
                    if "id" not in query:
                        self.insert.multi_column("school", **query)
                    else:
                        self.update.multi_column("school", **query)
                    school_queries.pop(school_i)

            if all(key in focus_query_builder for key in focus_keys):
                # Use the existing focus ID from the actual item ID
                if "id" not in focus_query_builder and item["id"] != "new" and item["id"].isdigit():
                    focus_query_builder.update({"id": int(item["id"])})

                focus_school_value = focus_query_builder.get("focus_school")

                # If user selected a different school in the dropdown, use that
                if isinstance(school_dropdown_id, dict) and "value" in school_dropdown_id and \
                        school_dropdown_id["value"] not in ["EDIT", "ADD"]:
                    try:
                        focus_query_builder.update({"focus_school": int(school_dropdown_id["value"])})
                    except ValueError:
                        pass

                if "focus_name" in focus_query_builder and "id" in focus_query_builder:
                    if focus_query_builder["focus_name"] == "":
                        focus_query_builder["focus_name"] = self.query.query_name(focus_query_builder["id"], "focus")
                if focus_query_builder.get("focus_school", 0) == 0:
                    focus_query_builder.update(
                        {"focus_school": self.query.query_id(school_name, "school")})
                if focus_query_builder.get("id", 0) == 0:
                    focus_query_builder.pop("id", None)
                focus_queries.append(focus_query_builder)
                focus_query_builder = {}

        for query in focus_queries:
            if "id" not in query:
                self.insert.multi_column("focus", **query)
            else:
                self.update.multi_column("focus", **query)

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
                continue

            # Create achievement.
            if "new" in item["id"]:
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
                if all(key in result for key in ["employer", "position", "shortdesc", "longdesc", "state"]):
                    self.insert.multi_column("achievement", **result)

            # Update achievement.
            else:
                # Get ID from name.
                match item["attr"]:
                    case "position":
                        item["value"] = str(self.query.query_id(item["value"], "position"))
                    case "employer":
                        item["value"] = str(self.query.query_id(item["value"], "employer"))
                self.update.single_item("achievement", item)

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
                if all(key in result for key in ["term", "url", "description", "state"]):
                    self.insert.multi_column("glossary", **result)


            # Update term.
            else:
                self.update.single_item("glossary", item)

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
            if item["value"] is None:
                self.cursor.execute(
                    f"""
                    DELETE FROM `{table}`
                    WHERE `id` = {int(item["id"])}"""
                )
            else:
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
