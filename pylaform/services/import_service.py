# pylaform/services/import_service.py

from pylaform.commands.db import update, query, delete
from pylaform.commands.db.query import Queries
import sqlite3
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Output to console
        logging.FileHandler('linkedin_import_debug.log')  # Also save to a file
    ]
)


class ImportService:
    """Service for importing data from external sources into the application."""

    def __init__(self):
        self.query = Queries()
        self.logger = logging.getLogger(__name__)

    def process_linkedin_import(self, profile_data, import_sections):
        """
        Process LinkedIn profile data and import selected sections

        Args:
            profile_data (dict): LinkedIn profile data
            import_sections (list): List of sections to import

        Returns:
            dict: Result with success status and details
        """
        self.logger.debug("--- DEBUG: Starting LinkedIn import process ---")
        self.logger.debug(f"Sections to import: {import_sections}")

        # Validate profile data
        if not isinstance(profile_data, dict):
            self.logger.error(f"Invalid profile data type: {type(profile_data)}")
            return {
                'success': False,
                'imported_sections': [],
                'errors': ["Invalid profile data format"]
            }

        result = {
            'success': True,
            'imported_sections': [],
            'errors': []
        }

        try:
            # Validate data for each section before trying to import
            if 'basic_info' in import_sections and (
                    'firstName' not in profile_data or
                    'lastName' not in profile_data):
                self.logger.warning("Missing required fields for basic info import")
                result['errors'].append("Basic Info: Missing required fields")
            else:
                # Basic information (contact, summary)
                if 'basic_info' in import_sections:
                    self.logger.debug("--- DEBUG: Importing basic information ---")
                    basic_info_result = self._import_basic_info(profile_data)
                    if basic_info_result['success']:
                        result['imported_sections'].append('Basic Information')
                        self.logger.debug("Basic information imported successfully")
                    else:
                        result['errors'].append(f"Basic Info: {basic_info_result['error']}")
                        self.logger.error(f"Error importing basic info: {basic_info_result['error']}")

            # Employment history - validate first
            if 'experience' in import_sections and (
                    'positions' not in profile_data or
                    not isinstance(profile_data.get('positions'), list)):
                self.logger.warning("Missing or invalid positions data for experience import")
                result['errors'].append("Experience: Missing or invalid positions data")
            else:
                # Process experience if validation passed
                if 'experience' in import_sections:
                    self.logger.debug("--- DEBUG: Importing work experience ---")
                    self.logger.debug(f"Number of positions to import: {len(profile_data.get('positions', []))}")

                    experience_result = self._import_experience(profile_data)
                    if experience_result['success']:
                        result['imported_sections'].append('Work Experience')
                        self.logger.debug("Work experience imported successfully")
                    else:
                        result['errors'].append(f"Experience: {experience_result['error']}")
                        self.logger.error(f"Error importing experience: {experience_result['error']}")

            # Education - validate first
            if 'education' in import_sections and (
                    'education' not in profile_data or
                    not isinstance(profile_data.get('education'), list)):
                self.logger.warning("Missing or invalid education data for education import")
                result['errors'].append("Education: Missing or invalid education data")
            else:
                # Process education if validation passed
                if 'education' in import_sections:
                    self.logger.debug("--- DEBUG: Importing education ---")
                    self.logger.debug(
                        f"Number of education entries to import: {len(profile_data.get('education', []))}")

                    education_result = self._import_education(profile_data)
                    if education_result['success']:
                        result['imported_sections'].append('Education')
                        self.logger.debug("Education imported successfully")
                    else:
                        result['errors'].append(f"Education: {education_result['error']}")
                        self.logger.error(f"Error importing education: {education_result['error']}")

            # Skills - validate first
            if 'skills' in import_sections and (
                    'skills' not in profile_data or
                    not isinstance(profile_data.get('skills'), list)):
                self.logger.warning("Missing or invalid skills data for skills import")
                result['errors'].append("Skills: Missing or invalid skills data")
            else:
                # Process skills if validation passed
                if 'skills' in import_sections:
                    self.logger.debug("--- DEBUG: Importing skills ---")
                    self.logger.debug(f"Number of skills to import: {len(profile_data.get('skills', []))}")

                    skills_result = self._import_skills(profile_data)
                    if skills_result['success']:
                        result['imported_sections'].append('Skills')
                        self.logger.debug("Skills imported successfully")
                    else:
                        result['errors'].append(f"Skills: {skills_result['error']}")
                        self.logger.error(f"Error importing skills: {skills_result['error']}")

            # Overall result
            if len(result['errors']) > 0:
                result['success'] = False

            self.logger.debug(f"--- DEBUG: Import process completed. Success: {result['success']} ---")
            return result

        except Exception as e:
            self.logger.exception("Unexpected error during LinkedIn import:")
            result['success'] = False
            result['errors'].append(str(e))
            return result

    def _import_basic_info(self, profile_data):
        """Import basic profile information"""
        self.logger.debug("--- DEBUG: Processing basic information ---")
        try:
            # Log what data we're using
            self.logger.debug(f"First Name: {profile_data.get('firstName', '')}")
            self.logger.debug(f"Last Name: {profile_data.get('lastName', '')}")
            self.logger.debug(f"Headline: {profile_data.get('headline', '')}")

            # Get summary text
            summary = profile_data.get('summary', '')
            if summary is None:
                summary = ''
            self.logger.debug(f"Summary length: {len(summary)} characters")

            # Use transaction context for database operations
            from pylaform.commands.db.connect import transaction_context

            # Import name information
            if profile_data.get('firstName') and profile_data.get('lastName'):
                try:
                    full_name = f"{profile_data['firstName']} {profile_data['lastName']}"

                    with transaction_context() as conn:
                        cursor = conn.cursor()

                        # Check if name record exists
                        cursor.execute("SELECT id FROM identification WHERE attr = 'name'")
                        result = cursor.fetchone()

                        if result:
                            # Update existing name
                            name_id = result[0]
                            self.logger.debug(f"Updating existing name to: {full_name}")
                            cursor.execute(
                                "UPDATE identification SET value = ? WHERE id = ?",
                                (full_name, name_id)
                            )
                        else:
                            # Insert new name
                            self.logger.debug(f"Inserting new name: {full_name}")
                            cursor.execute(
                                "INSERT INTO identification (attr, value, state) VALUES (?, ?, ?)",
                                ('name', full_name, 1)
                            )
                except Exception as e:
                    self.logger.error(f"Error updating name: {str(e)}")

            # Import summary if available
            if summary:
                try:
                    with transaction_context() as conn:
                        cursor = conn.cursor()

                        # Check if summary exists
                        cursor.execute("SELECT id FROM summary WHERE id = 1")
                        result = cursor.fetchone()

                        if result:
                            # Update existing summary
                            self.logger.debug(f"Updating existing summary with LinkedIn data")
                            cursor.execute(
                                "UPDATE summary SET longdesc = ? WHERE id = 1",
                                (summary,)
                            )
                        else:
                            # Insert new summary
                            self.logger.debug(f"Creating new summary from LinkedIn data")
                            cursor.execute(
                                "INSERT INTO summary (id, shortdesc, longdesc, state, summaryorder) VALUES (?, ?, ?, ?, ?)",
                                (1, 'LinkedIn Profile', summary, 1, 1)
                            )
                except Exception as e:
                    self.logger.error(f"Error updating summary: {str(e)}")

            # Purge the query cache to ensure fresh data is loaded
            self.query.purge_cache("identification")
            self.query.purge_cache("summary")

            return {'success': True}
        except Exception as e:
            self.logger.exception("Error importing basic information:")
            return {'success': False, 'error': str(e)}

    def _import_experience(self, profile_data):
        """Import work experience"""
        self.logger.debug("--- DEBUG: Processing work experience ---")
        try:
            from pylaform.commands.db.connect import transaction_context

            # Get the table schema for position table to check available columns
            position_columns = []
            try:
                with transaction_context(read_only=True) as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA table_info(position)")
                    position_columns = [row[1] for row in cursor.fetchall()]
                    self.logger.debug(f"Position table columns: {position_columns}")
            except Exception as e:
                self.logger.error(f"Error getting position table schema: {str(e)}")

            # First, identify all tables that might have foreign key relationships
            dependent_tables = []
            try:
                with transaction_context(read_only=True) as conn:
                    cursor = conn.cursor()

                    # Get all tables in the database
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    all_tables = [row[0] for row in cursor.fetchall()]
                    self.logger.debug(f"All tables in database: {all_tables}")

                    # For each table, check if it references position or employer
                    for table_name in all_tables:
                        if table_name in ('position', 'employer'):
                            continue  # Skip our main tables

                        # Check for foreign keys to position
                        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                        for fk in cursor.fetchall():
                            referenced_table = fk[2]  # Table referenced by foreign key
                            if referenced_table in ('position', 'employer'):
                                dependent_tables.append({
                                    'table': table_name,
                                    'references': referenced_table
                                })
                                break

                    self.logger.debug(f"Found dependent tables: {dependent_tables}")
            except Exception as e:
                self.logger.error(f"Error identifying dependent tables: {str(e)}")

            # Now handle the import with care for constraints
            with transaction_context() as conn:
                # Enable foreign keys to ensure constraints are respected
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON")

                # First, delete records from dependent tables
                for dependent in dependent_tables:
                    try:
                        table_name = dependent['table']
                        self.logger.debug(f"Clearing dependent table: {table_name}")
                        cursor.execute(f"DELETE FROM {table_name}")
                    except Exception as e:
                        self.logger.error(f"Error clearing dependent table {dependent['table']}: {str(e)}")
                        # Continue with other tables

                # Now delete positions and employers with explicit ID collection
                try:
                    # Get all position IDs
                    cursor.execute("SELECT id FROM position")
                    position_ids = [row[0] for row in cursor.fetchall()]

                    # Delete each position individually
                    for position_id in position_ids:
                        self.logger.debug(f"Deleting position ID: {position_id}")
                        cursor.execute("DELETE FROM position WHERE id = ?", (position_id,))

                    # Get all employer IDs
                    cursor.execute("SELECT id FROM employer")
                    employer_ids = [row[0] for row in cursor.fetchall()]

                    # Delete each employer individually
                    for employer_id in employer_ids:
                        self.logger.debug(f"Deleting employer ID: {employer_id}")
                        cursor.execute("DELETE FROM employer WHERE id = ?", (employer_id,))

                    # Verify deletion
                    cursor.execute("SELECT COUNT(*) FROM position")
                    position_count = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM employer")
                    employer_count = cursor.fetchone()[0]

                    self.logger.debug(
                        f"After deletion: {position_count} positions and {employer_count} employers remain")

                    if position_count > 0 or employer_count > 0:
                        # If records remain, try more aggressive approach
                        self.logger.debug("Using more aggressive deletion approach")
                        cursor.execute("DELETE FROM position")
                        cursor.execute("DELETE FROM employer")

                    self.logger.debug("Successfully deleted existing positions and employers")
                except Exception as e:
                    self.logger.error(f"Error clearing existing employment data: {str(e)}")
                    # Continue anyway - we'll try to insert new data

                # Now add LinkedIn positions
                positions = profile_data.get('positions', []) or []
                for idx, position in enumerate(positions):
                    try:
                        company_name = position.get('company', {}).get('name', '')
                        title = position.get('title', '')

                        if not company_name or not title:
                            self.logger.warning(f"Skipping position {idx}: Missing company or title")
                            continue

                        # Handle None summary value
                        summary = position.get('summary', '')
                        if summary is None:
                            summary = ''

                        start_month = position.get('startDate', {}).get('month', '1')  # Default to January
                        start_year = position.get('startDate', {}).get('year', '')
                        start_date = f"{start_year}-{start_month}-01" if start_year else None

                        # Set default location
                        location = "Remote"  # LinkedIn often doesn't provide location

                        # Handle end date or current position
                        is_current = position.get('current', False)
                        if is_current:
                            end_date = None
                        else:
                            end_month = position.get('endDate', {}).get('month', '1')  # Default to January
                            end_year = position.get('endDate', {}).get('year', '')
                            end_date = f"{end_year}-{end_month}-01" if end_year else None

                        self.logger.debug(f"Adding position #{idx + 1}: {title} at {company_name}")

                        # Find max IDs to avoid conflicts
                        cursor.execute("SELECT MAX(id) FROM employer")
                        result = cursor.fetchone()
                        max_employer_id = result[0] if result[0] is not None else 0
                        employer_id = max_employer_id + 1

                        cursor.execute("SELECT MAX(id) FROM position")
                        result = cursor.fetchone()
                        max_position_id = result[0] if result[0] is not None else 0
                        position_id = max_position_id + 1

                        # 1. Insert employer
                        cursor.execute(
                            "INSERT INTO employer (id, employer, location, state) VALUES (?, ?, ?, ?)",
                            (employer_id, company_name, location, 1)
                        )

                        # 2. Build dynamic SQL for position insert based on available columns
                        if 'description' in position_columns:
                            # If there's a description column, use it
                            cursor.execute(
                                """INSERT INTO position
                                       (id, position, employer, startdate, enddate, description, state)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                (position_id, title, employer_id, start_date, end_date, summary, 1)
                            )
                        else:
                            # If no description column, skip it
                            cursor.execute(
                                """INSERT INTO position
                                       (id, position, employer, startdate, enddate, state)
                                   VALUES (?, ?, ?, ?, ?, ?)""",
                                (position_id, title, employer_id, start_date, end_date, 1)
                            )

                        self.logger.debug(f"Successfully added employer and position: {company_name} - {title}")
                    except Exception as e:
                        self.logger.error(f"Error adding position {idx}: {str(e)}")
                        # Continue with next position instead of failing completely

                # Purge the query cache
                self.query.purge_cache("positions")

            return {'success': True}
        except Exception as e:
            self.logger.exception("Error importing work experience:")
            return {'success': False, 'error': str(e)}

    def _import_education(self, profile_data):
        """Import education history"""
        self.logger.debug("--- DEBUG: Processing education ---")
        try:
            # Import required modules
            from pylaform.commands.db.connect import transaction_context
            import sqlite3

            # First, use a single transaction to delete all existing records
            try:
                with transaction_context() as conn:
                    cursor = conn.cursor()

                    # First delete all focuses (to maintain foreign key constraints)
                    self.logger.debug("Deleting all existing focus records")
                    cursor.execute("DELETE FROM focus")

                    # Then delete all schools
                    self.logger.debug("Deleting all existing school records")
                    cursor.execute("DELETE FROM school")

                    # The transaction_context will handle the commit
                    self.logger.debug("Successfully deleted all existing education records")
            except Exception as e:
                self.logger.error(f"Error clearing existing education data: {str(e)}")
                # Continue with import even if deletion fails

            # Import each education entry one by one, each in its own transaction
            education_entries = profile_data.get('education', [])
            for idx, edu in enumerate(education_entries):
                try:
                    school_name = edu.get('schoolName', '')
                    degree = edu.get('degree', '')
                    field_of_study = edu.get('fieldOfStudy', '')

                    if not school_name:
                        self.logger.warning(f"Skipping education entry {idx}: No school name provided")
                        continue

                    start_year = edu.get('startDate', {}).get('year', '')
                    start_date = f"{start_year}-01-01" if start_year else None

                    # Handle end date
                    if 'endDate' in edu and edu['endDate']:
                        end_year = edu['endDate'].get('year', '')
                        end_date = f"{end_year}-12-31" if end_year else None
                    else:
                        end_date = None

                    # Set default location if not provided
                    location = "Online"  # LinkedIn often doesn't provide location

                    self.logger.debug(f"Adding education #{idx + 1}: {degree} in {field_of_study} at {school_name}")

                    # Combine degree and field of study for focus name
                    focus_name = degree
                    if field_of_study:
                        if focus_name:
                            focus_name += f" in {field_of_study}"
                        else:
                            focus_name = field_of_study

                    # Try to insert with incremental ID first
                    try:
                        with transaction_context() as conn:
                            cursor = conn.cursor()

                            # Find the maximum ID and increment to avoid conflicts
                            cursor.execute("SELECT MAX(id) FROM school")
                            result = cursor.fetchone()
                            max_school_id = result[0] if result[0] is not None else 0
                            school_id = max_school_id + 1

                            cursor.execute("SELECT MAX(id) FROM focus")
                            result = cursor.fetchone()
                            max_focus_id = result[0] if result[0] is not None else 0
                            focus_id = max_focus_id + 1

                            # 1. Insert school with the new ID
                            cursor.execute(
                                """INSERT INTO school (id, name, location, state)
                                   VALUES (?, ?, ?, ?)""",
                                (school_id, school_name, location, 1)
                            )

                            # 2. Insert focus with the new ID
                            cursor.execute(
                                """INSERT INTO focus (id, name, school, startdate, enddate, state)
                                   VALUES (?, ?, ?, ?, ?, ?)""",
                                (focus_id, focus_name, school_id, start_date, end_date, 1)
                            )

                            # Transaction will be committed by the context manager
                            self.logger.debug(f"Successfully added school and focus: {school_name} - {focus_name}")
                    except Exception as e:
                        self.logger.error(f"Error inserting education {idx}: {str(e)}")
                except Exception as e:
                    self.logger.error(f"Error processing education entry {idx}: {str(e)}")
                    # Continue with next education entry instead of failing completely

            # Purge the query cache to ensure fresh data is loaded
            self.query.purge_cache("education")

            return {'success': True}
        except Exception as e:
            self.logger.exception("Error importing education:")
            return {'success': False, 'error': str(e)}

    def _import_skills(self, profile_data):
        """Import skills"""
        self.logger.debug("--- DEBUG: Processing skills ---")
        try:
            # Use transaction context for all database operations
            from pylaform.commands.db.connect import transaction_context

            # First, get the table schema to check available columns
            columns = []
            required_columns = []
            try:
                with transaction_context(read_only=True) as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA table_info(skill)")
                    schema_info = cursor.fetchall()
                    columns = [row[1] for row in schema_info]
                    self.logger.debug(f"Skill table columns: {columns}")

                    # Check for required columns (NOT NULL)
                    required_columns = [row[1] for row in schema_info if
                                        row[3] == 1]  # row[3] is the "notnull" attribute
                    self.logger.debug(f"Required skill columns (NOT NULL): {required_columns}")
            except Exception as e:
                self.logger.error(f"Error getting skill table schema: {str(e)}")
                # Try to continue with default assumptions
                columns = ['id', 'shortdesc', 'longdesc', 'state', 'categoryorder', 'skillorder', 'category',
                           'subcategory', 'position', 'employer']
                required_columns = ['id', 'shortdesc', 'state', 'position', 'employer', 'subcategory']

            # Before processing skills, let's get the necessary references
            default_employer_id = None
            default_position_id = None

            # First, check if we need employer and position references
            need_employer = 'employer' in required_columns
            need_position = 'position' in required_columns

            if need_employer or need_position:
                try:
                    with transaction_context(read_only=True) as conn:
                        cursor = conn.cursor()

                        # Get default employer if needed
                        if need_employer:
                            cursor.execute("SELECT id FROM employer ORDER BY id LIMIT 1")
                            result = cursor.fetchone()
                            if result:
                                default_employer_id = result[0]
                                self.logger.debug(f"Found existing employer ID for skills: {default_employer_id}")

                        # Get default position if needed
                        if need_position:
                            cursor.execute("SELECT id FROM position ORDER BY id LIMIT 1")
                            result = cursor.fetchone()
                            if result:
                                default_position_id = result[0]
                                self.logger.debug(f"Found existing position ID for skills: {default_position_id}")
                except Exception as e:
                    self.logger.error(f"Error finding default references: {str(e)}")

                # Create default references if not found but needed
                with transaction_context() as conn:
                    cursor = conn.cursor()

                    # Create default employer if needed but not found
                    if need_employer and default_employer_id is None:
                        try:
                            # Find the next available employer ID
                            cursor.execute("SELECT MAX(id) FROM employer")
                            result = cursor.fetchone()
                            new_id = 1 if result[0] is None else result[0] + 1

                            # Insert a default employer for skills
                            cursor.execute(
                                "INSERT INTO employer (id, employer, location, state) VALUES (?, ?, ?, ?)",
                                (new_id, "General Skills", "Remote", 1)
                            )
                            default_employer_id = new_id
                            self.logger.debug(f"Created default employer for skills with ID {default_employer_id}")
                        except Exception as e:
                            self.logger.error(f"Error creating default employer: {str(e)}")
                            return {'success': False, 'error': "Unable to create default employer for skills"}

                    # Create default position if needed but not found
                    if need_position and default_position_id is None:
                        try:
                            # Find the next available position ID
                            cursor.execute("SELECT MAX(id) FROM position")
                            result = cursor.fetchone()
                            new_id = 1 if result[0] is None else result[0] + 1

                            # Insert a default position (using our employer if we created one)
                            position_employer_id = default_employer_id if default_employer_id else 1
                            cursor.execute(
                                """INSERT INTO position
                                       (id, position, employer, state)
                                   VALUES (?, ?, ?, ?)""",
                                (new_id, "Core Skills", position_employer_id, 1)
                            )
                            default_position_id = new_id
                            self.logger.debug(f"Created default position for skills with ID {default_position_id}")
                        except Exception as e:
                            self.logger.error(f"Error creating default position: {str(e)}")
                            return {'success': False, 'error': "Unable to create default position for skills"}

            # Now proceed with skill import
            with transaction_context() as conn:
                cursor = conn.cursor()

                # Identify and delete dependent tables first
                dependent_tables = []
                try:
                    # Get all tables in the database
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    all_tables = [row[0] for row in cursor.fetchall()]

                    # For each table, check if it references skill
                    for table_name in all_tables:
                        if table_name == 'skill':
                            continue  # Skip our main table

                        # Check for foreign keys to skill
                        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                        for fk in cursor.fetchall():
                            referenced_table = fk[2]  # Table referenced by foreign key
                            if referenced_table == 'skill':
                                dependent_tables.append(table_name)
                                break

                    self.logger.debug(f"Found tables dependent on skill: {dependent_tables}")

                    # Clear dependent tables first
                    for table_name in dependent_tables:
                        self.logger.debug(f"Clearing dependent table: {table_name}")
                        cursor.execute(f"DELETE FROM {table_name}")
                except Exception as e:
                    self.logger.error(f"Error handling dependent tables: {str(e)}")

                # Get existing skills records and delete them
                try:
                    self.logger.debug("Querying existing skills")
                    cursor.execute("SELECT id FROM skill")
                    skill_ids = [row[0] for row in cursor.fetchall()]

                    # Delete existing records
                    for skill_id in skill_ids:
                        self.logger.debug(f"Deleting skill ID: {skill_id}")
                        cursor.execute("DELETE FROM skill WHERE id = ?", (skill_id,))

                    # Verify deletion
                    cursor.execute("SELECT COUNT(*) FROM skill")
                    count = cursor.fetchone()[0]
                    self.logger.debug(f"Skills remaining after deletion: {count}")

                    # Try more aggressive deletion if records remain
                    if count > 0:
                        self.logger.debug("Attempting full table deletion")
                        cursor.execute("DELETE FROM skill")
                except Exception as e:
                    self.logger.error(f"Error clearing existing skills data: {str(e)}")
                    # Try to continue

                # Group the skills by category for better organization
                skill_categories = {}
                skills = profile_data.get('skills', []) or []

                # Parse LinkedIn skills and organize them
                for skill in skills:
                    # Extract skill name
                    skill_name = ''
                    if isinstance(skill, str):
                        skill_name = skill
                    elif isinstance(skill, dict):
                        skill_name = skill.get('name', '')

                    if not skill_name:
                        continue

                    # Attempt to categorize the skill
                    category = self._categorize_skill(skill_name)
                    if category not in skill_categories:
                        skill_categories[category] = []

                    skill_categories[category].append(skill_name)

                # Now insert all the skills with proper categorization
                skill_id = 1
                for category, category_skills in skill_categories.items():
                    # Each category gets subcategories
                    subcategories = self._get_subcategories(category)

                    for subcategory in subcategories:
                        subcategory_skills = category_skills  # For now, assign all skills to first subcategory

                        for idx, skill_name in enumerate(subcategory_skills):
                            try:
                                self.logger.debug(
                                    f"Adding skill: {skill_name} (Category: {category}, Subcategory: {subcategory})")

                                # Prepare skill data
                                skill_data = {
                                    'id': skill_id,
                                    'shortdesc': skill_name,
                                    'longdesc': '',
                                    'state': 1,
                                    'categoryorder': list(skill_categories.keys()).index(category) + 1,
                                    'skillorder': idx + 1,
                                    'category': category,
                                    'subcategory': subcategory
                                }

                                # Add employer if required
                                if 'employer' in required_columns:
                                    skill_data['employer'] = default_employer_id

                                # Add position if required
                                if 'position' in required_columns:
                                    skill_data['position'] = default_position_id

                                # Add rating if available
                                if 'rating' in columns:
                                    skill_data['rating'] = 4  # Default high rating

                                # Create dynamic SQL based on the columns we have
                                columns_str = ', '.join(skill_data.keys())
                                placeholders = ', '.join(['?'] * len(skill_data))

                                sql = f"INSERT INTO skill ({columns_str}) VALUES ({placeholders})"
                                cursor.execute(sql, tuple(skill_data.values()))

                                self.logger.debug(f"Successfully added skill: {skill_name}")
                                skill_id += 1
                            except Exception as e:
                                self.logger.error(f"Error adding skill {skill_name}: {str(e)}")
                                # Continue with next skill

                        # Only use the first subcategory for now
                        break  # Remove this if you want to spread skills across subcategories

                # Purge the query cache to ensure fresh data is loaded
                self.query.purge_cache("skills")

            return {'success': True}
        except Exception as e:
            self.logger.exception("Error importing skills:")
            return {'success': False, 'error': str(e)}

    def _categorize_skill(self, skill_name):
        """Categorize a skill based on its name"""
        skill_name = skill_name.lower()

        # Define categories and keywords
        categories = {
            'Programming Languages': ['python', 'java', 'javascript', 'c++', 'c#', 'php', 'ruby', 'golang', 'swift',
                                      'kotlin'],
            'Web Development': ['html', 'css', 'react', 'angular', 'vue', 'node', 'express', 'django', 'flask',
                                'frontend', 'backend'],
            'Data & Analytics': ['sql', 'database', 'data science', 'machine learning', 'statistics', 'analytics',
                                 'tableau', 'power bi', 'excel'],
            'Cloud & DevOps': ['aws', 'azure', 'gcp', 'cloud', 'devops', 'jenkins', 'docker', 'kubernetes', 'terraform',
                               'ci/cd'],
            'Project Management': ['agile', 'scrum', 'kanban', 'project management', 'jira', 'leadership',
                                   'team management'],
            'Design': ['ui', 'ux', 'graphic design', 'photoshop', 'illustrator', 'figma', 'sketch', 'indesign'],
            'Marketing': ['seo', 'sem', 'content marketing', 'social media', 'analytics', 'email marketing',
                          'digital marketing'],
            'Communication': ['writing', 'public speaking', 'presentation', 'negotiation', 'teamwork', 'collaboration'],
            'Soft Skills': ['leadership', 'problem-solving', 'critical thinking', 'time management', 'creativity',
                            'adaptability']
        }

        # Try to find a matching category
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in skill_name:
                    return category

        # Default category if no match is found
        return 'Technical Skills'

    def _get_subcategories(self, category):
        """Return subcategories for a given skill category"""
        subcategories = {
            'Programming Languages': ['Backend Development', 'Frontend Development', 'Mobile Development'],
            'Web Development': ['Frontend', 'Backend', 'Full Stack'],
            'Data & Analytics': ['Data Engineering', 'Data Science', 'Business Intelligence'],
            'Cloud & DevOps': ['Cloud Infrastructure', 'Automation', 'Monitoring'],
            'Project Management': ['Agile Methodologies', 'Resource Management', 'Risk Management'],
            'Design': ['UI Design', 'UX Design', 'Graphic Design'],
            'Marketing': ['Digital Marketing', 'Content Marketing', 'SEO/SEM'],
            'Communication': ['Written Communication', 'Verbal Communication', 'Presentation Skills'],
            'Soft Skills': ['Leadership', 'Problem Solving', 'Teamwork'],
            'Technical Skills': ['Core Technical Skills', 'Tools & Platforms', 'Methodologies']
        }

        # Return the subcategories for the given category, or a default if not found
        return subcategories.get(category, ['General'])
