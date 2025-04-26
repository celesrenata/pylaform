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

    def dropdowns(self, target):
        """
        Return dropdown data for the target section.
        Enhanced to handle separate employer and school data for achievements.

        :param target: Target section name (e.g., "achievements", "skills", "education", "employment")
        :return: Dictionary with dropdown data
        """
        if target == "achievements":
            try:
                # Debug what's happening
                print(f"Generating dropdowns for: {target}")

                # Get employer data
                employers = self.cursor.execute(
                    "SELECT id, employer, state FROM employer ORDER BY employer"
                ).fetchall()

                # Convert to list of dictionaries with proper keys for template compatibility
                employer_list = []
                for employer_id, employer_name, state in employers:
                    employer_list.append({
                        "id": employer_id,
                        "name": employer_name,  # Template expects 'name' key
                        "employer": employer_name,  # Some code might expect 'employer' key
                        "state": state,
                        "type": "employer"
                    })

                # Get school data
                schools = self.cursor.execute(
                    "SELECT id, name, state FROM school ORDER BY name"
                ).fetchall()

                # Convert to list of dictionaries with proper keys
                school_list = []
                for school_id, school_name, state in schools:
                    school_list.append({
                        "id": school_id,
                        "name": school_name,
                        "state": state,
                        "type": "school"
                    })

                # Get position data (for regular employment)
                positions = self.cursor.execute(
                    "SELECT p.id, p.position, p.state, p.employer, e.employer as employer_name " +
                    "FROM position p " +
                    "LEFT JOIN employer e ON p.employer = e.id " +
                    "ORDER BY p.position"
                ).fetchall()

                # Convert to list of dictionaries
                position_list = []
                for pos_id, pos_name, pos_state, employer_id, employer_name in positions:
                    position_list.append({
                        "id": pos_id,
                        "name": pos_name,
                        "position": pos_name,  # For backward compatibility
                        "state": pos_state,
                        "employer": employer_id,  # Keep employer id for filtering
                        "employer_name": employer_name,
                        "type": "position"
                    })

                # Get focus data (for school studies)
                focuses = self.cursor.execute(
                    "SELECT f.id, f.name, f.state, f.school, s.name as school_name " +
                    "FROM focus f " +
                    "LEFT JOIN school s ON f.school = s.id " +
                    "ORDER BY f.name"
                ).fetchall()

                # Convert to list of dictionaries
                focus_list = []
                for focus_id, focus_name, focus_state, school_id, school_name in focuses:
                    focus_list.append({
                        "id": focus_id,
                        "name": focus_name,
                        "state": focus_state,
                        "school_id": school_id,
                        "school_name": school_name,
                        "type": "focus"
                    })

                # Build a mapping of employer IDs to position IDs for client-side filtering
                employer_positions_map = {}

                # Add employer -> position mappings
                for position in position_list:
                    employer_id = position.get("employer")
                    if employer_id:
                        if str(employer_id) not in employer_positions_map:
                            employer_positions_map[str(employer_id)] = []
                        employer_positions_map[str(employer_id)].append({
                            "id": position["id"],
                            "name": position["name"],
                            "type": "position"
                        })

                # Add school -> focus mappings
                for focus in focus_list:
                    school_id = focus.get("school_id")
                    if school_id:
                        if str(school_id) not in employer_positions_map:
                            employer_positions_map[str(school_id)] = []
                        employer_positions_map[str(school_id)].append({
                            "id": focus["id"],
                            "name": focus["name"],
                            "type": "focus"
                        })

                # Debug the final data
                dropdown_data = {
                    "employers": employer_list,
                    "schools": school_list,
                    "positions": position_list,
                    "focuses": focus_list,
                    "employer_positions": employer_positions_map  # Map for JS filtering
                }

                print(f"Generated dropdowns with {len(employer_list)} employers, {len(school_list)} schools")
                print(f"Positions: {len(position_list)}, Focuses: {len(focus_list)}")

                return dropdown_data

            except Exception as e:
                print(f"Error in dropdowns for achievements: {e}")
                import traceback
                print(traceback.format_exc())
                return {
                    "employers": [],
                    "schools": [],
                    "positions": [],
                    "focuses": [],
                    "employer_positions": {}
                }

        elif target == "skills":
            try:
                category_query = self.cursor.execute(
                    "SELECT id, category FROM skill ORDER BY state, category"
                ).fetchall()

                subcategory_query = self.cursor.execute(
                    "SELECT id, subcategory, category FROM skill ORDER BY subcategory"
                ).fetchall()

                return {
                    "category": category_query,
                    "subcategory": subcategory_query
                }
            except Exception as e:
                print(f"Error in dropdowns for skills: {e}")
                return {"category": [], "subcategory": []}

        elif target == "education":
            try:
                degree_query = self.cursor.execute(
                    "SELECT id, name FROM focus ORDER BY state DESC, name"
                ).fetchall()

                school_query = self.cursor.execute(
                    "SELECT id, name FROM school ORDER BY state DESC, name"
                ).fetchall()

                return {
                    "degree": degree_query,
                    "school": school_query
                }
            except Exception as e:
                print(f"Error in dropdowns for education: {e}")
                return {"degree": [], "school": []}

        elif target == "employment":
            try:
                employer_query = self.cursor.execute(
                    "SELECT id, employer FROM employer ORDER BY state DESC, employer"
                ).fetchall()

                position_query = self.cursor.execute(
                    "SELECT id, position, employer FROM position ORDER BY position"
                ).fetchall()

                return {
                    "employer": employer_query,
                    "position": position_query
                }
            except Exception as e:
                print(f"Error in dropdowns for employment: {e}")
                return {"employer": [], "position": []}

        # Default return for unrecognized targets
        return {}

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
        # Get raw form data and analyze it
        raw_form_dict = form_data.to_dict(flat=False)

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
        Updates the achievement table with separate employer and school columns.

        :param form: Form data from request.
        """
        import traceback

        # Debug the form data
        print("Form keys:", list(form.keys()))

        # Create a list of all achievement IDs
        achievement_ids = []

        # Process each form field to identify achievement IDs
        for key in form:
            if key.endswith("_rowid") or key.endswith("_shortdesc"):
                achievement_id = key.split("_")[0]
                if achievement_id not in achievement_ids:
                    achievement_ids.append(achievement_id)

        print(f"Found {len(achievement_ids)} achievements to process")

        # Process each achievement
        for achievement_id in achievement_ids:
            print(f"\nProcessing achievement ID: {achievement_id}")

            # Check if we need to delete this achievement
            if f"{achievement_id}_delete" in form:
                print(f"Deleting achievement {achievement_id}")
                self.delete(f"DELETE FROM achievement WHERE id = {achievement_id}")
                continue

            # Get values from form
            employer_dropdown = form.get(f"{achievement_id}_employer_dropdown", "")
            position_dropdown = form.get(f"{achievement_id}_position_dropdown", "")

            # Get IDs directly from hidden fields
            employer_id = form.get(f"{achievement_id}_employer_id", "")
            position_id = form.get(f"{achievement_id}_position_id", "")

            # Parse the type prefixes from dropdown values if needed
            if employer_dropdown and employer_dropdown not in ["EDIT", "ADD", "new"]:
                if '_' in employer_dropdown:
                    employer_type, employer_dropdown_id = employer_dropdown.split('_', 1)
                    # Only update the type and ID if they're different from what's in the hidden fields
                    if employer_type in ["employer", "school"] and employer_dropdown_id.isdigit():
                        employer_id = employer_dropdown_id
                        form[f"{achievement_id}_employer_type"] = employer_type
                        form[f"{achievement_id}_employer_id"] = employer_dropdown_id

            if position_dropdown and position_dropdown not in ["EDIT", "ADD", "new"]:
                if '_' in position_dropdown:
                    position_type, position_dropdown_id = position_dropdown.split('_', 1)
                    # Only update the type and ID if they're different from what's in the hidden fields
                    if position_type in ["position", "focus"] and position_dropdown_id.isdigit():
                        position_id = position_dropdown_id
                        form[f"{achievement_id}_position_type"] = "focus" if position_type == "focus" else "position"
                        form[f"{achievement_id}_position_id"] = position_dropdown_id

            # Read values from form - updated if dropdown values were processed above
            employer_type = form.get(f"{achievement_id}_employer_type", "employer")
            employer_name = form.get(f"{achievement_id}_employer", "")
            position_type = form.get(f"{achievement_id}_position_type", "position")
            position_name = form.get(f"{achievement_id}_position", "")

            # Get achievement content
            shortdesc = form.get(f"{achievement_id}_shortdesc", "")
            longdesc = form.get(f"{achievement_id}_longdesc", "")

            # Get enabled state (check various field names that might be used)
            longdesc_enabled = (
                    form.get(f"{achievement_id}_longdesc_enabled") == "on" or
                    form.get(f"{achievement_id}_achievement_enabled") == "on"
            )

            # Debug info
            print(f"Achievement: {achievement_id}")
            print(f"Employer ID: {employer_id}, Type: {employer_type}, Name: {employer_name}")
            print(f"Position ID: {position_id}, Type: {position_type}, Name: {position_name}")
            print(f"Enabled: {longdesc_enabled}")

            # Initialize employer and school IDs to NULL
            final_employer_id = "NULL"
            final_school_id = "NULL"

            # Process based on employer type
            if employer_type == "school":
                # This is a school, so set school_id and leave employer_id as NULL
                if employer_id and employer_id not in ["EDIT", "ADD", "new"]:
                    try:
                        # Verify the school ID exists
                        result = self.cursor.execute(
                            "SELECT id FROM school WHERE id = ?",
                            (employer_id,)
                        ).fetchone()

                        if result:
                            final_school_id = employer_id
                            print(f"Using school ID: {final_school_id}")
                    except Exception as e:
                        print(f"Error verifying school ID: {e}")

                # If ID lookup failed, try by name
                if final_school_id == "NULL":
                    try:
                        # Clean the name (replace + with spaces)
                        clean_name = employer_name.replace("+", " ").strip()
                        if "(College)" in clean_name:
                            clean_name = clean_name.replace(" (College)", "")

                        # Look up school by name
                        result = self.cursor.execute(
                            "SELECT id FROM school WHERE name = ?",
                            (clean_name,)
                        ).fetchone()

                        if result:
                            final_school_id = result[0]
                            print(f"Found school by name '{clean_name}', ID: {final_school_id}")
                    except Exception as e:
                        print(f"Error looking up school by name: {e}")
            else:  # employer_type is "employer"
                # This is an employer, so set employer_id and leave school_id as NULL
                if employer_id and employer_id not in ["EDIT", "ADD", "new"]:
                    try:
                        # Verify the employer ID exists
                        result = self.cursor.execute(
                            "SELECT id FROM employer WHERE id = ?",
                            (employer_id,)
                        ).fetchone()

                        if result:
                            final_employer_id = employer_id
                            print(f"Using employer ID: {final_employer_id}")
                    except Exception as e:
                        print(f"Error verifying employer ID: {e}")

                # If ID lookup failed, try by name
                if final_employer_id == "NULL":
                    try:
                        # Clean the name (replace + with spaces)
                        clean_name = employer_name.replace("+", " ").strip()

                        # Look up employer by name
                        result = self.cursor.execute(
                            "SELECT id FROM employer WHERE employer = ?",
                            (clean_name,)
                        ).fetchone()

                        if result:
                            final_employer_id = result[0]
                            print(f"Found employer by name '{clean_name}', ID: {final_employer_id}")
                    except Exception as e:
                        print(f"Error looking up employer by name: {e}")

            # Validate position ID
            final_position_id = None

            if position_id and position_id not in ["EDIT", "ADD", "new"]:
                try:
                    if position_type == "focus":
                        # Verify focus ID
                        result = self.cursor.execute(
                            "SELECT id FROM focus WHERE id = ?",
                            (position_id,)
                        ).fetchone()

                        if result:
                            final_position_id = position_id
                            print(f"Using focus ID: {final_position_id}")
                    else:  # position type
                        # Verify position ID
                        result = self.cursor.execute(
                            "SELECT id FROM position WHERE id = ?",
                            (position_id,)
                        ).fetchone()

                        if result:
                            final_position_id = position_id
                            print(f"Using position ID: {final_position_id}")
                except Exception as e:
                    print(f"Error verifying position ID: {e}")

            # If ID lookup failed, try by name
            if not final_position_id:
                try:
                    # Clean the name
                    clean_name = position_name.replace("+", " ").strip()
                    if "(Focus)" in clean_name:
                        clean_name = clean_name.replace(" (Focus)", "")

                    if position_type == "focus":
                        # Look up focus by name
                        result = self.cursor.execute(
                            "SELECT id FROM focus WHERE name = ?",
                            (clean_name,)
                        ).fetchone()
                        if result:
                            final_position_id = result[0]
                            print(f"Found focus by name '{clean_name}', ID: {final_position_id}")
                    else:
                        # Look up position by name
                        result = self.cursor.execute(
                            "SELECT id FROM position WHERE position = ?",
                            (clean_name,)
                        ).fetchone()
                        if result:
                            final_position_id = result[0]
                            print(f"Found position by name '{clean_name}', ID: {final_position_id}")
                except Exception as e:
                    print(f"Error looking up position by name: {e}")

            # Still no position ID? This is a problem
            if not final_position_id:
                print(f"WARNING: Could not determine valid position ID for '{position_name}'")
                final_position_id = "NULL"

            # Final verification
            print(
                f"FINAL: Employer ID: {final_employer_id}, School ID: {final_school_id}, Position ID: {final_position_id}")

            # Update or insert the achievement
            try:
                if achievement_id.startswith("new"):
                    # Create new achievement using the new schema with school and employer
                    self.cursor.execute(
                        """
                        INSERT INTO achievement
                            (employer, school, position, shortdesc, longdesc, state)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            None if final_employer_id == "NULL" else final_employer_id,
                            None if final_school_id == "NULL" else final_school_id,
                            None if final_position_id == "NULL" else final_position_id,
                            shortdesc,
                            longdesc,
                            int(longdesc_enabled)
                        )
                    )
                    self.conn.commit()
                    print(
                        f"Inserted new achievement with employer={final_employer_id}, school={final_school_id}, position={final_position_id}")
                else:
                    # Update existing achievement with the new schema
                    self.cursor.execute(
                        """
                        UPDATE achievement
                        SET employer  = ?,
                            school    = ?,
                            position  = ?,
                            shortdesc = ?,
                            longdesc  = ?,
                            state     = ?
                        WHERE id = ?
                        """,
                        (
                            None if final_employer_id == "NULL" else final_employer_id,
                            None if final_school_id == "NULL" else final_school_id,
                            None if final_position_id == "NULL" else final_position_id,
                            shortdesc,
                            longdesc,
                            int(longdesc_enabled),
                            achievement_id
                        )
                    )
                    self.conn.commit()
                    print(
                        f"Updated achievement {achievement_id} with employer={final_employer_id}, school={final_school_id}, position={final_position_id}")
            except Exception as e:
                print(f"Error updating achievement: {e}")
                print(traceback.format_exc())

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
