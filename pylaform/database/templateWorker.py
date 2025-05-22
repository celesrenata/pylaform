import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from boto3.dynamodb.conditions import Key, Attr  # Add this import

# Import DynamoDB modules
from pylaform.database.dynamo_query import DynamoQueries
from pylaform.database.dynamo_update import DynamoUpdates
from pylaform.database.dynamo_delete import DynamoDeletes
from pylaform.database.dynamo_insert import DynamoInserts
from pylaform.database.connect import db
from tenacity import retry, stop_after_delay, wait_exponential, RetryError, stop_after_attempt

# Configure logger
logger = logging.getLogger(__name__)


class Worker:
    """
    Worker class to handle all template-related database operations.
    Provides a centralized interface for accessing and modifying resume data.

    This class supports multi-user operations by filtering data based on user_id.
    """

    def __init__(self, user_id=None):
        """
        Initialize the Worker with optional user_id for multi-user support.

        :param str user_id: Optional user ID to filter operations
        """
        self.user_id = user_id
        self.table = db()
        self.query = DynamoQueries()
        self.insert = DynamoInserts()
        self.update = DynamoUpdates()
        logger.debug(f"Worker initialized with user_id: {self.user_id}")

    # ==================== IDENTIFICATION METHODS ====================

    @retry(
        stop=stop_after_attempt(3),  # Try 3 times
        wait=wait_exponential(multiplier=1, min=1, max=5),  # Wait between 1-5 seconds between retries
        reraise=True
    )
    def get_identification(self, resume_id=None):
        """
        Get all identification items for a user or specific resume.

        :param str resume_id: Optional resume ID to get identification for
        :return: List of identification items
        """
        try:
            if not self.user_id and not resume_id:
                logger.warning("No user_id or resume_id available, cannot get identification")
                return []

            # Determine the correct PK based on whether resume_id is provided
            pk = f"RESUME#{resume_id}" if resume_id else f"USER#{self.user_id}"

            logger.info(f"Getting identification with PK: {pk}")

            # Query for all identification items
            response = self.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                ExpressionAttributeValues={
                    ":pk": pk,
                    ":sk_prefix": "IDENTIFICATION#"
                }
            )

            items = response.get('Items', [])
            logger.info(f"Found {len(items)} identification items for PK: {pk}")

            return items
        except Exception as e:
            logger.error(f"Error getting identification: {str(e)}")
            return []

    def create_default_identification(self, resume_id=None):
        """
        Create default identification items for a user or specific resume.

        :param str resume_id: Optional resume ID to create defaults for
        :return: True if successful, False otherwise
        """
        try:
            if not self.user_id and not resume_id:
                logger.warning("No user_id or resume_id available, cannot create default identification")
                return False

            # Determine the correct PK based on whether resume_id is provided
            pk = f"USER#{self.user_id}"
            if resume_id:
                pk = f"RESUME#{resume_id}"

            logger.info(f"Creating default identification with PK: {pk}")

            # Default identification fields
            defaults = [
                {"attr": "name", "contacttype": "name", "label": "Full Name", "value": "", "state": True},
                {"attr": "email", "contacttype": "email", "label": "Email", "value": "", "state": True},
                {"attr": "phone", "contacttype": "phone", "label": "Phone", "value": "", "state": True},
                {"attr": "location", "contacttype": "location", "label": "Location", "value": "", "state": True},
                {"attr": "www", "contacttype": "www", "label": "Website", "value": "", "state": False},
                {"attr": "linkedin", "contacttype": "linkedin", "label": "LinkedIn", "value": "", "state": False},
                {"attr": "github", "contacttype": "github", "label": "GitHub", "value": "", "state": False}
            ]

            # Create each default item
            for item in defaults:
                item_id = str(uuid.uuid4())
                self.table.put_item(
                    Item={
                        "PK": pk,
                        "SK": f"IDENTIFICATION#{item_id}",
                        "id": item_id,
                        "attr": item.get("attr", ""),
                        "contacttype": item.get("contacttype", ""),
                        "label": item.get("label", ""),
                        "value": item.get("value", ""),
                        "state": item.get("state", False),
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                )

            return True
        except Exception as e:
            logger.error(f"Error creating default identification: {str(e)}")
            return False

    def identification(self, form_data):
        """
        Process form data for identification information.

        :param form_data: The form data from the request
        :return: True if successful, False otherwise
        """
        try:
            logger.debug(f"Processing identification form data: {form_data}")

            # Group form fields by their ID prefix
            grouped_data = {}
            for key, value in form_data.items():
                if '_' in key:
                    field_id, field_type = key.split('_', 1)
                    if field_id not in grouped_data:
                        grouped_data[field_id] = {}
                    grouped_data[field_id][field_type] = value

            # Process each contact field
            success = True
            for field_id, field_data in grouped_data.items():
                # Skip fields that don't have all required attributes
                if not all(k in field_data for k in ['attr', 'value']):
                    continue

                # Determine if field is enabled
                enabled = field_data.get('enabled') == 'on'

                # Get the SK if available
                sk = field_data.get('sk', '')

                # Extract the item_id from SK if present
                item_id = ''
                if sk and sk.startswith('IDENTIFICATION#'):
                    item_id = sk.split('#')[1]

                # Update the field
                field_success = self.update_identification(
                    item_id=item_id if item_id else field_data.get('attr'),
                    attr=field_data.get('attr'),
                    value=field_data.get('value'),
                    contacttype=field_data.get('contacttype'),
                    label=field_data.get('label'),
                    state=1 if enabled else 0
                )

                if not field_success:
                    success = False

            return success
        except Exception as e:
            logger.error(f"Error processing identification form: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def process_information_form(self, form_data, resume_id=None):
        """
        Process form data for information/identification fields.

        :param form_data: Form data from the information page
        :param str resume_id: Optional resume ID to associate with
        :return bool: True if successful, False otherwise
        """
        try:
            if not self.user_id and not resume_id:
                logger.warning("No user_id or resume_id available, cannot process information form")
                return False

            # Get the resume_id from form data if not provided
            if not resume_id and 'active_resume_id' in form_data:
                resume_id = form_data.get('active_resume_id')
                logger.info(f"Using resume_id from form data: {resume_id}")

            logger.info(f"Processing information form data for user {self.user_id}, resume {resume_id}")
            logger.debug(f"Form data received: {dict(form_data)}")  # Log the entire form data

            # First, check if we need to create default identification entries
            existing_items = self.get_identification(resume_id=resume_id)
            if not existing_items:
                logger.info("No existing identification entries found, creating defaults")
                self.create_default_identification(resume_id=resume_id)
                # Refresh the list after creation
                existing_items = self.get_identification(resume_id=resume_id)

            # Log what we have in the database
            logger.debug(f"Existing identification entries: {[item.get('attr', 'unknown') for item in existing_items]}")

            # Create a map of existing attributes for faster lookup
            existing_attrs = {item.get('attr', '').lower(): item for item in existing_items if item.get('attr')}

            updates_made = False
            update_count = 0
            error_count = 0

            # Group form fields by their ID prefix to handle structured form data
            grouped_data = {}
            for key, value in form_data.items():
                if '_' in key:
                    # Extract field_id and field_type from the key
                    # Format is typically: field_index_fieldtype (e.g., name_1_value)
                    parts = key.rsplit('_', 1)
                    if len(parts) == 2:
                        field_id = parts[0]  # e.g., "name_1"
                        field_type = parts[1]  # e.g., "value"

                        if field_id not in grouped_data:
                            grouped_data[field_id] = {}
                        grouped_data[field_id][field_type] = value

            # Process each grouped field
            for field_id, field_data in grouped_data.items():
                # Skip fields that don't have all required attributes
                if not all(k in field_data for k in ['attr', 'value']):
                    continue

                # Determine if field is enabled
                enabled = field_data.get('enabled') == 'on'

                # Clean up the SK value if needed
                sk = field_data.get('sk', '')
                item_id = ''
                if sk and sk.startswith('IDENTIFICATION#'):
                    item_id = sk.replace('IDENTIFICATION#', '')

                attr = field_data.get('attr', '')
                value = field_data.get('value', '')
                contacttype = field_data.get('contacttype', attr)
                label = field_data.get('label', attr.capitalize())

                logger.debug(f"Processing field: id={item_id}, attr={attr}, value={value}, enabled={enabled}")

                # Update the field
                success = self.update_identification(
                    item_id=item_id,
                    resume_id=resume_id,
                    attr=attr,
                    value=value,
                    contacttype=contacttype,
                    label=label,
                    state=1 if enabled else 0
                )

                if success:
                    update_count += 1
                    updates_made = True
                else:
                    error_count += 1

            # Process any remaining direct fields that weren't in the grouped data
            for key, value in form_data.items():
                # Skip empty values, special fields, and already processed fields
                if not value or key == 'active_resume_id' or '_' in key:
                    continue

                logger.debug(f"Processing direct field: {key}={value}")

                # Try to determine the attribute type from the field name
                attr_type = None
                label = None

                # Direct attribute names (e.g., 'name', 'email')
                if key in ['name', 'email', 'phone', 'location', 'www', 'github', 'linkedin', 'website']:
                    attr_type = key
                    # Use proper capitalized labels
                    label_map = {
                        'name': 'Name',
                        'email': 'Email',
                        'phone': 'Phone',
                        'location': 'Location',
                        'www': 'Website',
                        'website': 'Website',
                        'github': 'GitHub',
                        'linkedin': 'LinkedIn'
                    }
                    label = label_map.get(key, key.capitalize())

                    # Check if this attribute already exists
                    attr_lower = attr_type.lower()
                    if attr_lower in existing_attrs:
                        existing_item = existing_attrs[attr_lower]
                        item_id = existing_item.get('id') or existing_item.get('SK', '').replace('IDENTIFICATION#', '')

                        # Update the existing item
                        success = self.update_identification(
                            item_id=item_id,
                            resume_id=resume_id,
                            attr=attr_type,
                            value=value,
                            contacttype=attr_type,
                            label=label,
                            state=1  # Default to enabled for direct fields
                        )
                    else:
                        # Create a new item
                        success = self.update_identification(
                            item_id='',  # Empty ID will create a new item
                            resume_id=resume_id,
                            attr=attr_type,
                            value=value,
                            contacttype=attr_type,
                            label=label,
                            state=1  # Default to enabled for direct fields
                        )

                    if success:
                        update_count += 1
                        updates_made = True
                    else:
                        error_count += 1

            # Clear the cache to ensure fresh data on next page load
            if updates_made:
                self.query.purge_cache("identification")

            logger.info(f"Information form processing complete: {update_count} updates, {error_count} errors")
            return updates_made
        except Exception as e:
            logger.error(f"Error processing information form: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def find_identification_by_attr(self, attr_type: str) -> Optional[Dict[str, Any]]:
        """
        Find an identification entry by attribute type.

        :param str attr_type: The attribute type to find (e.g., 'email', 'name')
        :return: The identification entry or None if not found
        """
        try:
            if not self.user_id:
                logger.warning("No user_id available, cannot find identification")
                return None

            # Get all identification entries for this user
            items = self.get_identification()

            logger.debug(f"Looking for identification with attr={attr_type} among {len(items)} items")

            # Normalize the search attribute
            search_attr = attr_type.lower() if attr_type else ""
            if search_attr.startswith("identification#"):
                search_attr = search_attr.split("#", 1)[1]
                if "-" in search_attr:
                    search_attr = search_attr.split("-", 1)[0]

            # Special case handling for common aliases
            if search_attr == "website":
                search_attr = "www"
            elif search_attr == "web":
                search_attr = "www"

            # Find the entry with matching attr
            for item in items:
                item_attr = item.get('attr', '').lower() if item.get('attr') else ''
                contacttype = item.get('contacttype', '').lower() if item.get('contacttype') else ''

                # Debug the actual attribute values we're comparing
                logger.debug(f"Comparing item attr '{item_attr}' with search attr '{search_attr}'")

                # Try different matching strategies
                if item_attr == search_attr:
                    logger.debug(f"Found identification entry for attr={attr_type}, id={item.get('id')}")
                    return item

                # Try matching by contacttype
                if contacttype == search_attr:
                    logger.debug(f"Found identification entry by contacttype={contacttype} for attr={attr_type}")
                    return item

                # Try with SK format
                sk = item.get('SK', '').lower() if item.get('SK') else ''
                if sk and (sk == f"identification#{search_attr}" or
                           sk.startswith(f"identification#{search_attr}-")):
                    logger.debug(f"Found identification entry by SK={sk} for attr={attr_type}")
                    return item

            # If we get here, we didn't find a match
            logger.warning(f"No identification entry found for attr={attr_type}, user_id={self.user_id}")

            # Let's log what we actually have in the database for debugging
            debug_items = [{
                'attr': item.get('attr', 'unknown'),
                'contacttype': item.get('contacttype', 'unknown'),
                'id': item.get('id', 'unknown')
            } for item in items]
            logger.debug(f"Available identification items: {debug_items}")

            return None
        except Exception as e:
            logger.error(f"Error finding identification by attr {attr_type}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    @retry(
        stop=stop_after_attempt(3),  # Try 3 times
        wait=wait_exponential(multiplier=1, min=1, max=5),  # Wait between 1-5 seconds between retries
        reraise=True
    )
    def update_identification(self, item_id: str, resume_id=None, **kwargs) -> bool:
        """
        Update an identification item.

        :param str item_id: The ID of the item to update
        :param str resume_id: Optional resume ID this item belongs to
        :param kwargs: The fields to update
        :return bool: True if successful, False otherwise
        """
        try:
            if not self.user_id and not resume_id:
                logger.warning("No user_id or resume_id available, cannot update identification")
                return False

            # Determine the correct PK based on whether resume_id is provided
            pk = f"RESUME#{resume_id}" if resume_id else f"USER#{self.user_id}"

            # If item_id contains the full SK format, extract just the ID part
            if item_id and item_id.startswith("IDENTIFICATION#"):
                item_id = item_id.split("#")[1]

            # Build update expression and attribute values
            update_expr = "SET #updated_at = :updated_at"
            expr_attr_values = {
                ":updated_at": datetime.now().isoformat()
            }
            expr_attr_names = {
                "#updated_at": "updated_at"
            }

            # Add each field to update
            for i, (key, value) in enumerate(kwargs.items()):
                # Always use expression attribute names for all fields to be safe
                attr_name = f"#{key}"
                expr_attr_names[attr_name] = key
                update_expr += f", {attr_name} = :val{i}"
                expr_attr_values[f":val{i}"] = value

            logger.debug(f"Updating identification item {item_id} with PK={pk}, data: {kwargs}")
            logger.debug(f"Update expression: {update_expr}")
            logger.debug(f"Expression attribute names: {expr_attr_names}")
            logger.debug(f"Expression attribute values: {expr_attr_values}")

            # Update the item
            self.table.update_item(
                Key={
                    "PK": pk,
                    "SK": f"IDENTIFICATION#{item_id}"
                },
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_attr_values,
                ExpressionAttributeNames=expr_attr_names
            )

            return True
        except Exception as e:
            logger.error(f"Error updating identification: {str(e)}")
            return False

    def update_identification_by_attr(self, attr_type: str, **kwargs) -> bool:
        """
        Update an identification entry by attribute type instead of ID.

        :param str attr_type: The attribute type to update (e.g., 'email', 'name')
        :param kwargs: Fields to update
        :return bool: True if successful, False otherwise
        """
        try:
            if not self.user_id:
                logger.warning("No user_id available, cannot update identification")
                return False

            # Find the identification entry by attribute type
            item = self.find_identification_by_attr(attr_type)
            if not item:
                logger.warning(f"No identification entry found for attr={attr_type}")
                return False

            # Get the ID of the found item
            item_id = item.get('id') or item.get('SK', '').replace('IDENTIFICATION#', '')
            if not item_id:
                logger.warning(f"Found identification entry for attr={attr_type} has no ID")
                return False

            # Update the item using the existing update_identification method
            logger.debug(f"Updating identification {item_id} for attr={attr_type} with data: {kwargs}")
            return self.update_identification(item_id, **kwargs)
        except Exception as e:
            logger.error(f"Error updating identification by attr {attr_type}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def get_identification_safely(self, resume_id=None):
        """
        Get identification entries with fallback mechanisms.

        This method tries multiple approaches to get identification data,
        including retries and fallbacks to default values if needed.

        :param str resume_id: Optional resume ID to get identification for
        :return: List of identification items, never empty
        """
        try:
            # First try: Get identification normally
            items = self.get_identification(resume_id=resume_id)

            # If we got items, return them
            if items:
                return items

            # Second try: Create defaults and try again
            logger.info(f"No identification found, creating defaults for user_id={self.user_id}, resume_id={resume_id}")
            self.create_default_identification(resume_id=resume_id)
            items = self.get_identification(resume_id=resume_id)

            # If we got items now, return them
            if items:
                return items

            # Last resort: Return hardcoded defaults
            logger.warning(f"Failed to get or create identification data, returning hardcoded defaults")
            return [
                {"attr": "name", "contacttype": "name", "label": "Full Name", "value": "", "state": True},
                {"attr": "email", "contacttype": "email", "label": "Email", "value": "", "state": True},
                {"attr": "phone", "contacttype": "phone", "label": "Phone", "value": "", "state": True},
                {"attr": "location", "contacttype": "location", "label": "Location", "value": "", "state": True}
            ]
        except Exception as e:
            logger.error(f"Error in get_identification_safely: {str(e)}")
            # Return minimal defaults in case of error
            return [
                {"attr": "name", "contacttype": "name", "label": "Full Name", "value": "", "state": True},
                {"attr": "email", "contacttype": "email", "label": "Email", "value": "", "state": True}
            ]

    # ==================== SUMMARY METHODS ====================

    def get_all_summaries(self, resume_id=None):
        """
        Get all summary entries for the current user.

        :param str resume_id: Optional resume ID to filter by
        :return: List of summary entries
        """
        try:
            if not self.user_id and not resume_id:
                logger.warning("No user_id or resume_id available, cannot get summaries")
                return []

            # Clear cache before querying to ensure fresh data
            cache_key = f"summary_{resume_id}" if resume_id else "summary"
            if hasattr(self.query, 'purge_cache'):
                logger.debug(f"Purging cache for {cache_key} before querying")
                self.query.purge_cache(cache_key)

            if resume_id:
                # Query for resume-specific summaries
                pk = f"RESUME#{resume_id}"
                logger.debug(f"Querying summaries for resume {resume_id} with PK={pk}")

                response = self.table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('SUMMARY#'),
                    FilterExpression=Attr('state').eq(True)  # Only return active entries
                )

                summaries = response.get('Items', [])
                logger.debug(f"Found {len(summaries)} active summaries for resume {resume_id}")

                # Format the summaries
                formatted_summaries = []
                for summary in summaries:
                    # Extract the ID from the SK
                    summary_id = summary['SK'].split('#')[1]
                    formatted_summary = {
                        'id': summary_id,
                        'shortdesc': summary.get('shortdesc', ''),
                        'longdesc': summary.get('longdesc', ''),
                        'summaryorder': summary.get('summaryorder', 99),
                        'state': summary.get('state', True)
                    }
                    formatted_summaries.append(formatted_summary)

                return formatted_summaries
            else:
                # Use the existing method for user-specific summaries
                return self.query.get_all_summaries()
        except Exception as e:
            logger.error(f"Error getting summaries: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def add_summary(self, shortdesc: str, longdesc: str, summaryorder: int = 99, resume_id=None) -> str:
        """
        Add a new summary entry.

        :param str shortdesc: Short description
        :param str longdesc: Long description
        :param int summaryorder: Order of the summary (default: 99)
        :param str resume_id: Optional resume ID this summary belongs to
        :return str: ID of new entry, or None on failure
        """
        try:
            # Generate a unique ID for the new summary
            import uuid
            summary_id = str(uuid.uuid4())

            # If resume_id is provided, use it to create a resume-specific summary
            if resume_id:
                # Create the item with the resume PK
                pk = f"RESUME#{resume_id}"
                sk = f"SUMMARY#{summary_id}"

                # Current timestamp
                now = datetime.now().isoformat()

                # Create the item
                self.table.put_item(
                    Item={
                        "PK": pk,
                        "SK": sk,
                        "id": summary_id,
                        "shortdesc": shortdesc,
                        "longdesc": longdesc,
                        "summaryorder": summaryorder,
                        "state": True,
                        "created_at": now,
                        "updated_at": now,
                        "entity_type": "summary",
                        "resume_id": resume_id
                    }
                )

                # Clear cache for this resume's summaries
                if hasattr(self.query, 'purge_cache'):
                    self.query.purge_cache(f"summary_{resume_id}")

                return summary_id
            else:
                # For backward compatibility, use the old method for user-level summaries
                data = {
                    "shortdesc": shortdesc,
                    "longdesc": longdesc,
                    "summaryorder": summaryorder,
                    "state": True
                }

                # Add user_id if available
                if self.user_id:
                    data["user_id"] = self.user_id

                result = self.insert.multi_column("summary", **data)

                # Clear the cache after adding
                if hasattr(self.query, 'purge_cache'):
                    self.query.purge_cache("summary")

                return result
        except Exception as e:
            logger.error(f"Error adding summary: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def update_summary(self, summary_id: str, resume_id=None, **kwargs) -> bool:
        """
        Update an existing summary.

        :param str summary_id: ID of the summary to update
        :param str resume_id: Optional resume ID to associate with
        :param kwargs: Fields to update
        :return: True if successful, False otherwise
        """
        try:
            if not self.user_id and not resume_id:
                logger.warning("No user_id or resume_id available, cannot update summary")
                return False

            # Determine the correct PK based on whether resume_id is provided
            pk = f"RESUME#{resume_id}" if resume_id else f"USER#{self.user_id}"

            # Remove any SK prefix if present
            if summary_id.startswith("SUMMARY#"):
                summary_id = summary_id[8:]

            # Build update expression
            update_expression = "SET updated_at = :updated_at"
            expression_values = {
                ":updated_at": datetime.now().isoformat()
            }

            # Add each field to the update expression
            for key, value in kwargs.items():
                update_expression += f", {key} = :{key}"
                expression_values[f":{key}"] = value

            # Update the item
            self.table.update_item(
                Key={
                    "PK": pk,
                    "SK": f"SUMMARY#{summary_id}"
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )

            # Clear cache
            self.query.purge_cache("summary")

            return True
        except Exception as e:
            logger.error(f"Error updating summary: {str(e)}")
            return False

    def get_summary(self, resume_id=None) -> List[Dict[str, Any]]:
        """
        Get all summaries for the current user and resume, sorted by summaryorder.

        :param str resume_id: Optional resume ID to filter by
        :return: List of summary dictionaries sorted by summaryorder
        """
        try:
            # Get all summaries
            summaries = self.get_all_summaries(resume_id=resume_id)

            # Sort by summaryorder
            summaries.sort(key=lambda x: x.get('summaryorder', 99))

            # Ensure all summaries have the required fields
            for summary in summaries:
                # Set default values for any missing fields
                summary.setdefault('shortdesc', '')
                summary.setdefault('longdesc', '')
                summary.setdefault('state', True)
                summary.setdefault('summaryorder', 99)

                # Ensure ID is present
                if 'id' not in summary and 'SK' in summary:
                    # Extract ID from SK if needed
                    sk = summary.get('SK', '')
                    if sk.startswith('SUMMARY#'):
                        summary['id'] = sk[8:]  # Remove 'SUMMARY#' prefix

            return summaries
        except Exception as e:
            logger.error(f"Error getting summaries: {str(e)}")
            return []

    # ==================== EDUCATION METHODS ====================

    def get_all_education(self, resume_id=None, active_only: bool = True) -> List[Dict[str, Any]]:
        try:
            logger.debug(
                f"Getting education for resume_id: {resume_id}, active_only: {active_only}, user_id: {self.user_id}")

            schools = []
            if resume_id:
                # Query for resume-specific education entries
                pk = f"RESUME#{resume_id}"
                response = self.table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('SCHOOL#'),
                    FilterExpression=Attr('state').eq(True) if active_only else Attr('state').exists()
                )
                schools = response.get('Items', [])
                logger.debug(f"Found {len(schools)} schools for resume {resume_id}")
            elif self.user_id:
                schools = self.query.get_user_items("school", self.user_id, active_only)
                logger.debug(f"Found {len(schools)} schools for user {self.user_id}")
            else:
                schools = self.query.get_all("school", active_only)
                logger.debug(f"Found {len(schools)} schools (global)")

            logger.debug(f"Schools before processing: {schools}")

            # Process schools to ensure consistent structure
            processed_schools = []
            for school in schools:
                # Extract school_id based on whether it's a resume-specific entry or not
                school_id = school.get('id')
                if not school_id and 'SK' in school:
                    sk = school.get('SK', '')
                    if sk.startswith('SCHOOL#'):
                        school_id = sk.split('#')[1]
                        school['id'] = school_id

                # Ensure all required fields exist
                school.setdefault('name', '')
                school.setdefault('degree', '')
                school.setdefault('location', '')
                school.setdefault('graddate', '')
                school.setdefault('state', True)

                # Get focus areas and achievements for this school
                if school_id:
                    logger.debug(f"Processing school: {school_id}")
                    if resume_id:
                        focus_areas = self.get_focus_areas_for_resume(resume_id, school_id, active_only)
                        achievements = self.get_achievements_for_resume(resume_id, school_id, active_only)
                    elif self.user_id:
                        focus_areas = self.query.get_user_items_by_parent("focus", self.user_id, "school_id", school_id,
                                                                          active_only)
                        achievements = self.query.get_user_items_by_parent("achievement", self.user_id, "school_id",
                                                                           school_id,
                                                                           active_only)
                    else:
                        focus_areas = self.query.get_items_by_parent("focus", "school_id", school_id, active_only)
                        achievements = self.query.get_items_by_parent("achievement", "school_id", school_id,
                                                                      active_only)

                    # Process focus areas to ensure consistent structure
                    processed_focus_areas = []
                    for focus in focus_areas:
                        focus_id = focus.get('id')
                        if not focus_id and 'SK' in focus:
                            sk = focus.get('SK', '')
                            if '#FOCUS#' in sk:
                                focus_id = sk.split('#FOCUS#')[1]
                                focus['id'] = focus_id

                        # Ensure all required fields exist
                        focus.setdefault('name', '')
                        focus.setdefault('description', '')
                        focus.setdefault('state', True)
                        processed_focus_areas.append(focus)

                    # Process achievements to ensure consistent structure
                    processed_achievements = []
                    for achievement in achievements:
                        achievement_id = achievement.get('id')
                        if not achievement_id and 'SK' in achievement:
                            sk = achievement.get('SK', '')
                            if '#ACHIEVEMENT#' in sk:
                                achievement_id = sk.split('#ACHIEVEMENT#')[1]
                                achievement['id'] = achievement_id

                        # Ensure all required fields exist
                        achievement.setdefault('description', '')
                        achievement.setdefault('state', True)
                        processed_achievements.append(achievement)

                    school['focus_areas'] = processed_focus_areas
                    school['achievements'] = processed_achievements
                    logger.debug(
                        f"Found {len(processed_focus_areas)} focus areas and {len(processed_achievements)} achievements for school {school_id}")

                processed_schools.append(school)

            # Sort schools by graduation date (newest first)
            processed_schools.sort(key=lambda s: s.get('graddate', ''), reverse=True)

            logger.debug(f"Returning {len(processed_schools)} schools: {processed_schools}")
            return processed_schools
        except Exception as e:
            logger.error(f"Error getting education: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def get_focus_areas_for_resume(self, resume_id: str, school_id: str, active_only: bool = True) -> List[
        Dict[str, Any]]:
        """
        Get focus areas for a specific school in a resume.

        :param str resume_id: Resume ID
        :param str school_id: School ID
        :param bool active_only: If True, only return active entries
        :return: List of focus area dictionaries
        """
        try:
            pk = f"RESUME#{resume_id}"
            sk_prefix = f"SCHOOL#{school_id}#FOCUS#"
            response = self.table.query(
                KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with(sk_prefix),
                FilterExpression=Attr('state').eq(True) if active_only else Attr('state').exists()
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Error getting focus areas for resume {resume_id}, school {school_id}: {str(e)}")
            return []

    def get_achievements_for_resume(self, resume_id: str, school_id: str, active_only: bool = True) -> List[
        Dict[str, Any]]:
        """
        Get achievements for a specific school in a resume.

        :param str resume_id: Resume ID
        :param str school_id: School ID
        :param bool active_only: If True, only return active entries
        :return: List of achievement dictionaries
        """
        try:
            pk = f"RESUME#{resume_id}"
            sk_prefix = f"SCHOOL#{school_id}#ACHIEVEMENT#"
            response = self.table.query(
                KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with(sk_prefix),
                FilterExpression=Attr('state').eq(True) if active_only else Attr('state').exists()
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Error getting achievements for resume {resume_id}, school {school_id}: {str(e)}")
            return []

    def add_achievement(self, school_id: str, description: str, resume_id: str = None) -> str:
        try:
            import uuid
            achievement_id = str(uuid.uuid4())

            logger.debug(f"Adding achievement: school_id={school_id}, description={description}, resume_id={resume_id}")

            if resume_id:
                # Create resume-specific achievement entry
                pk = f"RESUME#{resume_id}"
                sk = f"SCHOOL#{school_id}#ACHIEVEMENT#{achievement_id}"
                item = {
                    "PK": pk,
                    "SK": sk,
                    "id": achievement_id,
                    "school_id": school_id,
                    "description": description,
                    "state": True,
                    "entity_type": "achievement",
                    "resume_id": resume_id
                }
                self.table.put_item(Item=item)
                logger.debug(f"Added resume-specific achievement: {item}")
            else:
                # Use existing method for user-level achievement entries
                data = {
                    "school_id": school_id,
                    "description": description,
                    "state": 1
                }
                if self.user_id:
                    # Verify school ownership
                    school = self.query.get_by_id("school", school_id)
                    if not school or school.get('user_id') != self.user_id:
                        logger.error(
                            f"Unauthorized attempt to add achievement to school {school_id} for user {self.user_id}")
                        return None
                    data["user_id"] = self.user_id

                achievement_id = self.insert.multi_column("achievement", **data)
                logger.debug(f"Added user-level achievement: {data}")

            # Clear the cache after adding
            self.query.purge_cache("achievement")

            return achievement_id
        except Exception as e:
            logger.error(f"Error adding achievement: {str(e)}")
            return None

    def update_achievement(self, achievement_id: str, resume_id: str = None, **kwargs) -> bool:
        try:
            if resume_id:
                # Update resume-specific achievement entry
                pk = f"RESUME#{resume_id}"
                sk = f"SCHOOL#*#ACHIEVEMENT#{achievement_id}"  # We use a wildcard for the school_id part

                # Query to get the full SK
                response = self.table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with(sk),
                    Limit=1
                )
                items = response.get('Items', [])
                if not items:
                    logger.error(f"Achievement {achievement_id} not found for resume {resume_id}")
                    return False

                full_sk = items[0]['SK']

                update_expression = "SET "
                expression_attribute_values = {}
                expression_attribute_names = {}
                for key, value in kwargs.items():
                    # Use expression attribute names for all attributes to be safe
                    attr_name = f"#{key}"
                    update_expression += f"{attr_name} = :{key}, "
                    expression_attribute_values[f":{key}"] = value
                    expression_attribute_names[attr_name] = key
                update_expression = update_expression.rstrip(", ")

                self.table.update_item(
                    Key={"PK": pk, "SK": full_sk},
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_attribute_values,
                    ExpressionAttributeNames=expression_attribute_names
                )
            else:
                # Use existing method for user-level achievement entries
                if self.user_id:
                    # Verify ownership
                    achievement = self.query.get_by_id("achievement", achievement_id)
                    if not achievement or achievement.get('user_id') != self.user_id:
                        logger.error(
                            f"Unauthorized attempt to update achievement {achievement_id} for user {self.user_id}")
                        return False

                    # Add user_id to kwargs to ensure ownership is maintained
                    kwargs["user_id"] = self.user_id

                result = self.update.multi_column("achievement", achievement_id, **kwargs)

            # Clear the cache after updating
            self.query.purge_cache("achievement")

            return True
        except Exception as e:
            logger.error(f"Error updating achievement {achievement_id}: {str(e)}")
            return False

    def get_all_schools(self, resume_id=None):
        """
        Get all schools for the current user or resume.

        :param resume_id: Optional resume ID to get resume-specific schools
        :return: List of school objects
        """
        try:
            logger.debug(f"Getting all schools for user_id: {self.user_id}, resume_id: {resume_id}")

            schools = []
            if resume_id:
                # Get resume-specific schools
                pk = f"RESUME#{resume_id}"
                sk_prefix = "SCHOOL#"
                response = self.table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with(sk_prefix),
                    FilterExpression=Attr('type').eq('school')
                )
                schools = response.get('Items', [])
            elif self.user_id:
                # Get user-specific schools
                schools = self.query.get_user_items_by_type("school", self.user_id)

            logger.debug(f"Found {len(schools)} schools")
            return schools
        except Exception as e:
            logger.error(f"Error getting schools: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def add_school(self, name: str, degree: str = None, graddate: str = None, location: str = None,
                   description: str = None, resume_id: str = None) -> str:
        try:
            import uuid
            school_id = str(uuid.uuid4())

            logger.debug(
                f"Adding school: name={name}, degree={degree}, graddate={graddate}, location={location}, description={description}, resume_id={resume_id}")

            if resume_id:
                # Create resume-specific school entry
                pk = f"RESUME#{resume_id}"
                sk = f"SCHOOL#{school_id}"
                item = {
                    "PK": pk,
                    "SK": sk,
                    "id": school_id,
                    "name": name,
                    "state": True,
                    "entity_type": "school",
                    "type": "school",  # Add this field to match the filter in get_all_schools
                    "resume_id": resume_id
                }

                # Add optional fields if they exist
                if degree:
                    item["degree"] = degree
                if graddate:
                    item["graddate"] = graddate
                if location:
                    item["location"] = location
                if description:
                    item["description"] = description

                self.table.put_item(Item=item)
                logger.debug(f"Added resume-specific school: {item}")
            else:
                # Use existing method for user-level school entries
                data = {
                    "name": name,
                    "state": 1,
                    "type": "school"  # Add this field for consistency
                }

                # Add optional fields if they exist
                if degree:
                    data["degree"] = degree
                if graddate:
                    data["graddate"] = graddate
                if location:
                    data["location"] = location
                if description:
                    data["description"] = description

                if self.user_id:
                    data["user_id"] = self.user_id

                school_id = self.insert.multi_column("school", **data)
                logger.debug(f"Added user-level school: {data}")

            # Clear the cache after adding
            self.query.purge_cache("school")

            return school_id
        except Exception as e:
            logger.error(f"Error adding school: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def update_school(self, school_id: str, resume_id: str = None, **kwargs):
        try:
            logger.debug(f"Updating school: school_id={school_id}, resume_id={resume_id}, data={kwargs}")

            # Check if we need to delete an achievement
            achievement_to_delete = kwargs.pop('delete_achievement', None)
            if achievement_to_delete:
                logger.debug(f"Deleting achievement: {achievement_to_delete}")
                self.delete_school_achievement(achievement_to_delete, school_id, resume_id)

            # Proceed with updating the school
            if resume_id:
                # Update resume-specific school entry
                pk = f"RESUME#{resume_id}"
                sk = f"SCHOOL#{school_id}"

                update_expression = "SET "
                expression_attribute_values = {}
                expression_attribute_names = {}
                for key, value in kwargs.items():
                    # Use expression attribute names for all attributes to be safe
                    attr_name = f"#{key}"
                    update_expression += f"{attr_name} = :{key}, "
                    expression_attribute_values[f":{key}"] = value
                    expression_attribute_names[attr_name] = key
                update_expression = update_expression.rstrip(", ")

                self.table.update_item(
                    Key={"PK": pk, "SK": sk},
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_attribute_values,
                    ExpressionAttributeNames=expression_attribute_names
                )
                result = True
            else:
                # Use existing method for user-level school entries
                if self.user_id:
                    # Verify ownership
                    school = self.query.get_by_id("school", school_id)
                    if not school or school.get('user_id') != self.user_id:
                        logger.error(f"Unauthorized attempt to update school {school_id} for user {self.user_id}")
                        return False

                    # Add user_id to kwargs to ensure ownership is maintained
                    kwargs["user_id"] = self.user_id

                result = self.update.multi_column("school", school_id, **kwargs)

            # Clear the cache after updating
            self.query.purge_cache("school")

            logger.debug(f"update_school result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error updating school {school_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def delete_school(self, school_id: str, resume_id: str = None) -> bool:
        """
        Delete a school and all associated focuses and achievements.

        :param school_id: The ID of the school to delete
        :param resume_id: Optional resume ID if deleting from a specific resume
        :return: True if successful, False otherwise
        """
        try:
            logger.debug(f"Deleting school {school_id} for resume {resume_id}")

            # Get all focuses for this school
            focuses = self.get_focuses_by_school(school_id, resume_id)

            # Delete all focuses
            for focus in focuses:
                focus_id = focus.get('id')
                if not focus_id and 'SK' in focus:
                    sk = focus.get('SK', '')
                    if '#FOCUS#' in sk:
                        focus_id = sk.split('#FOCUS#')[1]

                if focus_id:
                    logger.debug(f"Deleting focus {focus_id} for school {school_id}")
                    self.delete_entry("focus", focus_id, resume_id)

            # Get all achievements for this school
            achievements = []
            if resume_id:
                # Query for resume-specific achievements
                pk = f"RESUME#{resume_id}"
                sk_prefix = f"SCHOOL#{school_id}#ACHIEVEMENT#"
                response = self.table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with(sk_prefix)
                )
                achievements = response.get('Items', [])
            elif self.user_id:
                # Get user-specific achievements for this school
                achievements = self.query.get_user_items_by_parent("achievement", self.user_id, "school_id", school_id)
            else:
                # Get all achievements for this school
                achievements = self.query.get_items_by_parent("achievement", "school_id", school_id)

            # Delete all achievements
            for achievement in achievements:
                achievement_id = achievement.get('id')
                if not achievement_id and 'SK' in achievement:
                    sk = achievement.get('SK', '')
                    if '#ACHIEVEMENT#' in sk:
                        achievement_id = sk.split('#ACHIEVEMENT#')[1]

                if achievement_id:
                    logger.debug(f"Deleting achievement {achievement_id} for school {school_id}")
                    self.delete_entry("achievement", achievement_id, resume_id)

            # Finally delete the school itself
            if resume_id:
                # Delete resume-specific school entry
                pk = f"RESUME#{resume_id}"
                sk = f"SCHOOL#{school_id}"
                self.table.delete_item(
                    Key={
                        'PK': pk,
                        'SK': sk
                    }
                )
                logger.debug(f"Deleted resume-specific school {school_id} from resume {resume_id}")
                result = True
            else:
                # Use existing delete_entry method for user-level school
                result = self.delete_entry("school", school_id)
                logger.debug(f"Deleted user-level school {school_id}, result: {result}")

            # Clear the cache after deletion
            self.query.purge_cache("school")
            self.query.purge_cache("focus")
            self.query.purge_cache("achievement")

            return result
        except Exception as e:
            logger.error(f"Error deleting school {school_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def add_focus(self, school_id: str, description: str, resume_id: str = None) -> str:
        try:
            import uuid
            focus_id = str(uuid.uuid4())

            logger.debug(f"Adding focus: school_id={school_id}, description={description}, resume_id={resume_id}")

            if resume_id:
                # Create resume-specific focus entry
                pk = f"RESUME#{resume_id}"
                sk = f"SCHOOL#{school_id}#FOCUS#{focus_id}"
                item = {
                    "PK": pk,
                    "SK": sk,
                    "id": focus_id,
                    "school_id": school_id,
                    "description": description,
                    "state": True,
                    "entity_type": "focus",
                    "resume_id": resume_id
                }
                self.table.put_item(Item=item)
                logger.debug(f"Added resume-specific focus: {item}")
            else:
                # Use existing method for user-level focus entries
                data = {
                    "school_id": school_id,
                    "description": description,
                    "state": 1
                }
                if self.user_id:
                    # Verify school ownership
                    school = self.query.get_by_id("school", school_id)
                    if not school or school.get('user_id') != self.user_id:
                        logger.error(f"Unauthorized attempt to add focus to school {school_id} for user {self.user_id}")
                        return None
                    data["user_id"] = self.user_id

                focus_id = self.insert.multi_column("focus", **data)
                logger.debug(f"Added user-level focus: {data}")

            # Clear the cache after adding
            self.query.purge_cache("focus")

            return focus_id
        except Exception as e:
            logger.error(f"Error adding focus: {str(e)}")
            return None

    def update_focus(self, focus_id: str, resume_id: str = None, **kwargs) -> bool:
        try:
            if resume_id:
                # Update resume-specific focus entry
                pk = f"RESUME#{resume_id}"
                sk = f"SCHOOL#*#FOCUS#{focus_id}"  # We use a wildcard for the school_id part

                # Query to get the full SK
                response = self.table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with(sk),
                    Limit=1
                )
                items = response.get('Items', [])
                if not items:
                    logger.error(f"Focus {focus_id} not found for resume {resume_id}")
                    return False

                full_sk = items[0]['SK']

                update_expression = "SET "
                expression_attribute_values = {}
                expression_attribute_names = {}
                for key, value in kwargs.items():
                    # Use expression attribute names for all attributes to be safe
                    attr_name = f"#{key}"
                    update_expression += f"{attr_name} = :{key}, "
                    expression_attribute_values[f":{key}"] = value
                    expression_attribute_names[attr_name] = key
                update_expression = update_expression.rstrip(", ")

                self.table.update_item(
                    Key={"PK": pk, "SK": full_sk},
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_attribute_values,
                    ExpressionAttributeNames=expression_attribute_names
                )
            else:
                # Use existing method for user-level focus entries
                if self.user_id:
                    # Verify ownership
                    focus = self.query.get_by_id("focus", focus_id)
                    if not focus or focus.get('user_id') != self.user_id:
                        logger.error(f"Unauthorized attempt to update focus {focus_id} for user {self.user_id}")
                        return False

                    # Add user_id to kwargs to ensure ownership is maintained
                    kwargs["user_id"] = self.user_id

                result = self.update.multi_column("focus", focus_id, **kwargs)

            # Clear the cache after updating
            self.query.purge_cache("focus")

            return True
        except Exception as e:
            logger.error(f"Error updating focus {focus_id}: {str(e)}")
            return False

    def get_focuses_by_school(self, school_id: str, resume_id: str = None, active_only: bool = True) -> List[
        Dict[str, Any]]:
        """
        Get all focus areas for a specific school.

        :param school_id: The ID of the school
        :param resume_id: Optional resume ID to get resume-specific focuses
        :param active_only: Whether to only return active focuses
        :return: List of focus areas
        """
        try:
            logger.debug(
                f"Getting focuses for school_id: {school_id}, resume_id: {resume_id}, active_only: {active_only}")

            focuses = []
            if resume_id:
                # Query for resume-specific focus entries
                pk = f"RESUME#{resume_id}"
                sk_prefix = f"SCHOOL#{school_id}#FOCUS#"
                response = self.table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with(sk_prefix),
                    FilterExpression=Attr('state').eq(True) if active_only else Attr('state').exists()
                )
                focuses = response.get('Items', [])
                logger.debug(f"Found {len(focuses)} focuses for school {school_id} in resume {resume_id}")
            elif self.user_id:
                # Get user-specific focuses for this school
                focuses = self.query.get_user_items_by_parent("focus", self.user_id, "school_id", school_id,
                                                              active_only)
                logger.debug(f"Found {len(focuses)} focuses for school {school_id} for user {self.user_id}")
            else:
                # Get all focuses for this school
                focuses = self.query.get_items_by_parent("focus", "school_id", school_id, active_only)
                logger.debug(f"Found {len(focuses)} focuses for school {school_id} (global)")

            return focuses
        except Exception as e:
            logger.error(f"Error getting focuses for school {school_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def add_school_achievement(self, school_id: str, description: str, resume_id: str = None) -> str:
        """
        Add an achievement to a school.

        :param school_id: The ID of the school
        :param description: Achievement description
        :param resume_id: Optional resume ID for resume-specific achievements
        :return: ID of the new achievement, or None on failure
        """
        try:
            import uuid
            achievement_id = str(uuid.uuid4())

            logger.debug(
                f"Adding achievement to school: school_id={school_id}, description={description}, resume_id={resume_id}")

            if resume_id:
                # Create resume-specific achievement entry
                pk = f"RESUME#{resume_id}"
                sk = f"SCHOOL#{school_id}#ACHIEVEMENT#{achievement_id}"
                item = {
                    "PK": pk,
                    "SK": sk,
                    "id": achievement_id,
                    "school_id": school_id,
                    "description": description,
                    "state": True,
                    "entity_type": "achievement",
                    "resume_id": resume_id
                }
                self.table.put_item(Item=item)
                logger.debug(f"Added resume-specific school achievement: {item}")
            else:
                # Use existing method for user-level achievement entries
                data = {
                    "school_id": school_id,
                    "description": description,
                    "state": True
                }
                if self.user_id:
                    # Verify school ownership
                    school = self.query.get_by_id("school", school_id)
                    if not school or school.get('user_id') != self.user_id:
                        logger.error(
                            f"Unauthorized attempt to add achievement to school {school_id} for user {self.user_id}")
                        return None
                    data["user_id"] = self.user_id

                achievement_id = self.insert.multi_column("achievement", **data)
                logger.debug(f"Added user-level school achievement: {data}")

            return achievement_id
        except Exception as e:
            logger.error(f"Failed to add achievement: {e}")
            return None

    def update_school_achievement(self, school_id: str, achievement_id: str, description: str,
                                  resume_id: str = None) -> bool:
        """
        Update an achievement for a school.

        :param school_id: The ID of the school
        :param achievement_id: The ID of the achievement to update
        :param description: New achievement description
        :param resume_id: Optional resume ID for resume-specific achievements
        :return: True if successful, False otherwise
        """
        try:
            logger.debug(
                f"Updating school achievement: school_id={school_id}, achievement_id={achievement_id}, description={description}, resume_id={resume_id}")

            if resume_id:
                # Update resume-specific achievement entry
                pk = f"RESUME#{resume_id}"
                sk = f"SCHOOL#{school_id}#ACHIEVEMENT#{achievement_id}"

                update_expression = "SET #desc = :description, #state = :state"
                expression_attribute_values = {
                    ":description": description,
                    ":state": True
                }
                expression_attribute_names = {
                    "#desc": "description",
                    "#state": "state"
                }

                self.table.update_item(
                    Key={"PK": pk, "SK": sk},
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_attribute_values,
                    ExpressionAttributeNames=expression_attribute_names
                )
                logger.debug(f"Updated resume-specific school achievement: {achievement_id}")
            else:
                # Use existing method for user-level achievement entries
                data = {
                    "description": description,
                    "state": True
                }
                if self.user_id:
                    # Verify achievement ownership
                    achievement = self.query.get_by_id("achievement", achievement_id)
                    if not achievement or achievement.get('user_id') != self.user_id:
                        logger.error(
                            f"Unauthorized attempt to update achievement {achievement_id} for user {self.user_id}")
                        return False
                    data["user_id"] = self.user_id

                result = self.update.multi_column("achievement", achievement_id, **data)
                if not result:
                    logger.error(f"Failed to update achievement {achievement_id}")
                    return False
                logger.debug(f"Updated user-level school achievement: {achievement_id}")

            # Clear the cache after updating
            self.query.purge_cache("achievement")

            return True
        except Exception as e:
            logger.error(f"Error updating school achievement: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def get_achievements_by_school(self, school_id: str, resume_id: str = None, active_only: bool = True) -> List[
        Dict[str, Any]]:
        """
        Get all achievements for a specific school.

        :param school_id: The ID of the school
        :param resume_id: Optional resume ID to get resume-specific achievements
        :param active_only: Whether to only return active achievements
        :return: List of achievements
        """
        try:
            logger.debug(
                f"Getting achievements for school_id: {school_id}, resume_id: {resume_id}, active_only: {active_only}")

            achievements = []
            if resume_id:
                # Query for resume-specific achievement entries
                pk = f"RESUME#{resume_id}"
                sk_prefix = f"SCHOOL#{school_id}#ACHIEVEMENT#"
                response = self.table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with(sk_prefix),
                    FilterExpression=Attr('state').eq(True) if active_only else Attr('state').exists()
                )
                achievements = response.get('Items', [])
                logger.debug(f"Found {len(achievements)} achievements for school {school_id} in resume {resume_id}")
            elif self.user_id:
                # Get user-specific achievements for this school
                achievements = self.query.get_user_items_by_parent("achievement", self.user_id, "school_id",
                                                                   school_id, active_only)
                logger.debug(
                    f"Found {len(achievements)} achievements for school {school_id} for user {self.user_id}")
            else:
                # Get all achievements for this school
                achievements = self.query.get_items_by_parent("achievement", "school_id", school_id, active_only)
                logger.debug(f"Found {len(achievements)} achievements for school {school_id} (global)")

            return achievements
        except Exception as e:
            logger.error(f"Error getting achievements for school {school_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def delete_school_achievement(self, achievement_id, school_id=None, resume_id=None):
        try:
            logger.debug(
                f"Deleting school achievement: achievement_id={achievement_id}, school_id={school_id}, resume_id={resume_id}")

            if resume_id:
                # Delete resume-specific achievement
                pk = f"RESUME#{resume_id}"

                if school_id:
                    sk = f"SCHOOL#{school_id}#ACHIEVEMENT#{achievement_id}"
                    self.table.delete_item(Key={'PK': pk, 'SK': sk})
                else:
                    # If school_id is not provided, we need to find the full SK
                    response = self.table.query(
                        KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with("SCHOOL#"),
                        ProjectionExpression="SK"
                    )
                    items = response.get('Items', [])
                    for item in items:
                        sk = item['SK']
                        if f"#ACHIEVEMENT#{achievement_id}" in sk:
                            self.table.delete_item(Key={'PK': pk, 'SK': sk})
                            break
                    else:
                        logger.error(f"Achievement {achievement_id} not found for resume {resume_id}")
                        return False
            else:
                # Delete user-level achievement
                result = self.delete_entry("achievement", achievement_id)
                if not result:
                    logger.error(f"Failed to delete achievement {achievement_id}")
                    return False

            logger.debug(f"Successfully deleted achievement {achievement_id}")

            # Clear the cache after deletion
            self.query.purge_cache("achievement")

            return True
        except Exception as e:
            logger.error(f"Error deleting school achievement: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    # ==================== EMPLOYMENT/EXPERIENCE METHODS ====================

    def get_all_employment(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Alias for get_all_experience.

        :param bool active_only: If True, only return active entries
        :return: List of employer dictionaries with positions and achievements
        """
        return self.get_all_experience(active_only)

    def get_all_experience(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all employer entries with positions and achievements for the current user.

        :param bool active_only: If True, only return active entries
        :return: List of employer dictionaries with positions and achievements
        """
        try:
            if self.user_id:
                employers = self.query.get_user_items("employer", self.user_id, active_only)
            else:
                employers = self.query.get_all("employer", active_only)

            # Get positions for each employer
            for employer in employers:
                employer_id = employer.get('SK')
                if employer_id:
                    if self.user_id:
                        positions = self.query.get_user_items_by_parent("position", self.user_id, "employer_id",
                                                                        employer_id, active_only)
                    else:
                        positions = self.query.get_items_by_parent("position", "employer_id", employer_id, active_only)

                    # Get achievements for each position
                    for position in positions:
                        position_id = position.get('SK')
                        if position_id:
                            if self.user_id:
                                achievements = self.query.get_user_items_by_parent("achievement", self.user_id,
                                                                                   "position_id", position_id,
                                                                                   active_only)
                            else:
                                achievements = self.query.get_items_by_parent("achievement", "position_id", position_id,
                                                                              active_only)

                            position['achievements'] = achievements

                    # Sort positions by date (newest first)
                    positions.sort(key=lambda p: p.get('startdate', ''), reverse=True)
                    employer['positions'] = positions

            # Sort employers by most recent position
            def get_most_recent_date(employer):
                positions = employer.get('positions', [])
                if positions:
                    return positions[0].get('startdate', '')
                return ''

            employers.sort(key=get_most_recent_date, reverse=True)

            return employers
        except Exception as e:
            logger.error(f"Error getting experience: {str(e)}")
            return []

    def add_employer(self, name: str, location: str) -> str:
        """
        Add a new employer entry for the current user.

        :param str name: Employer name
        :param str location: Employer location
        :return str: ID of new entry, or None on failure
        """
        try:
            data = {
                "name": name,
                "location": location,
                "state": 1
            }

            # Add user_id if available
            if self.user_id:
                data["user_id"] = self.user_id

            result = self.insert.multi_column("employer", **data)

            # Clear the cache after adding
            self.query.purge_cache("employer")

            return result
        except Exception as e:
            logger.error(f"Error adding employer: {str(e)}")
            return None

    def update_employer(self, employer_id: str, **kwargs) -> bool:
        """
        Update an employer entry.

        :param str employer_id: ID of employer to update
        :param kwargs: Fields to update
        :return bool: True if successful, False otherwise
        """
        try:
            if self.user_id:
                # Verify ownership
                employer = self.query.get_by_id("employer", employer_id)
                if not employer or employer.get('user_id') != self.user_id:
                    logger.error(f"Unauthorized attempt to update employer {employer_id} for user {self.user_id}")
                    return False

                # Add user_id to kwargs to ensure ownership is maintained
                kwargs["user_id"] = self.user_id

            result = self.update.multi_column("employer", employer_id, **kwargs)

            # Clear the cache after updating
            self.query.purge_cache("employer")

            return result
        except Exception as e:
            logger.error(f"Error updating employer {employer_id}: {str(e)}")
            return False

    def add_position(self, employer_id: str, title: str, startdate: str, enddate: str = None,
                     current: bool = False) -> str:
        """
        Add a new position entry for an employer.

        :param str employer_id: ID of parent employer
        :param str title: Position title
        :param str startdate: Start date (MM/YYYY)
        :param str enddate: End date (MM/YYYY) or None if current
        :param bool current: Whether this is the current position
        :return str: ID of new entry, or None on failure
        """
        try:
            data = {
                "employer_id": employer_id,
                "title": title,
                "startdate": startdate,
                "state": 1,
                "current": 1 if current else 0
            }

            if enddate and not current:
                data["enddate"] = enddate

            # Add user_id if available
            if self.user_id:
                # Verify employer ownership
                employer = self.query.get_by_id("employer", employer_id)
                if not employer or employer.get('user_id') != self.user_id:
                    logger.error(
                        f"Unauthorized attempt to add position to employer {employer_id} for user {self.user_id}")
                    return None

                data["user_id"] = self.user_id

            result = self.insert.multi_column("position", **data)

            # Clear the cache after adding
            self.query.purge_cache("position")

            return result
        except Exception as e:
            logger.error(f"Error adding position: {str(e)}")
            return None

    def update_position(self, position_id: str, **kwargs) -> bool:
        """
        Update a position entry.

        :param str position_id: ID of position to update
        :param kwargs: Fields to update
        :return bool: True if successful, False otherwise
        """
        try:
            if self.user_id:
                # Verify ownership
                position = self.query.get_by_id("position", position_id)
                if not position or position.get('user_id') != self.user_id:
                    logger.error(f"Unauthorized attempt to update position {position_id} for user {self.user_id}")
                    return False

                # Add user_id to kwargs to ensure ownership is maintained
                kwargs["user_id"] = self.user_id

            # Handle current position logic
            if 'current' in kwargs and kwargs['current'] == 1:
                kwargs.pop('enddate', None)  # Remove enddate if current is True

            result = self.update.multi_column("position", position_id, **kwargs)

            # Clear the cache after updating
            self.query.purge_cache("position")

            return result
        except Exception as e:
            logger.error(f"Error updating position {position_id}: {str(e)}")
            return False

    # ==================== SKILLS METHODS ====================

    def get_all_skills(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all skill entries for the current user, grouped by category.

        :param bool active_only: If True, only return active entries
        :return: List of skill dictionaries grouped by category
        """
        try:
            if self.user_id:
                skills = self.query.get_user_items("skill", self.user_id, active_only)
            else:
                skills = self.query.get_all("skill", active_only)

            # Group skills by category
            skill_categories = {}
            for skill in skills:
                category = skill.get('category', 'Uncategorized')
                if category not in skill_categories:
                    skill_categories[category] = []
                skill_categories[category].append(skill)

            # Sort skills within each category by name
            for category in skill_categories:
                skill_categories[category].sort(key=lambda s: s.get('name', ''))

            # Convert to list of categories with skills
            result = []
            for category, skills in sorted(skill_categories.items()):
                result.append({
                    'category': category,
                    'skills': skills
                })

            return result
        except Exception as e:
            logger.error(f"Error getting skills: {str(e)}")
            return []

    def add_skill(self, name: str, category: str = None, proficiency: int = None) -> str:
        """
        Add a new skill entry for the current user.

        :param str name: Skill name
        :param str category: Skill category (optional)
        :param int proficiency: Skill proficiency level (1-5, optional)
        :return str: ID of new entry, or None on failure
        """
        try:
            data = {
                "name": name,
                "state": 1
            }

            if category:
                data["category"] = category

            if proficiency is not None:
                data["proficiency"] = min(max(1, proficiency), 5)  # Ensure between 1-5

            # Add user_id if available
            if self.user_id:
                data["user_id"] = self.user_id

            result = self.insert.multi_column("skill", **data)

            # Clear the cache after adding
            self.query.purge_cache("skill")

            return result
        except Exception as e:
            logger.error(f"Error adding skill: {str(e)}")
            return None

    def update_skill(self, skill_id: str, **kwargs) -> bool:
        """
        Update a skill entry.

        :param str skill_id: ID of skill to update
        :param kwargs: Fields to update
        :return bool: True if successful, False otherwise
        """
        try:
            if self.user_id:
                # Verify ownership
                skill = self.query.get_by_id("skill", skill_id)
                if not skill or skill.get('user_id') != self.user_id:
                    logger.error(f"Unauthorized attempt to update skill {skill_id} for user {self.user_id}")
                    return False

                # Add user_id to kwargs to ensure ownership is maintained
                kwargs["user_id"] = self.user_id

            # Ensure proficiency is between 1-5
            if 'proficiency' in kwargs:
                kwargs['proficiency'] = min(max(1, kwargs['proficiency']), 5)

            result = self.update.multi_column("skill", skill_id, **kwargs)

            # Clear the cache after updating
            self.query.purge_cache("skill")

            return result
        except Exception as e:
            logger.error(f"Error updating skill {skill_id}: {str(e)}")
            return False

    # ==================== PROJECTS METHODS ====================

    def get_all_projects(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all project entries for the current user.

        :param bool active_only: If True, only return active entries
        :return: List of project dictionaries
        """
        try:
            if self.user_id:
                projects = self.query.get_user_items("project", self.user_id, active_only)
            else:
                projects = self.query.get_all("project", active_only)

            # Sort projects by date (newest first)
            projects.sort(key=lambda p: p.get('date', ''), reverse=True)

            return projects
        except Exception as e:
            logger.error(f"Error getting projects: {str(e)}")
            return []

    def add_project(self, name: str, description: str, date: str = None, url: str = None) -> str:
        """
        Add a new project entry for the current user.

        :param str name: Project name
        :param str description: Project description
        :param str date: Project date (optional)
        :param str url: Project URL (optional)
        :return str: ID of new entry, or None on failure
        """
        try:
            data = {
                "name": name,
                "description": description,
                "state": 1
            }

            if date:
                data["date"] = date

            if url:
                data["url"] = url

            # Add user_id if available
            if self.user_id:
                data["user_id"] = self.user_id

            result = self.insert.multi_column("project", **data)

            # Clear the cache after adding
            self.query.purge_cache("project")

            return result
        except Exception as e:
            logger.error(f"Error adding project: {str(e)}")
            return None

    def update_project(self, project_id: str, **kwargs) -> bool:
        """
        Update a project entry.

        :param str project_id: ID of project to update
        :param kwargs: Fields to update
        :return bool: True if successful, False otherwise
        """
        try:
            if self.user_id:
                # Verify ownership
                project = self.query.get_by_id("project", project_id)
                if not project or project.get('user_id') != self.user_id:
                    logger.error(f"Unauthorized attempt to update project {project_id} for user {self.user_id}")
                    return False

                # Add user_id to kwargs to ensure ownership is maintained
                kwargs["user_id"] = self.user_id

            result = self.update.multi_column("project", project_id, **kwargs)

            # Clear the cache after updating
            self.query.purge_cache("project")

            return result
        except Exception as e:
            logger.error(f"Error updating project {project_id}: {str(e)}")
            return False

        # ==================== CERTIFICATIONS METHODS ====================

    def get_all_certifications(self, resume_id=None, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all certification entries for the current user or a specific resume.

        :param resume_id: Optional resume ID to get resume-specific certifications
        :param bool active_only: If True, only return active entries
        :return: List of certification dictionaries
        """
        try:
            logger.debug(
                f"Getting certifications for resume_id: {resume_id}, active_only: {active_only}, user_id: {self.user_id}")

            certifications = []
            if resume_id:
                # Query for resume-specific certification entries
                pk = f"RESUME#{resume_id}"
                response = self.table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('CERTIFICATION#'),
                    FilterExpression=Attr('state').eq(True) if active_only else Attr('state').exists()
                )
                certifications = response.get('Items', [])
                logger.debug(f"Found {len(certifications)} certifications for resume {resume_id}")
            elif self.user_id:
                certifications = self.query.get_user_items("certification", self.user_id, active_only)
                logger.debug(f"Found {len(certifications)} certifications for user {self.user_id}")
            else:
                certifications = self.query.get_all("certification", active_only)
                logger.debug(f"Found {len(certifications)} certifications (global)")

            # Process certifications to ensure consistent structure
            processed_certifications = []
            for cert in certifications:
                # Extract certification_id based on whether it's a resume-specific entry or not
                cert_id = cert.get('id')
                if not cert_id and 'SK' in cert:
                    sk = cert.get('SK', '')
                    if sk.startswith('CERTIFICATION#'):
                        cert_id = sk.split('#')[1]
                        cert['id'] = cert_id

                # Ensure all required fields exist
                cert.setdefault('name', '')
                cert.setdefault('authority', '')
                cert.setdefault('date_achieved', '')
                cert.setdefault('expiration_date', '')
                cert.setdefault('certorder', 99)
                cert.setdefault('state', True)

                processed_certifications.append(cert)

            # Sort certifications by order, then by date achieved (newest first)
            processed_certifications.sort(key=lambda c: (int(c.get('certorder', 99)), c.get('date_achieved', '')), reverse=True)

            logger.debug(f"Returning {len(processed_certifications)} certifications: {processed_certifications}")
            return processed_certifications
        except Exception as e:
            logger.error(f"Error getting certifications: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def add_certification(self, name: str, authority: str, date_achieved: str = None,
                         expiration_date: str = None, certorder: int = 99, resume_id: str = None) -> str:
        """
        Add a new certification entry.

        :param str name: Certification name
        :param str authority: Certification issuing authority
        :param str date_achieved: Date the certification was achieved
        :param str expiration_date: Date the certification expires (optional)
        :param int certorder: Order to display the certification (lower numbers first)
        :param str resume_id: Optional resume ID to add to a specific resume
        :return str: ID of new entry, or None on failure
        """
        try:
            import uuid
            cert_id = str(uuid.uuid4())

            logger.debug(
                f"Adding certification: name={name}, authority={authority}, date_achieved={date_achieved}, "
                f"expiration_date={expiration_date}, certorder={certorder}, resume_id={resume_id}")

            if resume_id:
                # Create resume-specific certification entry
                pk = f"RESUME#{resume_id}"
                sk = f"CERTIFICATION#{cert_id}"
                item = {
                    "PK": pk,
                    "SK": sk,
                    "id": cert_id,
                    "name": name,
                    "authority": authority,
                    "state": True,
                    "entity_type": "certification",
                    "resume_id": resume_id,
                    "certorder": certorder
                }

                # Add optional fields if they exist
                if date_achieved:
                    item["date_achieved"] = date_achieved
                if expiration_date:
                    item["expiration_date"] = expiration_date

                self.table.put_item(Item=item)
                logger.debug(f"Added resume-specific certification: {item}")
            else:
                # Use existing method for user-level certification entries
                data = {
                    "name": name,
                    "authority": authority,
                    "state": 1,
                    "certorder": certorder
                }

                # Add optional fields if they exist
                if date_achieved:
                    data["date_achieved"] = date_achieved
                if expiration_date:
                    data["expiration_date"] = expiration_date

                if self.user_id:
                    data["user_id"] = self.user_id

                cert_id = self.insert.multi_column("certification", **data)
                logger.debug(f"Added user-level certification: {data}")

            # Clear the cache after adding
            self.query.purge_cache("certification")

            return cert_id
        except Exception as e:
            logger.error(f"Error adding certification: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def update_certification(self, cert_id: str, resume_id: str = None, **kwargs) -> bool:
        """
        Update an existing certification entry.

        :param str cert_id: ID of the certification to update
        :param str resume_id: Optional resume ID if updating a resume-specific certification
        :param kwargs: Fields to update
        :return bool: True if successful, False otherwise
        """
        try:
            logger.debug(f"Updating certification: cert_id={cert_id}, resume_id={resume_id}, data={kwargs}")

            if resume_id:
                # Update resume-specific certification entry
                pk = f"RESUME#{resume_id}"
                sk = f"CERTIFICATION#{cert_id}"

                update_expression = "SET "
                expression_attribute_values = {}
                expression_attribute_names = {}
                for key, value in kwargs.items():
                    # Use expression attribute names for all attributes to be safe
                    attr_name = f"#{key}"
                    update_expression += f"{attr_name} = :{key}, "
                    expression_attribute_values[f":{key}"] = value
                    expression_attribute_names[attr_name] = key
                update_expression = update_expression.rstrip(", ")

                self.table.update_item(
                    Key={"PK": pk, "SK": sk},
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_attribute_values,
                    ExpressionAttributeNames=expression_attribute_names
                )
                result = True
            else:
                # Use existing method for user-level certification entries
                if self.user_id:
                    # Verify ownership
                    cert = self.query.get_by_id("certification", cert_id)
                    if not cert or cert.get('user_id') != self.user_id:
                        logger.error(f"Unauthorized attempt to update certification {cert_id} for user {self.user_id}")
                        return False

                    # Add user_id to kwargs to ensure ownership is maintained
                    kwargs["user_id"] = self.user_id

                result = self.update.multi_column("certification", cert_id, **kwargs)

            # Clear the cache after updating
            self.query.purge_cache("certification")

            logger.debug(f"update_certification result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error updating certification {cert_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def delete_certification(self, cert_id: str, resume_id: str = None) -> bool:
        """
        Delete a certification entry.

        :param str cert_id: ID of the certification to delete
        :param str resume_id: Optional resume ID if deleting from a specific resume
        :return bool: True if successful, False otherwise
        """
        try:
            logger.debug(f"Deleting certification {cert_id} for resume {resume_id}")

            if resume_id:
                # Delete resume-specific certification entry
                pk = f"RESUME#{resume_id}"
                sk = f"CERTIFICATION#{cert_id}"
                self.table.delete_item(
                    Key={
                        'PK': pk,
                        'SK': sk
                    }
                )
                logger.debug(f"Deleted resume-specific certification {cert_id} from resume {resume_id}")
                result = True
            else:
                # Use existing delete_entry method for user-level certification
                result = self.delete_entry("certification", cert_id)
                logger.debug(f"Deleted user-level certification {cert_id}, result: {result}")

            # Clear the cache after deletion
            self.query.purge_cache("certification")

            return result
        except Exception as e:
            logger.error(f"Error deleting certification {cert_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

        # ==================== GENERAL METHODS ====================

    def delete_entry(self, entity_type: str, entry_id: str, resume_id=None) -> bool:
        """
        Delete an entry by setting its state to False.

        :param str entity_type: Type of entity (e.g., 'summary', 'education')
        :param str entry_id: ID of the entry to delete
        :param str resume_id: Optional resume ID this entry belongs to
        :return bool: True if successful, False otherwise
        """
        try:
            if not self.user_id and not resume_id:
                logger.warning("No user_id or resume_id available, cannot delete entry")
                return False

            # For resume-specific entities like identification and summary
            if entity_type.lower() in ['identification', 'summary'] and resume_id:
                # Determine the correct PK based on resume_id
                pk = f"RESUME#{resume_id}"

                # Remove any prefix if present
                if entry_id.startswith(f"{entity_type.upper()}#"):
                    entry_id = entry_id.split("#")[1]

                # Log the deletion attempt
                logger.debug(f"Attempting to delete {entity_type} entry {entry_id} from resume {resume_id}")
                logger.debug(f"Using PK={pk}, SK={entity_type.upper()}#{entry_id}")

                # Set state to False using update_item
                response = self.table.update_item(
                    Key={
                        "PK": pk,
                        "SK": f"{entity_type.upper()}#{entry_id}"
                    },
                    UpdateExpression="SET #state = :state, #updated_at = :updated_at",
                    ExpressionAttributeNames={
                        "#state": "state",
                        "#updated_at": "updated_at"
                    },
                    ExpressionAttributeValues={
                        ":state": False,
                        ":updated_at": datetime.now().isoformat()
                    },
                    ReturnValues="UPDATED_NEW"  # Return the updated values
                )

                logger.debug(f"DynamoDB update response: {response}")

                # Clear cache for this entity type
                if hasattr(self.query, 'purge_cache'):
                    logger.debug(f"Purging cache for {entity_type.lower()}")
                    self.query.purge_cache(entity_type.lower())

                    # Also purge any resume-specific cache
                    cache_key = f"{entity_type.lower()}_{resume_id}"
                    logger.debug(f"Purging resume-specific cache for {cache_key}")
                    self.query.purge_cache(cache_key)

                return True
            else:
                # For other entity types, use the existing method
                logger.debug(f"Using update.set_state for {entity_type} entry {entry_id}")
                return self.update.set_state(entity_type, entry_id, False)
        except Exception as e:
            logger.error(f"Error deleting {entity_type} entry {entry_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def get_resume_data(self, resume_id=None) -> Dict[str, Any]:
        """
        Get all resume data for the current user.

        :param str resume_id: Optional resume ID to get data for
        :return: Dictionary containing all resume sections
        """
        try:
            # Get identification data
            identification = self.get_identification(resume_id=resume_id)

            # Get all other sections
            summaries = self.get_all_summaries(resume_id=resume_id)
            education = self.get_all_education()
            experience = self.get_all_experience()
            skills = self.get_all_skills()
            projects = self.get_all_projects()
            certifications = self.get_all_certifications()

            # Combine into a single dictionary
            resume_data = {
                "identification": identification,
                "summaries": summaries,
                "education": education,
                "experience": experience,
                "skills": skills,
                "projects": projects,
                "certifications": certifications
            }

            return resume_data
        except Exception as e:
            logger.error(f"Error getting resume data: {str(e)}")
            return {
                "identification": {},
                "summaries": [],
                "education": [],
                "experience": [],
                "skills": [],
                "projects": [],
                "certifications": []
            }