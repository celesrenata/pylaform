import boto3
from boto3.dynamodb.conditions import Key, Attr
import logging
from tenacity import retry, stop_after_delay, wait_exponential
from pylaform.database.connect import db
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)


class DynamoQueries:
    """
    Handle all DynamoDB query operations with proper error handling.
    Includes caching for query results to improve performance.
    """

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def __init__(self, table=None):
        """
        Initialize the DynamoDB connection.

        :param table: Optional DynamoDB table object
        """
        # Use provided table or get from connect.py
        self.table = table if table is not None else db()

        # Cache dictionary to store query results
        self.cache = {}

    def get_identification(self, user_id=None):
        """
        Get all identification records for a user.

        :param user_id: Optional user ID, defaults to current user
        :return: List of identification records
        """
        try:
            if not user_id and hasattr(self, 'user_id'):
                user_id = self.user_id

            if not user_id:
                logger.warning("No user_id available for get_identification")
                return []

            # Check cache first
            cache_key = f"identification_{user_id}"
            if cache_key in self.cache:
                logger.debug(f"Using cached identification data for user {user_id}")
                return self.cache[cache_key]

            logger.debug(f"Fetching identification data for user {user_id}")

            # Try multiple query approaches
            items = []

            # Approach 1: Direct query based on logs
            try:
                logger.debug("Trying direct query for IDENTIFICATION")
                response = self.table.scan(
                    FilterExpression=
                    Attr('PK').eq("IDENTIFICATION") &
                    Attr('user_id').eq(user_id)
                )
                items = response.get('Items', [])
                logger.debug(f"Direct query returned {len(items)} items")

                # If we got items, print the first one for debugging
                if items:
                    logger.debug(f"Sample item: {items[0]}")
            except Exception as e:
                logger.error(f"Error in direct query: {str(e)}")

            # Approach 2: Try with SK pattern from logs
            if not items:
                try:
                    logger.debug("Trying SK pattern query for IDENTIFICATION")
                    response = self.table.scan(
                        FilterExpression=
                        Attr('SK').begins_with("IDENTIFICATION#") &
                        Attr('user_id').eq(user_id)
                    )
                    items = response.get('Items', [])
                    logger.debug(f"SK pattern query returned {len(items)} items")
                except Exception as e:
                    logger.error(f"Error in SK pattern query: {str(e)}")

            # Approach 3: Try GSI1 query
            if not items:
                try:
                    logger.debug("Trying GSI1 query for IDENTIFICATION")
                    response = self.table.query(
                        IndexName='GSI1',
                        KeyConditionExpression=Key('GSI1PK').eq("IDENTIFICATION") &
                                               Key('GSI1SK').begins_with(f"USER#{user_id}#")
                    )
                    items = response.get('Items', [])
                    logger.debug(f"GSI1 query returned {len(items)} items")
                except Exception as e:
                    logger.error(f"Error in GSI1 query: {str(e)}")

            # Approach 4: Try entity_type scan
            if not items:
                try:
                    logger.debug("Trying entity_type scan for IDENTIFICATION")
                    response = self.table.scan(
                        FilterExpression=
                        Attr('entity_type').eq("IDENTIFICATION") &
                        Attr('user_id').eq(user_id)
                    )
                    items = response.get('Items', [])
                    logger.debug(f"Entity type scan returned {len(items)} items")
                except Exception as e:
                    logger.error(f"Error in entity_type scan: {str(e)}")

            # Cache the results
            self.cache[cache_key] = items
            logger.debug(f"Cached {len(items)} identification items for user {user_id}")

            return items
        except Exception as e:
            logger.error(f"Error in get_identification: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def purge_cache(self, entity_type=None):
        """
        Clear the query cache, either for a specific entity type or all.

        :param str entity_type: Optional entity type to clear cache for
        """
        try:
            if entity_type:
                # Clear cache for specific entity type
                keys_to_remove = [k for k in self.cache.keys() if k.startswith(entity_type)]
                for key in keys_to_remove:
                    del self.cache[key]
                logger.debug(f"Purged cache for {entity_type}")
            else:
                # Clear all cache
                self.cache.clear()
                logger.debug("Purged all cache")
        except Exception as e:
            logger.error(f"Error purging cache: {str(e)}")
            print(f"DEBUG: Error in purge_cache: {str(e)}")

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def get_all(self, entity_type, active_only=True, user_id=None):
        """
        Get all items of a specific entity type.

        :param entity_type: Type of entity to query
        :param active_only: If True, only return active items
        :param user_id: Optional user ID to filter by
        :return: List of items
        """
        try:
            # Convert entity_type to uppercase for consistency
            entity_type_upper = entity_type.upper()

            # Check cache first
            cache_key = f"{entity_type}_all_{active_only}_{user_id}"
            if cache_key in self.cache:
                return self.cache[cache_key]

            # Query using GSI1 with uppercase entity type
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression=Key('GSI1PK').eq(entity_type_upper)
            )

            items = response.get('Items', [])

            # Filter by active state if requested
            if active_only:
                items = [item for item in items if item.get('state', 0) == 1]

            # Filter by user_id if provided
            if user_id:
                items = [item for item in items if item.get('user_id') == user_id]

            # Cache the results
            self.cache[cache_key] = items

            return items
        except Exception as e:
            logger.error(f"Error in get_all: {str(e)}")
            print(f"DEBUG: Error in get_all: {str(e)}")
            return []

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def get_by_id(self, entity_type, record_id, user_id=None):
        """
        Get a specific record by its ID.

        :param str entity_type: The entity type to query
        :param str record_id: The record ID to retrieve
        :param str user_id: Optional user ID to filter records
        :return: The record if found, None otherwise
        """
        try:
            # Convert entity_type to uppercase for consistency
            entity_type_upper = entity_type.upper()

            # Cache key includes user_id
            cache_key = f"{entity_type}_{record_id}_{user_id if user_id else 'global'}"

            # Check cache first
            if cache_key in self.cache:
                logger.debug(f"Using cached data for {cache_key}")
                return self.cache[cache_key]

            # Build the query based on whether we're filtering by user_id
            if user_id:
                # For user-specific data
                if entity_type_upper == "IDENTIFICATION":
                    pk = f"USER#{user_id}#IDENTIFICATION"
                else:
                    pk = f"USER#{user_id}#{entity_type_upper}"
            else:
                # For global data
                pk = entity_type_upper

            response = self.table.get_item(
                Key={
                    'PK': pk,
                    'SK': record_id
                }
            )

            item = response.get('Item')

            # If user-specific query returned no results, try falling back to global data
            if user_id and not item and entity_type_upper != "USER":
                logger.info(f"No user-specific {entity_type_upper} {record_id} found for {user_id}, trying global")
                return self.get_by_id(entity_type, record_id, None)

            # Store in cache
            self.cache[cache_key] = item

            return item
        except Exception as e:
            logger.error(f"Error getting {entity_type} {record_id}: {str(e)}")
            return None

    def get_by_user(self, entity_type: str, user_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all items of a specific entity type for a specific user.

        :param entity_type: The type of entity to query (e.g., "IDENTIFICATION")
        :param user_id: The user ID to filter by
        :param active_only: If True, only return active entries
        :return: List of items belonging to the user
        """
        try:
            if not user_id:
                logger.warning(f"No user_id provided for get_by_user({entity_type})")
                return []

            # Check cache first
            cache_key = f"{entity_type.lower()}_{user_id}"
            if cache_key in self.cache:
                items = self.cache[cache_key]
                logger.debug(f"Using cached data for {cache_key}: {len(items)} items")
                if active_only:
                    return [item for item in items if item.get('state', 0) == 1]
                return items

            # Ensure entity_type is uppercase for consistency
            entity_type_upper = entity_type.upper()
            logger.debug(f"Querying for {entity_type_upper} items for user {user_id}")

            # Try multiple query approaches
            items = []

            # Special handling for IDENTIFICATION
            if entity_type_upper == "IDENTIFICATION":
                # Try direct query first - this is how the data appears to be stored based on logs
                try:
                    logger.debug(f"Trying direct query for IDENTIFICATION with PK=IDENTIFICATION")
                    # Query all items with PK=IDENTIFICATION
                    response = self.table.scan(
                        FilterExpression=
                        Attr('PK').eq("IDENTIFICATION") &
                        Attr('user_id').eq(user_id)
                    )
                    items = response.get('Items', [])
                    logger.debug(f"Direct query returned {len(items)} items")
                except Exception as e:
                    logger.error(f"Error in direct query: {str(e)}")

                # If no items found, try with the SK pattern from the logs
                if not items:
                    try:
                        logger.debug(f"Trying SK pattern query for IDENTIFICATION")
                        # The logs show SK values like "IDENTIFICATION#name-20250518171444"
                        response = self.table.scan(
                            FilterExpression=
                            Attr('SK').begins_with("IDENTIFICATION#") &
                            Attr('user_id').eq(user_id)
                        )
                        items = response.get('Items', [])
                        logger.debug(f"SK pattern query returned {len(items)} items")
                    except Exception as e:
                        logger.error(f"Error in SK pattern query: {str(e)}")
            else:
                # Standard approach for non-identification entities
                # Approach 1: Query using GSI1
                try:
                    logger.debug(f"Trying GSI1 query for {entity_type_upper} and user {user_id}")
                    response = self.table.query(
                        IndexName='GSI1',
                        KeyConditionExpression=Key('GSI1PK').eq(entity_type_upper) &
                                               Key('GSI1SK').begins_with(f"USER#{user_id}#")
                    )

                    items = response.get('Items', [])
                    logger.debug(f"GSI1 query returned {len(items)} items")
                except Exception as e:
                    logger.error(f"Error in GSI1 query: {str(e)}")

            # Common fallback approaches if no items found
            if not items:
                # Approach 2: Try direct scan with user_id attribute
                try:
                    logger.debug(f"Trying scan for {entity_type_upper} with user_id={user_id}")
                    response = self.table.scan(
                        FilterExpression=
                        Attr('PK').eq(entity_type_upper) &
                        Attr('user_id').eq(user_id)
                    )
                    items = response.get('Items', [])
                    logger.debug(f"Scan returned {len(items)} items")
                except Exception as e:
                    logger.error(f"Error in scan: {str(e)}")

                # Approach 3: Try another scan pattern if still no items
                if not items:
                    try:
                        logger.debug(f"Trying alternative scan for {entity_type_upper}")
                        response = self.table.scan(
                            FilterExpression=
                            Attr('entity_type').eq(entity_type_upper) &
                            Attr('user_id').eq(user_id)
                        )
                        items = response.get('Items', [])
                        logger.debug(f"Alternative scan returned {len(items)} items")
                    except Exception as e:
                        logger.error(f"Error in alternative scan: {str(e)}")

            # Cache the results
            self.cache[cache_key] = items
            logger.debug(f"Cached {len(items)} items for {cache_key}")

            # Filter by state if needed
            if active_only:
                filtered_items = [item for item in items if item.get('state', 0) == 1]
                logger.debug(f"Filtered to {len(filtered_items)} active items")
                return filtered_items

            return items
        except Exception as e:
            logger.error(f"Error in get_by_user({entity_type}, {user_id}): {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def get_related_items(self, parent_type, parent_id, child_type, active_only=True, user_id=None):
        """
        Get items related to a parent item.

        :param str parent_type: The parent entity type
        :param str parent_id: The parent record ID
        :param str child_type: The child entity type to retrieve
        :param bool active_only: If True, only return active records
        :param str user_id: Optional user ID to filter records
        :return: List of related items
        """
        try:
            # Convert entity types to uppercase for consistency
            parent_type_upper = parent_type.upper()
            child_type_upper = child_type.upper()

            # Cache key includes user_id and active_only flag
            cache_key = f"{parent_type}_{parent_id}_{child_type}_{active_only}_{user_id if user_id else 'global'}"

            # Check cache first
            if cache_key in self.cache:
                logger.debug(f"Using cached data for {cache_key}")
                return self.cache[cache_key]

            # Build the query based on whether we're filtering by user_id
            if user_id:
                # For user-specific data
                if parent_type_upper == "IDENTIFICATION":
                    pk = f"USER#{user_id}#IDENTIFICATION"
                else:
                    pk = f"USER#{user_id}#{parent_type_upper}"
            else:
                # For global data
                pk = parent_type_upper

            # Build the relationship key
            relationship_key = f"{pk}#{parent_id}#{child_type_upper}"

            # Build filter expression for active records if needed
            if active_only:
                response = self.table.query(
                    KeyConditionExpression="PK = :pk",
                    FilterExpression="attribute_not_exists(state) OR state = :active",
                    ExpressionAttributeValues={
                        ":pk": relationship_key,
                        ":active": 1
                    }
                )
            else:
                response = self.table.query(
                    KeyConditionExpression="PK = :pk",
                    ExpressionAttributeValues={
                        ":pk": relationship_key
                    }
                )

            items = response.get('Items', [])

            # If user-specific query returned no results, try falling back to global data
            if user_id and not items:
                logger.info(
                    f"No user-specific related items found for {parent_type_upper} {parent_id} -> {child_type_upper}, trying global")
                return self.get_related_items(parent_type, parent_id, child_type, active_only, None)

            # Store in cache
            self.cache[cache_key] = items

            return items
        except Exception as e:
            logger.error(f"Error getting related items for {parent_type} {parent_id} -> {child_type}: {str(e)}")
            return []

    # Add this method if it doesn't exist
    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def get_by_attribute(self, entity_type: str, attr_name: str, attr_value: Any, active_only: bool = True,
                         user_id: str = None) -> List[Dict[str, Any]]:
        """
        Get items by a specific attribute value.

        :param entity_type: Type of entity to query (e.g., "IDENTIFICATION", "SKILL")
        :param attr_name: Attribute name to filter by (e.g., "contacttype", "category")
        :param attr_value: Attribute value to match
        :param active_only: If True, only return active items
        :param user_id: Optional user ID to filter by
        :return: List of matching items
        """
        try:
            # Create cache key
            cache_key = f"{entity_type}_{attr_name}_{attr_value}_{active_only}_{user_id if user_id else 'global'}"

            # Check cache first
            if cache_key in self.cache:
                logger.debug(f"Using cached data for {cache_key}")
                return self.cache[cache_key]

            # Ensure entity_type is uppercase for consistency
            entity_type_upper = entity_type.upper()
            logger.debug(f"Querying {entity_type_upper} items where {attr_name}={attr_value}")

            # Try multiple query approaches
            items = []

            # Approach 1: Try GSI1 query with filter
            try:
                logger.debug(f"Trying GSI1 query with filter for {attr_name}={attr_value}")

                # Build filter expression
                filter_expression = Attr(attr_name).eq(attr_value)

                # Add user_id filter if provided
                if user_id:
                    filter_expression = filter_expression & Attr('user_id').eq(user_id)

                # Add active state filter if requested
                if active_only:
                    filter_expression = filter_expression & (Attr('state').eq(1) | Attr('state').not_exists())

                # Query using GSI1 for the entity type
                response = self.table.query(
                    IndexName='GSI1',
                    KeyConditionExpression=Key('GSI1PK').eq(entity_type_upper),
                    FilterExpression=filter_expression
                )

                items = response.get('Items', [])
                logger.debug(f"GSI1 query returned {len(items)} items")
            except Exception as e:
                logger.error(f"Error in GSI1 query: {str(e)}")

            # Approach 2: If no items found, try direct scan
            if not items:
                try:
                    logger.debug(f"Trying direct scan for {entity_type_upper} where {attr_name}={attr_value}")

                    # Build filter expression
                    filter_expression = Attr('PK').eq(entity_type_upper) & Attr(attr_name).eq(attr_value)

                    # Add user_id filter if provided
                    if user_id:
                        filter_expression = filter_expression & Attr('user_id').eq(user_id)

                    # Add active state filter if requested
                    if active_only:
                        filter_expression = filter_expression & (Attr('state').eq(1) | Attr('state').not_exists())

                    # Execute scan
                    response = self.table.scan(FilterExpression=filter_expression)
                    items = response.get('Items', [])
                    logger.debug(f"Direct scan returned {len(items)} items")
                except Exception as e:
                    logger.error(f"Error in direct scan: {str(e)}")

            # Approach 3: Try entity_type attribute scan
            if not items:
                try:
                    logger.debug(f"Trying entity_type scan for {entity_type_upper} where {attr_name}={attr_value}")

                    # Build filter expression
                    filter_expression = Attr('entity_type').eq(entity_type_upper) & Attr(attr_name).eq(attr_value)

                    # Add user_id filter if provided
                    if user_id:
                        filter_expression = filter_expression & Attr('user_id').eq(user_id)

                    # Add active state filter if requested
                    if active_only:
                        filter_expression = filter_expression & (Attr('state').eq(1) | Attr('state').not_exists())

                    # Execute scan
                    response = self.table.scan(FilterExpression=filter_expression)
                    items = response.get('Items', [])
                    logger.debug(f"Entity type scan returned {len(items)} items")
                except Exception as e:
                    logger.error(f"Error in entity_type scan: {str(e)}")

            # Cache the results
            self.cache[cache_key] = items
            logger.debug(f"Cached {len(items)} items for {cache_key}")

            return items
        except Exception as e:
            logger.error(f"Error in get_by_attribute({entity_type}, {attr_name}, {attr_value}): {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def get_positions_by_employer(self, employer_id, active_only=True, user_id=None):
        """
        Get positions related to a specific employer.

        :param str employer_id: The employer ID to filter by
        :param bool active_only: If True, only return active records
        :param str user_id: Optional user ID to filter records
        :return: List of matching position records
        """
        try:
            # This is a specialized version of get_by_attribute
            return self.get_by_attribute("POSITION", "employer_id", employer_id, active_only, user_id)
        except Exception as e:
            logger.error(f"Error getting positions for employer {employer_id}: {str(e)}")
            return []

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def get_achievements_by_position(self, position_id, active_only=True, user_id=None):
        """
        Get achievements related to a specific position.

        :param str position_id: The position ID to filter by
        :param bool active_only: If True, only return active records
        :param str user_id: Optional user ID to filter records
        :return: List of matching achievement records
        """
        try:
            # This is a specialized version of get_by_attribute
            return self.get_by_attribute("ACHIEVEMENT", "position_id", position_id, active_only, user_id)
        except Exception as e:
            logger.error(f"Error getting achievements for position {position_id}: {str(e)}")
            return []

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def get_standalone_achievements(self, active_only=True, user_id=None):
        """
        Get standalone achievements (not associated with a position).

        :param bool active_only: If True, only return active records
        :param str user_id: Optional user ID to filter records
        :return: List of standalone achievement records
        """
        try:
            # Cache key includes parameters
            cache_key = f"standalone_achievements_{active_only}_{user_id if user_id else 'global'}"

            # Check cache first
            if cache_key in self.cache:
                logger.debug(f"Using cached data for {cache_key}")
                return self.cache[cache_key]

            # Get all achievements
            all_achievements = self.get_all("ACHIEVEMENT", active_only, user_id)

            # Filter for standalone achievements (those without a position_id)
            standalone = [a for a in all_achievements if not a.get('position_id')]

            # Store in cache
            self.cache[cache_key] = standalone

            return standalone
        except Exception as e:
            logger.error(f"Error getting standalone achievements: {str(e)}")
            return []

    @retry(stop=stop_after_delay(10), wait=wait_exponential(multiplier=1, min=1, max=3))
    def search_items(self, entity_type, search_term, search_fields=None, active_only=True, user_id=None):
        """
        Search for items containing a specific term in specified fields.

        :param str entity_type: The entity type to search
        :param str search_term: The term to search for
        :param list search_fields: List of fields to search in (if None, search all text fields)
        :param bool active_only: If True, only search active records
        :param str user_id: Optional user ID to filter records
        :return: List of matching records
        """
        try:
            # Normalize search term
            search_term = search_term.lower()

            # Get all items of this type
            all_items = self.get_all(entity_type, active_only, user_id)

            # If no search fields specified, use common text fields
            if not search_fields:
                search_fields = ['name', 'title', 'description', 'content', 'value']

            # Filter items that contain the search term in any of the specified fields
            results = []
            for item in all_items:
                for field in search_fields:
                    if field in item and isinstance(item[field], str) and search_term in item[field].lower():
                        results.append(item)
                        break  # Once we've matched an item, no need to check other fields

            return results
        except Exception as e:
            logger.error(f"Error searching {entity_type} for '{search_term}': {str(e)}")
            return []

    def get_user_items(self, entity_type: str, user_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all items of a specific type for a specific user.

        :param entity_type: Type of entity to query
        :param user_id: User ID to filter by
        :param active_only: If True, only return active items
        :return: List of matching items
        """
        try:
            # Create cache key
            cache_key = f"{entity_type}_user_{user_id}"
            if cache_key in self.cache:
                return self.cache[cache_key]

            # Build filter expression for user_id
            filter_expression = Attr('user_id').eq(user_id)

            if active_only:
                filter_expression = filter_expression & Attr('state').eq(1)

            # Query using GSI1 for the entity type
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression=Key('GSI1PK').eq(entity_type.upper()),
                FilterExpression=filter_expression
            )

            items = response.get('Items', [])

            # Cache the results
            self.cache[cache_key] = items

            return items
        except Exception as e:
            logger.error(f"Error in get_user_items: {str(e)}")
            return []