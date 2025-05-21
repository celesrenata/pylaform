import boto3
import os
import logging
from botocore.exceptions import ClientError
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Get table name from environment or use default
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'pylaform-data')


def db():
    """
    Connect to DynamoDB and return the table resource.
    Also ensures the DynamoDB table exists.

    :return: boto3.resource.Table for DynamoDB
    """
    try:
        # Check if running in Lambda environment
        if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            # When running in Lambda, use the AWS SDK without specific credentials
            dynamodb = boto3.resource('dynamodb')
        else:
            # For local development, use credentials and specify endpoint if provided
            endpoint_url = os.environ.get('DYNAMODB_ENDPOINT_URL')
            if endpoint_url:
                dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
            else:
                dynamodb = boto3.resource('dynamodb')

        # Get or create the table
        table = ensure_table_exists(dynamodb)

        # Verify initialization after table creation
        verify_initialization(table)

        return table
    except Exception as e:
        logger.error(f"Error connecting to DynamoDB: {str(e)}")
        raise


def verify_initialization(table):
    """
    Verify that all identification records were properly initialized

    :param table: The DynamoDB table resource
    """
    try:
        # Query all identification records
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('PK').eq("IDENTIFICATION")
        )

        items = response.get('Items', [])
        found_attrs = [item.get('attr') for item in items]

        logger.info(f"Found {len(items)} identification records: {found_attrs}")

        # Check for missing records
        expected_attrs = ['name', 'email', 'phone', 'location', 'www', 'github']
        missing = [attr for attr in expected_attrs if attr not in found_attrs]

        if missing:
            logger.warning(f"Missing identification records: {missing}")
            # If records are missing, initialize them
            logger.info("Initializing missing identification records...")
            initialize_missing_records(table, missing)
        else:
            logger.info("All identification records successfully verified")

    except ClientError as e:
        logger.error(f"Error verifying initialization: {str(e)}")


def initialize_missing_records(table, missing_attrs):
    """
    Initialize only the missing identification records

    :param table: The DynamoDB table resource
    :param missing_attrs: List of missing attribute names
    """
    try:
        # Define the default values for all possible records
        default_values = {
            "name": {"value": "Your Name", "contacttype": "name", "state": 1},
            "email": {"value": "your.email@example.com", "contacttype": "email", "state": 1},
            "phone": {"value": "555-123-4567", "contacttype": "phone", "state": 1},
            "location": {"value": "City, State", "contacttype": "location", "state": 1},
            "www": {"value": "example.com", "contacttype": "www", "state": 1},
            "github": {"value": "github.com/yourusername", "contacttype": "github", "state": 1}
        }

        # Only initialize the missing ones
        for attr in missing_attrs:
            if attr in default_values:
                item = {"attr": attr, **default_values[attr]}

                # Create a unique ID for the identification item
                item_id = f"{attr}-{item['contacttype']}"

                # Add required keys for DynamoDB
                full_item = {
                    'PK': 'IDENTIFICATION',
                    'SK': item_id,
                    **item
                }

                table.put_item(Item=full_item)
                logger.info(f"Created missing identification item: {attr}")

    except ClientError as e:
        logger.error(f"Error initializing missing records: {str(e)}")


