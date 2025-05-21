from datetime import datetime
import logging
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_delay, wait_exponential
from pylaform.database.connect import db

logger = logging.getLogger(__name__)


class DynamoUpdates:
    """
    Handle all DynamoDB update operations with proper error handling.
    """

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def __init__(self):
        """
        Initialize the DynamoDB connection.
        """
        # Get table from connect.py
        self.table = db()

    def update_identification(self, attr: str, value: str, contacttype: str = None, user_id: str = None,
                              label: str = None) -> bool:
        """
        Update an identification entry.

        :param str attr: The attribute name (e.g., 'email', 'name') or the SK of an existing item
        :param str value: The new value
        :param str contacttype: Optional contact type, defaults to attr if not specified
        :param str user_id: Optional user ID to associate with this identification
        :param str label: Optional friendly display name for this identification
        :return bool: True if successful, False otherwise
        """
        try:
            # DEBUG: Print exact input values
            print(
                f"DEBUG: update_identification called with attr='{attr}', value='{value}', contacttype='{contacttype}', user_id='{user_id}', label='{label}'")

            # If contacttype not provided, use attr as the contacttype
            if contacttype is None:
                contacttype = attr
                print(f"DEBUG: contacttype set to '{contacttype}'")

            # The SK for identification items is attr-contacttype (without timestamp)
            item_id = f"{attr}-{contacttype}"
            print(f"DEBUG: item_id constructed as '{item_id}'")

            # DEBUG: Explicitly show the key being used
            print(f"DEBUG: Using key PK='IDENTIFICATION', SK='{item_id}'")

            # First, check if the item exists
            try:
                response = self.table.get_item(
                    Key={
                        'PK': "IDENTIFICATION",
                        'SK': item_id
                    }
                )
                item_exists = 'Item' in response
                print(f"DEBUG: Item exists check: {item_exists}")
            except Exception as e:
                print(f"DEBUG: Error checking if item exists: {str(e)}")
                item_exists = False

            # Update or create the item
            try:
                print(f"DEBUG: Executing DynamoDB update_item")

                # Build update expression
                update_expression = "SET #item_value = :val"
                expression_attribute_names = {
                    "#item_value": "value"}  # Use expression attribute name for reserved keyword
                expression_attribute_values = {":val": value}

                # Add user_id if provided
                if user_id:
                    update_expression += ", #uid = :uid"
                    expression_attribute_names["#uid"] = "user_id"
                    expression_attribute_values[":uid"] = user_id

                # Add label if provided
                if label:
                    update_expression += ", #label = :label"
                    expression_attribute_names["#label"] = "label"
                    expression_attribute_values[":label"] = label

                # Add GSI1 attributes if creating a new item
                if not item_exists:
                    update_expression += ", #gsi1pk = :gsi1pk, #gsi1sk = :gsi1sk, #entity = :entity, #created = :created"
                    expression_attribute_names.update({
                        "#gsi1pk": "GSI1PK",
                        "#gsi1sk": "GSI1SK",
                        "#entity": "entity_type",
                        "#created": "created_at"
                    })
                    expression_attribute_values.update({
                        ":gsi1pk": "IDENTIFICATION",
                        ":gsi1sk": f"USER#{user_id}#{item_id}" if user_id else f"GLOBAL#{item_id}",
                        ":entity": "IDENTIFICATION",
                        ":created": datetime.datetime.now().isoformat()
                    })

                # Always update the updated_at timestamp
                update_expression += ", #updated = :updated"
                expression_attribute_names["#updated"] = "updated_at"
                expression_attribute_values[":updated"] = datetime.datetime.now().isoformat()

                # Add attr and contacttype if not already set
                if not item_exists:
                    update_expression += ", #attr = :attr, #contacttype = :contacttype"
                    expression_attribute_names.update({
                        "#attr": "attr",
                        "#contacttype": "contacttype"
                    })
                    expression_attribute_values.update({
                        ":attr": attr,
                        ":contacttype": contacttype
                    })

                # Add state if not already set
                update_expression += ", #state = :state"
                expression_attribute_names["#state"] = "state"
                expression_attribute_values[":state"] = 1

                response = self.table.update_item(
                    Key={
                        'PK': "IDENTIFICATION",
                        'SK': item_id
                    },
                    UpdateExpression=update_expression,
                    ExpressionAttributeNames=expression_attribute_names,
                    ExpressionAttributeValues=expression_attribute_values,
                    ReturnValues="UPDATED_NEW"
                )
                print(f"DEBUG: DynamoDB response: {response}")
            except Exception as db_error:
                print(f"DEBUG: DynamoDB update_item exception: {str(db_error)}")
                raise db_error

            # Check if the update was successful
            if response and 'Attributes' in response:
                logger.info(f"Successfully updated identification: {attr} = {value}")
                print(f"DEBUG: Update successful, returning True")
                return True
            else:
                logger.error(f"Failed to update identification: {attr}")
                print(f"DEBUG: Update failed, returning False")
                return False
        except Exception as e:
            logger.error(f"Error updating identification {attr}: {str(e)}")
            print(f"DEBUG: Exception in update_identification: {str(e)}")
            return False

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def update_position_relationship(self, position_id, employer_id, startdate=None, user_id=None):
        """
        Update the GSI1 index for a position to maintain its relationship with an employer.

        :param str position_id: The position ID
        :param str employer_id: The employer ID
        :param str startdate: The position start date (used for sorting)
        :param str user_id: Optional user ID to associate with this position
        :return bool: True if successful, False otherwise
        """
        try:
            print(
                f"DEBUG: Updating position relationship: position={position_id}, employer={employer_id}, user_id={user_id}")

            # Create the update expression
            update_expression = "SET GSI1PK = :gsi1pk, GSI1SK = :gsi1sk"

            # Set the GSI1 values
            expression_attribute_values = {
                ":gsi1pk": f"EMPLOYER#{employer_id}",
                ":gsi1sk": startdate if startdate else position_id
            }

            # Add user_id if provided
            if user_id:
                update_expression += ", #uid = :uid"
                expression_attribute_names = {"#uid": "user_id"}
                expression_attribute_values[":uid"] = user_id
            else:
                expression_attribute_names = {}

            print(f"DEBUG: Update expression: {update_expression}")
            print(f"DEBUG: Expression attribute names: {expression_attribute_names}")
            print(f"DEBUG: Expression attribute values: {expression_attribute_values}")

            # Update the item
            response = self.table.update_item(
                Key={
                    'PK': 'POSITION',
                    'SK': position_id
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names if expression_attribute_names else None,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="UPDATED_NEW"
            )

            print(f"DEBUG: DynamoDB update response: {response}")

            return True
        except Exception as e:
            print(f"DEBUG: Error updating position relationship: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            return False

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def single_attr(self, table_key: str, row_id: str, attr: str, value, user_id=None) -> bool:
        """
        Update a single attribute in a DynamoDB record.

        :param str table_key: The entity type (replaces the table name concept)
        :param str row_id: ID of the record to update
        :param str attr: Attribute name to update
        :param value: New value for the attribute
        :param str user_id: Optional user ID to associate with this record
        :return bool: True if successful, False otherwise
        """
        try:
            print(
                f"DEBUG: single_attr called with table_key={table_key}, row_id={row_id}, attr={attr}, value={value}, user_id={user_id}")

            # Validate entity type to prevent injection
            valid_entities = ["IDENTIFICATION", "SUMMARY", "summary", "school", "focus", "employer", "position",
                              "achievement", "skill", "certification", "glossary", "standalone_achievement"]
            if table_key not in valid_entities:
                logger.error(f"Invalid entity type: {table_key}")
                return False

            # In DynamoDB, we use a composite primary key:
            # - PK: entity type (e.g., "SUMMARY", "SKILL")
            # - SK: ID value (e.g., "123")

            # Convert table_key for consistency
            pk_value = table_key
            if table_key.lower() == "summary":
                pk_value = "SUMMARY"
            elif table_key not in ["IDENTIFICATION", "SUMMARY"]:
                pk_value = table_key.upper()

            # Construct the update expression
            update_expression = f"SET #{attr} = :value"
            expression_attribute_names = {
                f"#{attr}": attr
            }
            expression_attribute_values = {
                ":value": value
            }

            # Add user_id if provided
            if user_id and attr != "user_id":
                update_expression += ", #uid = :uid"
                expression_attribute_names["#uid"] = "user_id"
                expression_attribute_values[":uid"] = user_id

            # Update the item
            response = self.table.update_item(
                Key={
                    'PK': pk_value,
                    'SK': str(row_id)
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="UPDATED_NEW"
            )

            print(f"DEBUG: DynamoDB update response: {response}")

            return True
        except ClientError as e:
            logger.error(f"Error updating {attr} in {table_key} (ID {row_id}): {str(e)}")
            return False
        except Exception as e:
            print(f"DEBUG: Unexpected error in single_attr: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            return False

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def multi_column(self, table_key: str, record_id: str, user_id=None, **kwargs) -> bool:
        """
        Update multiple attributes at once for a specific record.

        :param str table_key: Entity type (replaces table name concept)
        :param str record_id: ID of the record to update
        :param str user_id: Optional user ID to associate with this record
        :param kwargs: Attribute names and values to update
        :return bool: True if successful, False otherwise
        """
        try:
            print(
                f"DEBUG: DynamoUpdates.multi_column called with table_key={table_key}, record_id={record_id}, user_id={user_id}")
            print(f"DEBUG: Update data: {kwargs}")

            # Validate entity type
            valid_entities = ["IDENTIFICATION", "SUMMARY", "summary", "school", "focus", "employer", "position",
                              "achievement", "skill", "certification", "glossary", "standalone_achievement"]
            if table_key not in valid_entities:
                print(f"DEBUG: Invalid entity type: {table_key}")
                logger.error(f"Invalid entity type: {table_key}")
                return False

            if not kwargs and not user_id:
                print(f"DEBUG: No attributes to update for {table_key} with ID {record_id}")
                logger.warning(f"No attributes to update for {table_key} with ID {record_id}")
                return False

            # Convert table_key for consistency
            pk_value = table_key
            if table_key.lower() == "summary":
                pk_value = "SUMMARY"
            elif table_key not in ["IDENTIFICATION", "SUMMARY"]:
                pk_value = table_key.upper()

            print(f"DEBUG: Using PK={pk_value}, SK={record_id}")

            # Build update expression and values
            update_parts = []
            expression_attribute_names = {}
            expression_attribute_values = {}

            # Add user_id if provided and not already in kwargs
            if user_id and "user_id" not in kwargs:
                update_parts.append("#uid = :uid")
                expression_attribute_names["#uid"] = "user_id"
                expression_attribute_values[":uid"] = user_id

            for key, value in kwargs.items():
                if value is None:
                    # Skip null values as they can't be directly set in DynamoDB
                    continue
                else:
                    # Add to SET expression
                    attr_name = f"#{key.replace('.', '_')}"
                    attr_value = f":{key.replace('.', '_')}"
                    update_parts.append(f"{attr_name} = {attr_value}")
                    expression_attribute_names[attr_name] = key
                    expression_attribute_values[attr_value] = value

            # If no attributes to update, return early
            if not update_parts:
                print(f"DEBUG: No valid attributes to update for {table_key} with ID {record_id}")
                return False

            # Construct the final update expression
            update_expression = "SET " + ", ".join(update_parts)
            print(f"DEBUG: Update expression: {update_expression}")
            print(f"DEBUG: Expression attribute names: {expression_attribute_names}")
            print(f"DEBUG: Expression attribute values: {expression_attribute_values}")

            # Execute the update
            response = self.table.update_item(
                Key={
                    'PK': pk_value,
                    'SK': str(record_id)
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="UPDATED_NEW"
            )

            print(f"DEBUG: DynamoDB update response: {response}")
            return True
        except ClientError as e:
            print(f"DEBUG: DynamoDB ClientError: {str(e)}")
            logger.error(f"Error updating {table_key} record {record_id}: {str(e)}")
            return False
        except Exception as e:
            print(f"DEBUG: Unexpected error in multi_column: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            return False

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def set_state(self, table_key: str, record_id: str, active: bool, user_id=None) -> bool:
        """
        Set the state of a record (active or inactive).

        :param str table_key: Entity type
        :param str record_id: ID of the record to update
        :param bool active: True for active, False for inactive
        :param str user_id: Optional user ID to associate with this record
        :return bool: True if successful, False otherwise
        """
        try:
            print(
                f"DEBUG: set_state called with table_key={table_key}, record_id={record_id}, active={active}, user_id={user_id}")

            # Validate entity type
            valid_entities = ["IDENTIFICATION", "SUMMARY", "summary", "school", "focus", "employer", "position",
                              "achievement", "skill", "certification", "glossary", "standalone_achievement"]
            if table_key not in valid_entities:
                print(f"DEBUG: Invalid entity type: {table_key}")
                logger.error(f"Invalid entity type: {table_key}")
                return False

            # Convert table_key for consistency
            pk_value = table_key
            if table_key.lower() == "summary":
                pk_value = "SUMMARY"
            elif table_key not in ["IDENTIFICATION", "SUMMARY"]:
                pk_value = table_key.upper()

            # Build update expression
            update_expression = "SET #state = :state"
            expression_attribute_names = {"#state": "state"}
            expression_attribute_values = {":state": 1 if active else 0}

            # Add user_id if provided
            if user_id:
                update_expression += ", #uid = :uid"
                expression_attribute_names["#uid"] = "user_id"
                expression_attribute_values[":uid"] = user_id

            # Execute the update
            response = self.table.update_item(
                Key={
                    'PK': pk_value,
                    'SK': str(record_id)
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="UPDATED_NEW"
            )

            print(f"DEBUG: DynamoDB update response: {response}")
            return True
        except ClientError as e:
            print(f"DEBUG: DynamoDB ClientError: {str(e)}")
            logger.error(f"Error setting state for {table_key} record {record_id}: {str(e)}")
            return False
        except Exception as e:
            print(f"DEBUG: Unexpected error in set_state: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            return False