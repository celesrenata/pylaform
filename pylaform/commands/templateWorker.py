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

    def dropdowns(self, template: str) -> dict:
        """
        Returns dropdowns for templates.
        :param template: The template to get dropdowns for.
        :return: A dictionary of dropdown options.
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Getting dropdowns for template: {template}")

        # Ensure cursor is initialized
        if not hasattr(self, 'cursor') or self.cursor is None:
            from . import connect
            self.conn = connect.db()
            self.cursor = self.conn.cursor()
            logger.info("Initialized cursor connection")

        try:
            match template:
                case "education":
                    logger.info("Handling education template")
                    result = self.query.get_options(["school", "focus"], ["name", "name"])
                case "employment":
                    logger.info("Handling employment template")
                    result = self.query.get_options(["employer", "position"], ["employer", "position"])
                case "achievements":
                    logger.info("Handling achievements template")
                    # Get employer and school options
                    try:
                        employer_options = self.query.get_options(["employer"], ["employer"])["employer"]
                        logger.info(f"Got {len(employer_options)} employer options")
                    except Exception as e:
                        logger.error(f"Error getting employer options: {e}")
                        employer_options = []

                    try:
                        school_options = self.query.get_options(["school"], ["name"])["school"]
                        logger.info(f"Got {len(school_options)} school options")
                    except Exception as e:
                        logger.error(f"Error getting school options: {e}")
                        school_options = []

                    # Get position options with employer ID
                    try:
                        self.cursor.execute("""
                                            SELECT p.id, p.position, p.employer
                                            FROM position p
                                            ORDER BY p.position
                                            """)
                        position_options = [
                            {"id": int(item[0]), "name": item[1], "employer": item[2], "type": "position"}
                            for item in self.cursor.fetchall()
                        ]
                        logger.info(f"Got {len(position_options)} position options")
                    except Exception as e:
                        logger.error(f"Error getting position options: {e}")
                        position_options = []

                    # Get focus options with school ID
                    try:
                        self.cursor.execute("""
                                            SELECT f.id, f.name, f.school
                                            FROM focus f
                                            ORDER BY f.name
                                            """)
                        focus_options = [
                            {"id": int(item[0]), "name": item[1], "employer": item[2], "type": "focus"}
                            for item in self.cursor.fetchall()
                        ]
                        logger.info(f"Got {len(focus_options)} focus options")
                    except Exception as e:
                        logger.error(f"Error getting focus options: {e}")
                        focus_options = []

                    # Combine employers and schools into one list
                    combined_orgs = []
                    for employer in employer_options:
                        employer["type"] = "employer"
                        combined_orgs.append(employer)

                    for school in school_options:
                        school["type"] = "school"
                        combined_orgs.append(school)

                    # Combine positions and focuses
                    combined_roles = position_options + focus_options

                    # Create mappings between organizations and roles
                    org_roles_map = {}

                    # Map employers to positions
                    for position in position_options:
                        employer_id = str(position["employer"])
                        if employer_id not in org_roles_map:
                            org_roles_map[employer_id] = []
                        org_roles_map[employer_id].append(position["id"])

                    # Map schools to focuses
                    for focus in focus_options:
                        school_id = str(focus["employer"])
                        if school_id not in org_roles_map:
                            org_roles_map[school_id] = []
                        org_roles_map[school_id].append(focus["id"])

                    # Build the result
                    result = {
                        "employer": combined_orgs,  # Will contain both employers and schools
                        "position": combined_roles,  # Will contain both positions and focuses
                        "employer_positions": org_roles_map  # Maps org IDs to role IDs
                    }
                    logger.info(f"Built result with {len(combined_orgs)} orgs, {len(combined_roles)} roles")
                case "skills":
                    logger.info("Handling skills template")
                    # Get options with employer-position mapping
                    options = self.query.get_options(["skill", "skill", "employer", "position"],
                                                     ["category", "subcategory", "employer", "position"])

                    # Add employer-position map for client-side filtering
                    employer_positions = {}
                    self.cursor.execute("SELECT id, employer FROM position")
                    for position_id, employer_id in self.cursor.fetchall():
                        if str(employer_id) not in employer_positions:
                            employer_positions[str(employer_id)] = []
                        employer_positions[str(employer_id)].append(position_id)

                    options["employer_positions"] = employer_positions
                    result = options
                case _:
                    # Default case for unhandled templates
                    logger.warning(f"Unhandled template type: {template}")
                    result = {}

            logger.info(f"Returning result of type {type(result)}")
            return result
        except Exception as e:
            logger.error(f"Error in dropdowns method: {e}")
            # Return a minimal valid result to avoid template errors
            return {"employer": [], "position": [], "employer_positions": {}}

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

    def certifications(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the certification table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return: None
        """
        # Get raw form data as dictionary with arrays
        raw_form_dict = form_data.to_dict(flat=False)

        # Process existing certifications
        existing_certs = {}
        for key, value in raw_form_dict.items():
            # Skip new entries
            if key.startswith('new'):
                continue

            # Process delete entries
            if '_delete' in key:
                cert_id = key.split('_')[0]
                self.delete.delete_target(cert_id, 'certification')
                continue

            # Process existing certification fields
            parts = key.split('_')
            if len(parts) >= 2:
                cert_id = parts[0]

                # Initialize record if it doesn't exist
                if cert_id not in existing_certs:
                    existing_certs[cert_id] = {}

                # Store the field value
                field_name = '_'.join(parts[1:])
                existing_certs[cert_id][field_name] = value[0]

        # Update existing certifications
        for cert_id, data in existing_certs.items():
            if cert_id.isdigit() and 'certification' in data:
                update_data = {
                    'id': int(cert_id),
                    'name': data.get('certification', ''),
                    'year': data.get('year', ''),
                    'state': 1 if 'year_enabled' in data else 0
                }

                self.update.multi_column('certification', **update_data)

        # Get all new certification entries
        new_cert_fields = {}
        for key in raw_form_dict:
            if key.startswith('new') and '_certification' in key:
                entry_id = key.split('_')[0]  # Get 'new1', 'new2', etc.

                if entry_id not in new_cert_fields:
                    new_cert_fields[entry_id] = {}

                new_cert_fields[entry_id]['name'] = raw_form_dict[key][0]

                # Try to get corresponding year field
                year_key = f"{entry_id}_year"
                if year_key in raw_form_dict:
                    new_cert_fields[entry_id]['year'] = raw_form_dict[year_key][0]
                else:
                    new_cert_fields[entry_id]['year'] = ''

                # Check if enabled
                enabled_key = f"{entry_id}_year_enabled"
                new_cert_fields[entry_id]['state'] = 1 if enabled_key in raw_form_dict else 0

        # Insert all new certifications
        for entry_id, data in new_cert_fields.items():
            if 'name' in data and data['name']:  # Only insert if we have a name
                insert_data = {
                    'name': data['name'],
                    'year': data.get('year', ''),
                    'state': data.get('state', 1)
                }

                self.insert.multi_column('certification', **insert_data)

        return

    def update_positions(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the employer and position tables.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """
        import logging
        import sys
        from werkzeug.datastructures import MultiDict
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

        # Convert ImmutableMultiDict to a manageable structure that handles multiple entries
        # MultiDict.to_dict(flat=False) returns lists for multiple values with the same key
        raw_form_dict = form_data.to_dict(flat=False)
        logger.debug(f"Raw form data dictionary: {raw_form_dict}")

        # Process existing entries (not "new")
        existing_entries = {}
        for key, values in raw_form_dict.items():
            position_id = key.split('_')[0]
            if position_id != 'new' and not key.endswith('_delete'):
                if position_id not in existing_entries:
                    existing_entries[position_id] = {}
                field_name = '_'.join(key.split('_')[1:])
                existing_entries[position_id][field_name] = values[0]  # Take first value

        # Process deletes
        for key in raw_form_dict:
            if key.endswith('_delete'):
                position_id = key.split('_')[0]
                if position_id.isdigit():
                    # Get employer ID to delete associated entries
                    self.cursor.execute("SELECT employer FROM position WHERE id = ?", (position_id,))
                    result = self.cursor.fetchone()
                    if result:
                        employer_id = result[0]
                        # Delete the position
                        self.cursor.execute("DELETE FROM position WHERE id = ?", (position_id,))
                        # Check if this was the last position for this employer
                        self.cursor.execute("SELECT COUNT(*) FROM position WHERE employer = ?", (employer_id,))
                        count = self.cursor.fetchone()[0]
                        if count == 0:
                            # No positions left, delete the employer too
                            self.cursor.execute("DELETE FROM employer WHERE id = ?", (employer_id,))

        # Create a mapping for existing positions
        id_mapping = {}  # Maps position_id -> actual DB position id
        for position_id, data in existing_entries.items():
            if 'rowid' in data:
                id_mapping[position_id] = data['rowid']

        logger.debug(f"ID mapping: {id_mapping}")

        # 1. Handle employer updates for existing entries
        for position_id, data in existing_entries.items():
            employer_id = data.get('rowid')
            if employer_id and employer_id != 'new' and employer_id.isdigit():
                # Update existing employer
                employer_name = data.get('employer', '')
                employer_location = data.get('location', '')
                employer_state = 1 if data.get('employer_enabled') == 'on' else 0

                if employer_name:
                    logger.debug(
                        f"Updating employer ID {employer_id}: {employer_name}, {employer_location}, state={employer_state}")
                    self.cursor.execute(
                        "UPDATE employer SET employer = ?, location = ?, state = ? WHERE id = ?",
                        (employer_name, employer_location, employer_state, employer_id)
                    )

        # 2. Process new entries
        # Group new entries by their index
        new_entries = {}

        # Collect all 'new' keys and determine how many new entries we have
        new_keys = [k for k in raw_form_dict.keys() if k.startswith('new_')]

        # For each new entry field, process all values
        for key in new_keys:
            field_name = '_'.join(key.split('_')[1:])
            values = raw_form_dict[key]

            # Process each value as a separate new entry
            for index, value in enumerate(values):
                entry_id = f"new_{index}"
                if entry_id not in new_entries:
                    new_entries[entry_id] = {}
                new_entries[entry_id][field_name] = value

        logger.debug(f"Processed new entries: {new_entries}")

        # Create new employers and positions
        for entry_id, data in new_entries.items():
            # 2a. Create new employer if needed
            employer_dropdown = data.get('employer_dropdown')
            new_employer_id = None

            if employer_dropdown == 'EDIT':
                # Create a new employer
                employer_name = data.get('employer', '')
                employer_location = data.get('location', '')
                employer_state = 1 if data.get('employer_enabled') == 'on' else 0

                if employer_name:
                    logger.debug(f"Creating new employer: {employer_name}, {employer_location}, state={employer_state}")
                    self.cursor.execute(
                        "INSERT INTO employer (employer, location, state) VALUES (?, ?, ?)",
                        (employer_name, employer_location, employer_state)
                    )
                    # Get the new employer ID
                    self.cursor.execute("SELECT last_insert_rowid()")
                    new_employer_id = self.cursor.fetchone()[0]
                    logger.debug(f"Created new employer with ID {new_employer_id}")
            elif employer_dropdown and employer_dropdown != 'ADD' and employer_dropdown.isdigit():
                # Use existing employer from dropdown
                new_employer_id = employer_dropdown
                logger.debug(f"Using existing employer ID {new_employer_id} from dropdown")

            # 2b. Create new position if needed
            position_dropdown = data.get('position_dropdown')

            if position_dropdown == 'EDIT' and new_employer_id:
                # Create a new position
                position_name = data.get('position', '')
                start_date = data.get('startdate', '')
                end_date = data.get('enddate', '')
                position_state = 1 if data.get('position_enabled') == 'on' else 0

                if position_name and start_date:
                    if start_date:
                        start_date = date_adapter(start_date)
                    if end_date:
                        end_date = date_adapter(end_date)

                    logger.debug(
                        f"Creating new position: {position_name}, dates: {start_date}-{end_date}, state={position_state}, employer={new_employer_id}")
                    self.cursor.execute(
                        "INSERT INTO position (position, startdate, enddate, state, employer) VALUES (?, ?, ?, ?, ?)",
                        (position_name, start_date, end_date, position_state, new_employer_id)
                    )

        # 3. Update existing positions
        for position_id, data in existing_entries.items():
            if position_id.isdigit():
                # Get employer for this position
                employer_dropdown = data.get('employer_dropdown')
                employer_id = None

                if employer_dropdown and employer_dropdown != 'EDIT' and employer_dropdown != 'ADD' and employer_dropdown.isdigit():
                    # Use employer from dropdown
                    employer_id = employer_dropdown
                else:
                    # Use the original employer ID
                    employer_id = data.get('rowid')

                # Handle position data
                position_name = data.get('position', '')
                start_date = data.get('startdate', '')
                end_date = data.get('enddate', '')
                position_state = 1 if data.get('position_enabled') == 'on' else 0

                if position_name and start_date and employer_id:
                    if start_date:
                        start_date = date_adapter(start_date)
                    if end_date:
                        end_date = date_adapter(end_date)

                    logger.debug(
                        f"Updating position ID {position_id}: {position_name}, dates: {start_date}-{end_date}, state={position_state}, employer={employer_id}")
                    self.cursor.execute(
                        "UPDATE position SET position = ?, startdate = ?, enddate = ?, state = ?, employer = ? WHERE id = ?",
                        (position_name, start_date, end_date, position_state, employer_id, position_id)
                    )

        # Commit all changes
        self.conn.commit()
        logger.debug("Finished update_positions - committed all changes")
        return

    def update_skills(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the skill table.
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
                logging.FileHandler('skills_debug.log', mode='w')
            ]
        )
        logger = logging.getLogger('update_skills')

        logger.debug("Start update_skills - Form data received: %s", dict(form_data))

        # Get raw form data as dictionary with arrays
        raw_form_dict = form_data.to_dict(flat=False)
        logger.debug(f"Raw form data dictionary: {raw_form_dict}")

        # Process existing skills
        existing_skills = {}
        for key, values in raw_form_dict.items():
            # Skip new entries and delete commands
            if key.startswith('new') or key.endswith('_delete'):
                continue

            # Process existing skills fields
            parts = key.split('_')
            if len(parts) >= 2 and parts[0].isdigit():
                skill_id = parts[0]

                # Initialize record if it doesn't exist
                if skill_id not in existing_skills:
                    existing_skills[skill_id] = {}

                # Store the field value (first value if multiple)
                field_name = '_'.join(parts[1:])
                existing_skills[skill_id][field_name] = values[0]

        # Process deletes
        for key in raw_form_dict:
            if key.endswith('_delete'):
                skill_id = key.split('_')[0]
                if skill_id.isdigit():
                    logger.debug(f"Deleting skill ID {skill_id}")
                    self.delete.delete_target(skill_id, 'skill')
                    self.conn.commit()  # Commit after each delete

        # Update existing skills
        for skill_id, data in existing_skills.items():
            if skill_id.isdigit():
                # Handle category dropdown/input selection
                category_dropdown = data.get('category_dropdown', '')
                category = data.get('category', '')

                # Determine which category to use based on the dropdown selection
                if category_dropdown and category_dropdown not in ['EDIT', 'ADD']:
                    # Use the category from the dropdown
                    category_value = self.query.query_name(int(category_dropdown), 'category')
                else:
                    # Use the manually entered category
                    category_value = category

                # Handle subcategory dropdown/input selection
                subcategory_dropdown = data.get('subcategory_dropdown', '')
                subcategory = data.get('subcategory', '')

                # Determine which subcategory to use based on the dropdown selection
                if subcategory_dropdown and subcategory_dropdown not in ['EDIT', 'ADD']:
                    # Use the subcategory from the dropdown
                    subcategory_value = self.query.query_name(int(subcategory_dropdown), 'subcategory')
                else:
                    # Use the manually entered subcategory
                    subcategory_value = subcategory

                # Handle employer and position dropdowns
                employer_id = data.get('employer_dropdown', '')
                position_id = data.get('position_dropdown', '')

                # Validate that the position belongs to the employer
                if employer_id and position_id and employer_id != 'EDIT' and employer_id != 'ADD' and position_id != 'EDIT' and position_id != 'ADD':
                    # Check if the position belongs to the selected employer
                    self.cursor.execute(
                        "SELECT employer FROM position WHERE id = ?",
                        (position_id,)
                    )
                    result = self.cursor.fetchone()
                    if result and str(result[0]) != str(employer_id):
                        # Position doesn't belong to this employer, don't update
                        logger.debug(
                            f"Position {position_id} doesn't belong to employer {employer_id}, skipping update")
                        continue

                # Determine state from the checkbox
                skill_state = 1 if data.get('longdesc_enabled') == 'on' else 0

                # Prepare skill update data
                update_data = {
                    'id': int(skill_id),
                    'category': category_value,
                    'subcategory': subcategory_value,
                    'employer': employer_id if employer_id and employer_id not in ['EDIT', 'ADD'] else None,
                    'position': position_id if position_id and position_id not in ['EDIT', 'ADD'] else None,
                    'shortdesc': data.get('shortdesc', ''),
                    'longdesc': data.get('longdesc', ''),
                    'state': skill_state
                }

                logger.debug(f"Updating skill ID {skill_id}: {update_data}")

                try:
                    # Direct SQL approach to avoid potential retry issues in multi_column
                    set_parts = []
                    params = []

                    for key, value in update_data.items():
                        if key != 'id':  # Skip the ID field for the SET clause
                            if value is None:
                                set_parts.append(f"`{key}` = NULL")
                            elif isinstance(value, int):
                                set_parts.append(f"`{key}` = ?")
                                params.append(value)
                            elif isinstance(value, str):
                                set_parts.append(f"`{key}` = ?")
                                params.append(value)

                    params.append(update_data['id'])  # Add ID for WHERE clause

                    query = f"""
                    UPDATE `skill`
                    SET {", ".join(set_parts)}
                    WHERE `id` = ?;
                    """

                    logger.debug(f"Executing query: {query} with params: {params}")
                    self.cursor.execute(query, params)
                    self.conn.commit()  # Commit after each update

                except Exception as e:
                    logger.error(f"Error updating skill ID {skill_id}: {e}")
                    # Continue with next skill instead of failing completely

        # Process new entries with 'new1_', 'new2_', etc. prefixes
        new_entries = {}
        new_entry_prefixes = set()

        # Find all prefixes for new entries (like 'new1_', 'new2_')
        for key in raw_form_dict.keys():
            if key.startswith('new') and '_' in key:
                prefix = key.split('_')[0] + '_'  # e.g., 'new1_'
                new_entry_prefixes.add(prefix)

        # Group form fields by their new entry prefix
        for prefix in new_entry_prefixes:
            entry_data = {}
            for key, values in raw_form_dict.items():
                if key.startswith(prefix):
                    field_name = key[len(prefix):]  # Remove the prefix to get the field name
                    entry_data[field_name] = values[0]

            if entry_data:  # Only add if we found data for this prefix
                new_entries[prefix] = entry_data

        logger.debug(f"Processed new entries: {new_entries}")

        # Insert all new skills
        for prefix, data in new_entries.items():
            try:
                # Handle category dropdown/input selection
                category_dropdown = data.get('category_dropdown', '')
                category = data.get('category', '')

                # Determine which category to use based on the dropdown selection
                if category_dropdown and category_dropdown not in ['EDIT', 'ADD']:
                    # Use the category from the dropdown
                    category_value = self.query.query_name(int(category_dropdown), 'category')
                else:
                    # Use the manually entered category
                    category_value = category

                # Handle subcategory dropdown/input selection
                subcategory_dropdown = data.get('subcategory_dropdown', '')
                subcategory = data.get('subcategory', '')

                # Determine which subcategory to use based on the dropdown selection
                if subcategory_dropdown and subcategory_dropdown not in ['EDIT', 'ADD']:
                    # Use the subcategory from the dropdown
                    subcategory_value = self.query.query_name(int(subcategory_dropdown), 'subcategory')
                else:
                    # Use the manually entered subcategory
                    subcategory_value = subcategory

                # Handle employer and position dropdowns
                employer_id = data.get('employer_dropdown', '')
                position_id = data.get('position_dropdown', '')

                # Validate that the position belongs to the employer
                if employer_id and position_id and employer_id != 'EDIT' and employer_id != 'ADD' and position_id != 'EDIT' and position_id != 'ADD':
                    # Check if the position belongs to the selected employer
                    self.cursor.execute(
                        "SELECT employer FROM position WHERE id = ?",
                        (position_id,)
                    )
                    result = self.cursor.fetchone()
                    if result and str(result[0]) != str(employer_id):
                        # Position doesn't belong to this employer, skip this entry
                        logger.debug(
                            f"Position {position_id} doesn't belong to employer {employer_id}, skipping insert")
                        continue

                # Determine state from the checkbox
                skill_state = 1 if data.get('longdesc_enabled') == 'on' else 0

                # Only proceed if we have the required data
                if category_value and 'shortdesc' in data and data['shortdesc']:
                    # First, find out what the max categoryorder and skillorder are
                    self.cursor.execute("SELECT MAX(categoryorder) FROM skill")
                    max_category_order = self.cursor.fetchone()[0] or 0

                    self.cursor.execute("SELECT MAX(skillorder) FROM skill")
                    max_skill_order = self.cursor.fetchone()[0] or 0

                    # Use direct SQL to insert the new skill with order values
                    columns = [
                        'category', 'subcategory', 'employer', 'position',
                        'shortdesc', 'longdesc', 'state',
                        'categoryorder', 'skillorder'  # Add the required order columns
                    ]

                    values = [
                        category_value,
                        subcategory_value,
                        employer_id if employer_id and employer_id not in ['EDIT', 'ADD'] else None,
                        position_id if position_id and position_id not in ['EDIT', 'ADD'] else None,
                        data.get('shortdesc', ''),
                        data.get('longdesc', ''),
                        skill_state,
                        max_category_order + 1,  # Increment categoryorder
                        max_skill_order + 1  # Increment skillorder
                    ]

                    # Filter out None values for SQL (but keep the order columns)
                    valid_columns = []
                    valid_values = []
                    for i, val in enumerate(values):
                        if val is not None or columns[i] in ('categoryorder', 'skillorder'):
                            valid_columns.append(columns[i])
                            valid_values.append(val if val is not None else 0)  # Use 0 as default for NULL values

                    placeholders = ', '.join(['?' for _ in valid_values])

                    query = f"""
                    INSERT INTO `skill` ({', '.join([f'`{col}`' for col in valid_columns])})
                    VALUES ({placeholders});
                    """

                    logger.debug(f"Inserting new skill: {dict(zip(valid_columns, valid_values))}")
                    logger.debug(f"Executing query: {query} with values: {valid_values}")

                    self.cursor.execute(query, valid_values)
                    self.conn.commit()  # Commit after each insert

                    logger.debug(f"Successfully inserted new skill with prefix {prefix}")
            except Exception as e:
                logger.error(f"Error inserting new skill with prefix {prefix}: {e}")
                # Continue with next entry instead of failing completely

        logger.debug("Finished update_skills - committed all changes")
        return

    def update_summary(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the summary table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """
        import re  # Add this import

        # Debug: Print form data
        print("Raw form data:")
        for key, value in form_data.items():
            print(f"  {key}: {value}")

        # Transform from template
        transform_form_data = transform_get_id(form_data)

        # Debug: Print transformed data
        print("Transformed form data:")
        for item in transform_form_data:
            print(f"  {item}")

        # Group data by ID
        items_by_id = {}
        for item in transform_form_data:
            item_id = item["id"]
            if item_id not in items_by_id:
                items_by_id[item_id] = {}

            # Store the attribute and its value
            items_by_id[item_id][item["attr"]] = item["value"]

            # Store the state (enabled status)
            if "state" not in items_by_id[item_id]:
                items_by_id[item_id]["state"] = item["state"]

        # Process each ID group
        for item_id, data in items_by_id.items():
            # Handle deletions
            if any(attr.endswith("delete") for attr in data):
                print(f"Deleting summary item: {item_id}")
                self.delete.delete_target(item_id, "summary")
                continue

            # Handle new items
            if "new" in item_id:
                # Check if we have the required fields
                if "shortdesc" in data and "longdesc" in data:
                    print(f"Creating new summary item with data: {data}")
                    # Create a clean data dictionary for the insert

                    # Check if the form checkbox was checked (enabled state)
                    # The form input name is typically "item_id_longdesc_enabled"
                    checkbox_name = f"{item_id}_longdesc_enabled"
                    is_enabled = checkbox_name in form_data and form_data[checkbox_name] == 'on'

                    insert_data = {
                        "shortdesc": data.get("shortdesc", ""),
                        "longdesc": data.get("longdesc", ""),
                        "summaryorder": data.get("summaryorder", 99),  # Default order
                        "state": 1  # Always set to active (1) for new entries
                    }

                    # Insert the new record
                    try:
                        self.insert.multi_column("summary", **insert_data)
                        print(f"Successfully created new summary item with state=1")
                    except Exception as e:
                        print(f"Error creating summary item: {e}")
                else:
                    print(f"Skipping incomplete new item: {data}")

            # Handle updates to existing items
            else:
                # Update each attribute individually
                try:
                    item_id_int = int(item_id)

                    if "shortdesc" in data:
                        self.update.single_item("summary", {
                            "id": item_id_int,
                            "attr": "shortdesc",
                            "value": data["shortdesc"],
                            "state": data.get("state", False)
                        })

                    if "longdesc" in data:
                        self.update.single_item("summary", {
                            "id": item_id_int,
                            "attr": "longdesc",
                            "value": data["longdesc"],
                            "state": data.get("state", False)
                        })

                    print(f"Updated summary item: {item_id}")
                except Exception as e:
                    print(f"Error updating summary item {item_id}: {e}")

        # Purge the cache after all operations are complete
        self.query.purge_cache("summary")

        return

    def update_education(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the education and focus tables.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """
        # Get raw form data and analyze it
        raw_form_dict = form_data.to_dict(flat=False)

        # Process deletion requests first
        for key, value in raw_form_dict.items():
            if "_delete" in key and value[0] == "True":
                focus_id = key.split("_delete")[0]
                if focus_id.isdigit():
                    # Delete the focus record
                    self.delete.delete_target(focus_id, "focus")
                # Check if this focus is the last one for its school
                school_id = None
                try:
                    school_query = self.cursor.execute(
                        "SELECT school FROM focus WHERE id = ?", (int(focus_id),)
                    )
                    school_result = school_query.fetchone()
                    if school_result:
                        school_id = school_result[0]
                except Exception as e:
                    print(f"Error querying school for focus {focus_id}: {e}")

                if school_id:
                    # Count how many focuses are left for this school
                    remaining_query = self.cursor.execute(
                        "SELECT COUNT(*) FROM focus WHERE school = ?", (school_id,)
                    )
                    remaining_focuses = remaining_query.fetchone()[0]

                    # If this was the last focus, delete the school too
                    if remaining_focuses <= 1:  # Using <= 1 because the focus we're deleting is still counted
                        self.delete.delete_target(str(school_id), "school")

        # Determine how many 'new' entries we have
        new_entries_count = 0
        if 'new_rowid' in raw_form_dict:
            new_entries_count = len(raw_form_dict['new_rowid'])

        # Process existing records first
        existing_records = {}
        for key, value in raw_form_dict.items():
            # Skip new entries for now
            if key.startswith('new_'):
                continue

            # Handle existing entries
            parts = key.split('_')
            if len(parts) >= 2:
                record_id = parts[0]
                field_type = parts[1]

                # Initialize record if it doesn't exist
                if record_id not in existing_records:
                    existing_records[record_id] = {
                        'school': {},
                        'focus': {}
                    }

                # Handle different field types
                if field_type == 'school':
                    # Extract the attribute name (everything after 'school_')
                    attr = '_'.join(parts[2:]) if len(parts) > 2 else parts[-1]
                    existing_records[record_id]['school'][attr] = value[0]
                elif field_type == 'focus':
                    # Extract the attribute name (everything after 'focus_')
                    attr = '_'.join(parts[2:]) if len(parts) > 2 else parts[-1]
                    existing_records[record_id]['focus'][attr] = value[0]
                elif field_type == 'rowid':
                    existing_records[record_id]['rowid'] = value[0]

        # Process existing records
        for record_id, data in existing_records.items():
            school_data = data.get('school', {})
            focus_data = data.get('focus', {})

            # Update school if we have school data
            if 'name' in school_data and record_id.isdigit():
                school_id = int(record_id)

                # Prepare school update data
                school_update = {
                    'id': school_id,
                    'name': school_data.get('name', ''),
                    'location': school_data.get('location', ''),
                    'state': 1 if 'enabled' in school_data else 0
                }

                # Update school
                self.update.multi_column('school', **school_update)

            # Update focus if we have focus data
            if 'name' in focus_data and record_id.isdigit():
                focus_id = int(record_id)

                # Prepare focus update data
                focus_update = {
                    'id': focus_id,
                    'school': int(record_id),  # Link to school ID
                    'name': focus_data.get('name', ''),
                    'startdate': date_adapter(focus_data.get('startdate', '')),
                    'enddate': date_adapter(focus_data.get('enddate', '')),
                    'state': 1 if 'enabled' in focus_data else 0
                }

                # Update focus
                self.update.multi_column('focus', **focus_update)

        # Now process new entries
        for i in range(new_entries_count):
            # First insert the school
            school_name = raw_form_dict.get('new_school_name', [''])[i] if i < len(
                raw_form_dict.get('new_school_name', [])) else ''
            school_location = raw_form_dict.get('new_school_location', [''])[i] if i < len(
                raw_form_dict.get('new_school_location', [])) else ''
            school_enabled = 1 if 'new_school_enabled' in raw_form_dict and i < len(
                raw_form_dict['new_school_enabled']) else 0

            # Skip if we don't have a school name
            if not school_name:
                continue

            # Insert school
            school_insert = {
                'name': school_name,
                'location': school_location,
                'state': school_enabled
            }

            # Insert the school first
            self.insert.multi_column('school', **school_insert)

            # Query the DB to get the school_id by name - more reliable than relying on a return value
            school_id = self.query.query_id(school_name, 'school')

            # Skip focus insert if we couldn't get the school_id
            if not school_id:
                continue

            # Now insert the focus for this school
            focus_name = raw_form_dict.get('new_focus_name', [''])[i] if i < len(
                raw_form_dict.get('new_focus_name', [])) else ''
            focus_startdate = raw_form_dict.get('new_focus_startdate', [''])[i] if i < len(
                raw_form_dict.get('new_focus_startdate', [])) else ''
            focus_enddate = raw_form_dict.get('new_focus_enddate', [''])[i] if i < len(
                raw_form_dict.get('new_focus_enddate', [])) else ''
            focus_enabled = 1 if 'new_focus_enabled' in raw_form_dict and i < len(
                raw_form_dict['new_focus_enabled']) else 0

            # Only insert focus if we have a name
            if focus_name:
                focus_insert = {
                    'school': school_id,
                    'name': focus_name,
                    'startdate': date_adapter(focus_startdate),
                    'enddate': date_adapter(focus_enddate),
                    'state': focus_enabled
                }

                # Insert the focus
                self.insert.multi_column('focus', **focus_insert)

        return

    def update_glossary(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the glossary table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """
        # Get raw form data as dictionary with arrays
        raw_form_dict = form_data.to_dict(flat=False)

        # Process existing glossary items
        existing_items = {}
        for key, value in raw_form_dict.items():
            # Skip new entries
            if key.startswith('new'):
                continue

            # Process delete entries (if any)
            if '_delete' in key:
                item_id = key.split('_')[0]
                self.delete.delete_target(item_id, 'glossary')
                continue

            # Process existing glossary fields
            parts = key.split('_')
            if len(parts) >= 2:
                item_id = parts[0]

                # Initialize record if it doesn't exist
                if item_id not in existing_items:
                    existing_items[item_id] = {}

                # Store the field value
                field_name = '_'.join(parts[1:])
                existing_items[item_id][field_name] = value[0]

        # Update existing glossary items
        for item_id, data in existing_items.items():
            if item_id.isdigit() and 'term' in data:
                update_data = {
                    'id': int(item_id),
                    'term': data.get('term', ''),
                    'url': data.get('url', ''),
                    'description': data.get('description', ''),
                    'state': 1 if 'description_enabled' in data else 0
                }

                self.update.multi_column('glossary', **update_data)

        # Process new glossary entries
        new_items = {}
        for key in raw_form_dict:
            if key.startswith('new') and '_term' in key:
                entry_id = key.split('_')[0]  # Get 'new1', 'new2', etc.

                if entry_id not in new_items:
                    new_items[entry_id] = {}

                # Get the term
                new_items[entry_id]['term'] = raw_form_dict[key][0]

                # Try to get corresponding URL
                url_key = f"{entry_id}_url"
                if url_key in raw_form_dict:
                    new_items[entry_id]['url'] = raw_form_dict[url_key][0]
                else:
                    new_items[entry_id]['url'] = ''

                # Try to get corresponding description
                desc_key = f"{entry_id}_description"
                if desc_key in raw_form_dict:
                    new_items[entry_id]['description'] = raw_form_dict[desc_key][0]
                else:
                    new_items[entry_id]['description'] = ''

                # Check if enabled
                enabled_key = f"{entry_id}_description_enabled"
                new_items[entry_id]['state'] = 1 if enabled_key in raw_form_dict else 0

        # Insert all new glossary items
        for entry_id, data in new_items.items():
            if 'term' in data and data['term']:  # Only insert if we have a term
                insert_data = {
                    'term': data['term'],
                    'url': data.get('url', ''),
                    'description': data.get('description', ''),
                    'state': data.get('state', 1)
                }

                self.insert.multi_column('glossary', **insert_data)

        # Commit changes
        self.conn.commit()
        return

    def update_achievements(self, form):
        """
        Updates the achievement, employer, and position tables based on form data.
        :param form: Form data from request.
        """
        # Create a list of all achievement IDs
        achievement_ids = []

        # Debug: Log form data
        print("DEBUG - Form data:")
        for key, value in form.items():
            print(f"  {key}: {value}")

        # Process each form field to identify achievement IDs
        for key in form:
            if key.endswith("_rowid"):
                achievement_id = key.split("_")[0]
                achievement_ids.append(achievement_id)

        print(f"DEBUG - Found achievement IDs: {achievement_ids}")

        # Process each achievement
        for achievement_id in achievement_ids:
            # Check if we need to delete this achievement
            if f"{achievement_id}_delete" in form:
                print(f"DEBUG - Deleting achievement ID: {achievement_id}")
                self.delete.delete_target(achievement_id, "achievement")
                continue

            # Get the employer/school ID and type
            employer_id = form.get(f"{achievement_id}_employer_dropdown")
            employer_type = form.get(f"{achievement_id}_employer_type", "employer")

            # Get employer name to help detect if it's a school
            employer_name = form.get(f"{achievement_id}_employer", "").strip()

            # Detect if this is actually a school by checking for " (College)" suffix
            is_school = "(College)" in employer_name
            if is_school:
                employer_type = "school"
                print(f"DEBUG - Detected school from employer name: {employer_name}")

            # Get the position/focus ID and type
            position_value = form.get(f"{achievement_id}_position_dropdown")
            position_type = form.get(f"{achievement_id}_position_type", "position")

            # Detect if this is actually a focus by checking for " (Focus)" suffix
            position_name = form.get(f"{achievement_id}_position", "").strip()
            is_focus = "(Focus)" in position_name
            if is_focus:
                position_type = "focus"
                print(f"DEBUG - Detected focus from position name: {position_name}")

            # Debug: Log key values
            print(f"DEBUG - Achievement {achievement_id}:")
            print(f"  Employer ID: {employer_id}, Type: {employer_type}")
            print(f"  Position Value: {position_value}, Type: {position_type}")

            # Get the achievement descriptions
            shortdesc = form.get(f"{achievement_id}_shortdesc", "")
            longdesc = form.get(f"{achievement_id}_longdesc", "")

            # Get the enabled state
            longdesc_enabled = f"{achievement_id}_longdesc_enabled" in form

            # Check if this is a new achievement
            if achievement_id.startswith("new"):
                # Handle new achievement creation based on the types
                if employer_type == "employer" and position_type == "position":
                    # This is a regular employer/position achievement

                    # VALIDATE EMPLOYER ID first - if invalid, skip completely
                    if not employer_id or employer_id == "0":
                        print(f"WARNING: Invalid employer value ({employer_id}). Skipping achievement creation.")
                        continue  # Skip this achievement

                    # Query the actual employer ID
                    try:
                        employer_id = int(self.query.query_id(employer_name, "employer"))
                        # Validate the returned employer_id
                        if employer_id <= 0:
                            print(
                                f"WARNING: Invalid queried employer ID ({employer_id}). Skipping achievement creation.")
                            continue
                    except (ValueError, TypeError) as e:
                        print(f"ERROR: Invalid employer ID format: {e}. Skipping achievement creation.")
                        continue

                    # VALIDATE POSITION ID - Check if position_value is valid
                    position_id = None  # Default to None (NULL in database)
                    if position_value and position_value != "0":
                        try:
                            position_id = int(self.query.query_id(position_value, "position"))
                            # Validate the returned position_id
                            if position_id <= 0:
                                print(f"WARNING: Invalid queried position ID ({position_id}). Setting to NULL.")
                                position_id = None
                        except (ValueError, TypeError) as e:
                            print(f"ERROR: Invalid position ID format: {e}. Setting to NULL.")
                            position_id = None
                    else:
                        print(f"WARNING: Empty position value. Setting to NULL.")

                    print(f"DEBUG - New achievement with employer ID: {employer_id}, position ID: {position_id}")

                    try:
                        self.insert.multi_column("achievement",
                                                 employer=employer_id,
                                                 position=position_id,
                                                 shortdesc=shortdesc,
                                                 longdesc=longdesc,
                                                 state=1 if longdesc_enabled else 0
                                                 )
                        print(f"SUCCESS: Created new achievement with employer={employer_id}, position={position_id}")
                    except Exception as e:
                        print(f"ERROR creating achievement: {e}")
                        # Continue with other achievements rather than letting the error cascade
                        continue

                elif employer_type == "school" or is_school:
                    # This is a school/focus achievement
                    school_name = employer_name.replace(" (College)", "")

                    # Validate school ID
                    try:
                        school_id = int(self.query.query_id(school_name, "school"))
                        if school_id <= 0:
                            print(f"WARNING: Invalid school ID ({school_id}). Skipping achievement creation.")
                            continue
                    except (ValueError, TypeError) as e:
                        print(f"ERROR: Invalid school ID format: {e}. Skipping achievement creation.")
                        continue

                    # Handle focus vs position
                    position_to_use = None  # Default to NULL
                    if position_type == "focus" or is_focus:
                        focus_name = position_name.replace(" (Focus)", "")
                        try:
                            focus_id = int(self.query.query_id(focus_name, "focus"))
                            if focus_id > 0:
                                position_to_use = focus_id
                            else:
                                print(f"WARNING: Invalid focus ID ({focus_id}). Using NULL instead.")
                        except (ValueError, TypeError) as e:
                            print(f"ERROR: Invalid focus ID format: {e}. Using NULL instead.")
                    else:
                        # VALIDATE POSITION VALUE
                        if position_value and position_value != "0":
                            try:
                                position_to_use = int(position_value)
                                if position_to_use <= 0:
                                    print(f"WARNING: Invalid position value ({position_to_use}). Using NULL instead.")
                                    position_to_use = None
                            except (ValueError, TypeError):
                                print(f"WARNING: Invalid position value format. Using NULL instead.")
                                position_to_use = None
                        else:
                            print(f"INFO: No position specified. Using NULL.")

                    print(f"DEBUG - New achievement with school ID: {school_id}, position ID: {position_to_use}")

                    try:
                        # For school achievements, we use the school ID and focus/position ID
                        self.insert.multi_column("achievement",
                                                 school=school_id,
                                                 employer=None,  # Make sure employer is NULL
                                                 position=position_to_use,
                                                 shortdesc=shortdesc,
                                                 longdesc=longdesc,
                                                 state=1 if longdesc_enabled else 0
                                                 )
                        print(f"SUCCESS: Created new achievement with school={school_id}, position={position_to_use}")
                    except Exception as e:
                        print(f"ERROR creating achievement: {e}")
                        # Continue with other achievements rather than letting the error cascade
                        continue
                else:
                    print(f"WARNING: Couldn't determine achievement type. Skipping.")
                    continue
            else:
                # Update existing achievement
                try:
                    update_data = {
                        "id": achievement_id,
                        "shortdesc": shortdesc,
                        "longdesc": longdesc,
                        "state": 1 if longdesc_enabled else 0
                    }

                    # Update employer/position references based on the types
                    if (employer_type == "school" or is_school) and employer_id:
                        # Handle school case
                        school_id = None
                        if is_school:
                            # Extract school name and get ID
                            school_name = employer_name.replace(" (College)", "")
                            try:
                                school_id = int(self.query.query_id(school_name, "school"))
                                if school_id <= 0:
                                    print(f"WARNING: Invalid school ID ({school_id}). Skipping school update.")
                                    school_id = None
                            except (ValueError, TypeError) as e:
                                print(f"ERROR: Invalid school ID format: {e}. Skipping school update.")
                        else:
                            # Use the dropdown ID directly
                            try:
                                school_id = int(employer_id)
                                if school_id <= 0:
                                    print(
                                        f"WARNING: Invalid school ID from dropdown ({school_id}). Skipping school update.")
                                    school_id = None
                            except (ValueError, TypeError) as e:
                                print(f"ERROR: Invalid school ID from dropdown: {e}. Skipping school update.")

                        if school_id is not None:
                            update_data["school"] = school_id
                            # Clear employer when school is set
                            update_data["employer"] = None
                            print(f"DEBUG - Setting school ID: {update_data['school']}")

                    else:
                        # Handle employer case
                        if employer_id:
                            try:
                                employer_id_int = int(employer_id)
                                if employer_id_int > 0:
                                    update_data["employer"] = employer_id_int
                                    # Clear school when employer is set
                                    update_data["school"] = None
                                    print(f"DEBUG - Setting employer ID: {update_data['employer']}")
                                else:
                                    print(
                                        f"WARNING: Invalid employer ID ({employer_id_int}). Skipping employer update.")
                            except (ValueError, TypeError) as e:
                                print(f"ERROR: Invalid employer ID format: {e}. Skipping employer update.")

                    # Update position/focus ID
                    if position_value:
                        position_id = None

                        if position_type == "focus" or is_focus:
                            # Handle focus type
                            if is_focus:
                                # Extract focus name and get ID
                                focus_name = position_name.replace(" (Focus)", "")
                                try:
                                    focus_id = int(self.query.query_id(focus_name, "focus"))
                                    if focus_id > 0:
                                        position_id = focus_id
                                    else:
                                        print(f"WARNING: Invalid focus ID ({focus_id}). Skipping position update.")
                                except (ValueError, TypeError) as e:
                                    print(f"ERROR: Invalid focus ID format: {e}. Skipping position update.")
                            else:
                                # Use the dropdown ID directly
                                try:
                                    position_id = int(position_value)
                                    if position_id <= 0:
                                        print(
                                            f"WARNING: Invalid position ID ({position_id}). Skipping position update.")
                                        position_id = None
                                except (ValueError, TypeError) as e:
                                    print(f"ERROR: Invalid position ID format: {e}. Skipping position update.")
                        else:
                            # Handle regular position
                            try:
                                position_id = int(position_value)
                                if position_id <= 0:
                                    print(f"WARNING: Invalid position ID ({position_id}). Skipping position update.")
                                    position_id = None
                            except (ValueError, TypeError) as e:
                                print(f"ERROR: Invalid position ID format: {e}. Skipping position update.")

                        if position_id is not None:
                            update_data["position"] = position_id
                            print(f"DEBUG - Setting position ID: {update_data['position']}")

                    print(f"DEBUG - Final update data: {update_data}")
                    self.update.multi_column("achievement", **update_data)
                    print(f"SUCCESS: Updated achievement {achievement_id}")
                except Exception as e:
                    print(f"ERROR updating achievement {achievement_id}: {e}")
                    # Continue with other achievements rather than letting the error cascade
                    continue