def ensure_table_exists(dynamodb):
    """
    Ensure the DynamoDB table exists with the correct schema.
    Added User and Session management attributes
    """
    try:
        print(f"DEBUG: Ensuring table {TABLE_NAME} exists")
        table = dynamodb.Table(TABLE_NAME)
        table.load()
        print(f"DEBUG: Successfully connected to existing DynamoDB table: {TABLE_NAME}")
        return table

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"DEBUG: Table {TABLE_NAME} doesn't exist, creating...")

            table = dynamodb.create_table(
                TableName=TABLE_NAME,
                KeySchema=[
                    {'AttributeName': 'PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'PK', 'AttributeType': 'S'},
                    {'AttributeName': 'SK', 'AttributeType': 'S'},
                    {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
                    {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
                    {'AttributeName': 'email', 'AttributeType': 'S'},
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'GSI1',
                        'KeySchema': [
                            {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                            {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    },
                    {
                        'IndexName': 'EmailIndex',
                        'KeySchema': [
                            {'AttributeName': 'email', 'KeyType': 'HASH'}
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    },
                    {
                        'IndexName': 'UserIndex',
                        'KeySchema': [
                            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                            {'AttributeName': 'PK', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                BillingMode='PROVISIONED',
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )

            # Wait for the table to be created
            print(f"DEBUG: Waiting for table {TABLE_NAME} to be created...")
            table.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)
            print(f"DEBUG: Table {TABLE_NAME} created successfully")
            return table
        else:
            print(f"DEBUG: Error creating table: {str(e)}")
            raise


def initialize_default_data(table):
    """
    Initialize default data in the DynamoDB table

    :param table: The DynamoDB table resource
    """
    try:
        # Insert default identification records
        default_identification = [
            {"attr": "name", "value": "Your Name", "contacttype": "name", "state": 1},
            {"attr": "email", "value": "your.email@example.com", "contacttype": "email", "state": 1},
            {"attr": "phone", "value": "555-123-4567", "contacttype": "phone", "state": 1},
            {"attr": "location", "value": "City, State", "contacttype": "location", "state": 1},
            {"attr": "www", "value": "example.com", "contacttype": "www", "state": 1},
            {"attr": "github", "value": "github.com/yourusername", "contacttype": "github", "state": 1}
        ]

        for item in default_identification:
            # Create a unique ID for each identification item
            item_id = f"{item['attr']}-{item['contacttype']}"

            # Add required keys for DynamoDB
            full_item = {
                'PK': 'IDENTIFICATION',
                'SK': item_id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                **item
            }

            table.put_item(Item=full_item)
            logger.info(f"Created default identification item: {item['attr']}")

        # Create a default admin user if none exists
        create_default_admin_user(table)

    except ClientError as e:
        logger.error(f"Error initializing default data: {str(e)}")
        raise


def create_default_admin_user(table):
    """
    Create a default admin user if no users exist in the system.
    This is useful for initial setup.

    :param table: The DynamoDB table resource
    """
    try:
        # Check if any users exist
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('PK').eq("USER")
        )

        if not response.get('Items'):
            # No users exist, create a default admin
            admin_id = str(uuid.uuid4())

            # You would normally hash this password, but for initial setup we'll use a placeholder
            # In a real application, you should use a proper password hashing library
            admin_user = {
                'PK': 'USER',
                'SK': admin_id,
                'user_id': admin_id,
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'password': 'CHANGE_THIS_PASSWORD',  # This should be hashed in production
                'role': 'admin',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'state': 1
            }

            table.put_item(Item=admin_user)
            logger.info(f"Created default admin user with ID: {admin_id}")
            print(f"DEBUG: Created default admin user with ID: {admin_id}")
            print(f"DEBUG: Default admin credentials: admin@example.com / CHANGE_THIS_PASSWORD")

            # Create personal identification records for this admin
            create_user_identification(table, admin_id)

    except ClientError as e:
        logger.error(f"Error creating default admin user: {str(e)}")
        print(f"DEBUG: Error creating default admin user: {str(e)}")


def create_user_identification(table, user_id):
    """
    Create personal identification records for a new user

    :param table: The DynamoDB table resource
    :param user_id: The user ID to associate with the identification records
    """
    try:
        # Default identification records for a new user
        default_identification = [
            {"attr": "name", "label": "Name", "value": "New User", "contacttype": "name", "state": 1},
            {"attr": "email", "label": "Email", "value": "user@example.com", "contacttype": "email", "state": 1},
            {"attr": "phone", "label": "Phone", "value": "555-123-4567", "contacttype": "phone", "state": 1},
            {"attr": "location", "label": "Location", "value": "City, State", "contacttype": "location", "state": 1},
            {"attr": "www", "label": "Website", "value": "example.com", "contacttype": "www", "state": 1},
            {"attr": "github", "label": "GitHub", "value": "github.com/username", "contacttype": "github", "state": 1}
        ]

        for item in default_identification:
            # Create a unique ID for each identification item
            item_id = f"{item['attr']}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Add required keys for DynamoDB
            full_item = {
                'PK': f"USER#{user_id}",
                'SK': f"IDENTIFICATION#{item_id}",
                'GSI1PK': "IDENTIFICATION",
                'GSI1SK': f"USER#{user_id}#{item_id}",
                'user_id': user_id,
                'entity_type': "IDENTIFICATION",
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                **item
            }

            table.put_item(Item=full_item)
            logger.info(f"Created user identification item: {item['attr']} for user {user_id}")

        return True
    except Exception as e:
        logger.error(f"Error creating user identification records: {str(e)}")
        print(f"DEBUG: Error creating user identification records: {str(e)}")
        return False