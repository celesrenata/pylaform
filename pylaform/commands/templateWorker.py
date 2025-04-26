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
                # Use correct table name 'achievement' for the mapping hint
                return self.query.get_options(["employer", "position", "achievement"], ["employer", "position", ""])
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
        Updates the skills table.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """
        # Get raw form data as dictionary with arrays
        raw_form_dict = form_data.to_dict(flat=False)

        # Process existing skills
        existing_skills = {}
        for key, value in raw_form_dict.items():
            # Skip new entries
            if key.startswith('new'):
                continue

            # Process delete entries
            if '_delete' in key:
                skill_id = key.split('_')[0]
                self.delete.delete_target(skill_id, 'skill')
                continue

            # Process existing skills fields
            parts = key.split('_')
            if len(parts) >= 2:
                skill_id = parts[0]

                # Initialize record if it doesn't exist
                if skill_id not in existing_skills:
                    existing_skills[skill_id] = {}

                # Store the field value
                field_name = '_'.join(parts[1:])
                existing_skills[skill_id][field_name] = value[0]

        # Update existing skills
        for skill_id, data in existing_skills.items():
            if skill_id.isdigit():
                # Handle employer and position dropdowns
                employer_id = data.get('employer_dropdown', '')
                position_id = data.get('position_dropdown', '')

                # Ensure we're using valid IDs
                if employer_id and employer_id not in ['EDIT', 'ADD']:
                    employer = employer_id
                else:
                    # Try to get employer from the form data
                    employer_name = data.get('employer', '')
                    if employer_name:
                        employer = str(self.query.query_id(employer_name, 'employer'))
                    else:
                        employer = ''

                if position_id and position_id not in ['EDIT', 'ADD']:
                    position = position_id
                else:
                    # Try to get position from the form data
                    position_name = data.get('position', '')
                    if position_name:
                        position = str(self.query.query_id(position_name, 'position'))
                    else:
                        position = ''

                # Prepare skill update data
                update_data = {
                    'id': int(skill_id),
                    'category': data.get('category', ''),
                    'subcategory': data.get('subcategory', ''),
                    'employer': employer,
                    'position': position,
                    'shortdesc': data.get('shortdesc', ''),
                    'longdesc': data.get('longdesc', ''),
                    'state': 1 if 'longdesc_enabled' in data else 0
                }

                # Optional fields - only include if present
                if 'categoryorder' in data:
                    update_data['categoryorder'] = data.get('categoryorder', '0')
                if 'skillorder' in data:
                    update_data['skillorder'] = data.get('skillorder', '0')

                # Update skill
                self.update.multi_column('skill', **update_data)

        # Process new skills entries
        new_skills = {}
        for key in raw_form_dict:
            if key.startswith('new') and ('_category' in key or '_shortdesc' in key):
                entry_id = key.split('_')[0]  # Get 'new1', 'new2', etc.

                if entry_id not in new_skills:
                    new_skills[entry_id] = {}

                # Store all fields for this entry
                for field_key, field_values in raw_form_dict.items():
                    if field_key.startswith(entry_id + '_'):
                        field_name = '_'.join(field_key.split('_')[1:])
                        new_skills[entry_id][field_name] = field_values[0]

        # Insert all new skills
        for entry_id, data in new_skills.items():
            if ('category' in data and data['category']) and ('shortdesc' in data and data['shortdesc']):
                # Handle employer and position dropdowns
                employer_id = data.get('employer_dropdown', '')
                position_id = data.get('position_dropdown', '')

                # Ensure we're using valid IDs
                if employer_id and employer_id not in ['EDIT', 'ADD']:
                    employer = employer_id
                else:
                    # Try to get employer from the form data
                    employer_name = data.get('employer', '')
                    if employer_name:
                        employer = str(self.query.query_id(employer_name, 'employer'))
                    else:
                        employer = ''

                if position_id and position_id not in ['EDIT', 'ADD']:
                    position = position_id
                else:
                    # Try to get position from the form data
                    position_name = data.get('position', '')
                    if position_name:
                        position = str(self.query.query_id(position_name, 'position'))
                    else:
                        position = ''

                # Create a new skill record
                insert_data = {
                    'category': data.get('category', ''),
                    'subcategory': data.get('subcategory', ''),
                    'employer': employer,
                    'position': position,
                    'shortdesc': data.get('shortdesc', ''),
                    'longdesc': data.get('longdesc', ''),
                    'state': 1 if 'longdesc_enabled' in data else 0
                }

                # Optional fields - only include if present
                if 'categoryorder' in data:
                    insert_data['categoryorder'] = data.get('categoryorder', '0')
                if 'skillorder' in data:
                    insert_data['skillorder'] = data.get('skillorder', '0')

                # Insert the new skill
                self.insert.multi_column('skill', **insert_data)

        # Commit changes
        self.conn.commit()
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

    def update_achievements(self, form_data: ImmutableMultiDict) -> None:
        """
        Updates the achievement table with relationships to employer and position.
        :param ImmutableMultiDict form_data: Form data from template.
        :return None: None
        """
        # Get raw form data as dictionary with arrays
        raw_form_dict = form_data.to_dict(flat=False)

        # Process existing achievements
        existing_achievements = {}
        for key, value in raw_form_dict.items():
            # Skip new entries
            if key.startswith('new'):
                continue

            # Process delete entries
            if '_delete' in key:
                achievement_id = key.split('_')[0]
                self.delete.delete_target(achievement_id, 'achievement')
                continue

            # Process existing achievement fields
            parts = key.split('_')
            if len(parts) >= 2:
                achievement_id = parts[0]

                # Initialize record if it doesn't exist
                if achievement_id not in existing_achievements:
                    existing_achievements[achievement_id] = {}

                # Store the field value
                field_name = '_'.join(parts[1:])
                existing_achievements[achievement_id][field_name] = value[0]

        # Update existing achievements
        for achievement_id, data in existing_achievements.items():
            if achievement_id.isdigit():
                # Handle employer and position dropdowns
                employer_id = data.get('employer_dropdown', '')
                position_id = data.get('position_dropdown', '')

                # Validate that the position belongs to the employer
                if employer_id and position_id:
                    # Check if the position belongs to the selected employer
                    self.cursor.execute(
                        "SELECT employer FROM position WHERE id = ?",
                        (position_id,)
                    )
                    result = self.cursor.fetchone()
                    if result and str(result[0]) != str(employer_id):
                        # Position doesn't belong to this employer, don't update
                        continue

                # Prepare achievement update data
                update_data = {
                    'id': int(achievement_id),
                    'employer': employer_id if employer_id else None,
                    'position': position_id if position_id else None,
                    'shortdesc': data.get('shortdesc', ''),
                    'longdesc': data.get('longdesc', ''),
                    'state': 1 if 'longdesc_enabled' in data else 0
                }

                # Update achievement only if we have valid employer and position
                if update_data['employer'] and update_data['position']:
                    self.update.multi_column('achievement', **update_data)

        # Process new achievement entries
        new_achievements = {}
        for key in raw_form_dict:
            if key.startswith('new') and ('_shortdesc' in key or '_longdesc' in key):
                entry_id = key.split('_')[0]  # Get 'new1', 'new2', etc.

                if entry_id not in new_achievements:
                    new_achievements[entry_id] = {}

                # Store all fields for this entry
                for field_key, field_values in raw_form_dict.items():
                    if field_key.startswith(entry_id + '_'):
                        field_name = '_'.join(field_key.split('_')[1:])
                        new_achievements[entry_id][field_name] = field_values[0]

        # Insert all new achievements
        for entry_id, data in new_achievements.items():
            # Handle employer and position dropdowns
            employer_id = data.get('employer_dropdown', '')
            position_id = data.get('position_dropdown', '')

            # Validate that the position belongs to the employer
            if employer_id and position_id:
                # Check if the position belongs to the selected employer
                self.cursor.execute(
                    "SELECT employer FROM position WHERE id = ?",
                    (position_id,)
                )
                result = self.cursor.fetchone()
                if result and str(result[0]) != str(employer_id):
                    # Position doesn't belong to this employer, skip this entry
                    continue

            # Only proceed if we have the required data
            if 'shortdesc' in data and employer_id and position_id:
                # Create a new achievement record
                insert_data = {
                    'employer': employer_id,
                    'position': position_id,
                    'shortdesc': data.get('shortdesc', ''),
                    'longdesc': data.get('longdesc', ''),
                    'state': 1 if 'longdesc_enabled' in data else 0
                }

                # Insert the new achievement
                self.insert.multi_column('achievement', **insert_data)

        # Commit changes
        self.conn.commit()
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
