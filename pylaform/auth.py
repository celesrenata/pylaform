import secrets
import time
import logging
import re
import os
import json
import bcrypt
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import boto3
from botocore.exceptions import ClientError
from functools import wraps
from flask import session, redirect, url_for, request

logger = logging.getLogger(__name__)


def store_reset_token(table, user_id, token, expiration):
    """
    Store a password reset token in the database.

    :param table: DynamoDB table object
    :param user_id: User ID
    :param token: Reset token
    :param expiration: Token expiration timestamp
    :return: True if successful, False otherwise
    """
    try:
        table.put_item(
            Item={
                'PK': f"TOKEN#{token}",
                'SK': 'RESET',
                'user_id': user_id,
                'expiration': expiration,
                'created_at': int(time.time())
            }
        )
        return True
    except Exception as e:
        logger.exception(f"Error storing reset token: {str(e)}")
        return False


def verify_reset_token(table, token):
    """
    Verify if a reset token is valid and not expired.

    :param table: DynamoDB table object
    :param token: Reset token to verify
    :return: Token data if valid, None otherwise
    """
    try:
        response = table.get_item(
            Key={
                'PK': f"TOKEN#{token}",
                'SK': 'RESET'
            }
        )

        if 'Item' not in response:
            return None

        token_data = response['Item']
        current_time = int(time.time())

        # Check if token is expired
        if token_data.get('expiration', 0) < current_time:
            return None

        return token_data
    except Exception as e:
        logger.exception(f"Error verifying reset token: {str(e)}")
        return None


def update_user_password(table, user_id, new_password):
    """
    Update a user's password.

    :param table: DynamoDB table object
    :param user_id: User ID
    :param new_password: New password (plaintext)
    :return: True if successful, False otherwise
    """
    try:
        # Hash the new password
        from werkzeug.security import generate_password_hash
        hashed_password = generate_password_hash(new_password)

        # Update the user's password in the database
        table.update_item(
            Key={
                'PK': user_id,
                'SK': 'PROFILE'
            },
            UpdateExpression="set password = :p, updated_at = :t",
            ExpressionAttributeValues={
                ':p': hashed_password,
                ':t': int(time.time())
            }
        )
        return True
    except Exception as e:
        logger.exception(f"Error updating user password: {str(e)}")
        return False


def invalidate_all_sessions(table, user_id):
    """
    Invalidate all sessions for a user.

    :param table: DynamoDB table object
    :param user_id: User ID
    :return: True if successful, False otherwise
    """
    try:
        # Query all sessions for this user
        response = table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
            ExpressionAttributeValues={
                ':pk': user_id,
                ':sk': 'SESSION#'
            }
        )

        # Delete each session
        for item in response.get('Items', []):
            table.delete_item(
                Key={
                    'PK': item['PK'],
                    'SK': item['SK']
                }
            )
        return True
    except Exception as e:
        logger.exception(f"Error invalidating user sessions: {str(e)}")
        return False


def send_password_reset_email(email, reset_url):
    """
    Send a password reset email to the user.

    :param email: Recipient email address
    :param reset_url: Password reset URL
    :return: True if successful, False otherwise
    """
    try:
        # Create a multipart message
        msg = MIMEMultipart()
        msg['Subject'] = 'Reset Your Password'
        msg['From'] = 'noreply@pylaform.com'
        msg['To'] = email

        # Create HTML content
        html = f"""
        <html>
        <body>
            <h2>Reset Your Password</h2>
            <p>You requested a password reset for your Pylaform account.</p>
            <p>Click the link below to set a new password:</p>
            <p><a href="{reset_url}">Reset Password</a></p>
            <p>This link will expire in 24 hours.</p>
            <p>If you didn't request this, you can safely ignore this email.</p>
            <p>Best regards,<br>The Pylaform Team</p>
        </body>
        </html>
        """

        # Attach HTML content
        msg.attach(MIMEText(html, 'html'))

        # Create plain text version
        text = f"""
        Reset Your Password

        You requested a password reset for your Pylaform account.

        Click the link below to set a new password:
        {reset_url}

        This link will expire in 24 hours.

        If you didn't request this, you can safely ignore this email.

        Best regards,
        The Pylaform Team
        """

        msg.attach(MIMEText(text, 'plain'))

        # Get AWS SES client
        ses = boto3.client('ses', region_name='us-east-1')

        # Send the email
        response = ses.send_raw_email(
            Source='noreply@pylaform.com',
            Destinations=[email],
            RawMessage={'Data': msg.as_string()}
        )

        logger.info(f"Password reset email sent to {email}")
        return True
    except Exception as e:
        logger.exception(f"Error sending password reset email: {str(e)}")
        return False


def get_user_by_email(table, email):
    """
    Get a user by email address.

    :param table: DynamoDB table object
    :param email: Email address to look up
    :return: User data if found, None otherwise
    """
    try:
        # Query the GSI to find user by email
        response = table.query(
            IndexName='GSI1',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('GSI1PK').eq(f"EMAIL#{email.lower()}")
        )

        if not response.get('Items'):
            return None

        return response['Items'][0]
    except Exception as e:
        logger.exception(f"Error getting user by email: {str(e)}")
        return None





def invalidate_reset_token(table, token):
    """
    Mark a reset token as used.

    :param table: DynamoDB table object
    :param token: Reset token to invalidate
    :return: True if successful, False otherwise
    """
    try:
        table.update_item(
            Key={
                'PK': f'RESET#{token}',
                'SK': 'TOKEN'
            },
            UpdateExpression="SET used = :used",
            ExpressionAttributeValues={
                ':used': True
            }
        )
        return True
    except Exception as e:
        logger.exception(f"Error invalidating reset token: {str(e)}")
        return False

def create_user(table, email, password, first_name, last_name):
    """
    Create a new user in the database.

    :param table: DynamoDB table object
    :param email: User email
    :param password: User password (plaintext)
    :param first_name: User first name
    :param last_name: User last name
    :return: User ID if successful, None if email already exists
    """
    try:
        # Check if email already exists
        existing_user = get_user_by_email(table, email)
        if existing_user:
            logger.warning(f"Email already exists: {email}")
            return None

        # Generate user ID
        user_id = secrets.token_hex(16)
        user_id_with_prefix = f"USER#{user_id}"

        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Create user record
        table.put_item(
            Item={
                'PK': user_id_with_prefix,
                'SK': 'PROFILE',
                'email': email.lower(),
                'GSI1PK': f"EMAIL#{email.lower()}",
                'GSI1SK': user_id_with_prefix,
                'password': password_hash,
                'first_name': first_name,
                'last_name': last_name,
                'created_at': int(time.time()),
                'updated_at': int(time.time())
            }
        )

        return user_id
    except Exception as e:
        logger.exception(f"Error creating user: {str(e)}")
        return None


def create_session(table, user_id):
    """
    Create a new session for a user.

    :param table: DynamoDB table object
    :param user_id: User ID
    :return: Session ID
    """
    try:
        session_id = secrets.token_hex(32)
        user_id_with_prefix = f"USER#{user_id}" if not user_id.startswith("USER#") else user_id
        expiration = int(time.time()) + (7 * 24 * 60 * 60)  # 7 days

        table.put_item(
            Item={
                'PK': user_id_with_prefix,
                'SK': f"SESSION#{session_id}",
                'session_id': session_id,
                'created_at': int(time.time()),
                'expires_at': expiration,
                'valid': True
            }
        )

        return session_id
    except Exception as e:
        logger.exception(f"Error creating session: {str(e)}")
        return None


def verify_password(stored_password, provided_password):
    """
    Verify a password against its hash.

    :param stored_password: Hashed password from database
    :param provided_password: Password to verify
    :return: True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))
    except Exception as e:
        logger.exception(f"Error verifying password: {str(e)}")
        return False


def login_required(f):
    """
    Decorator to require login for a route.

    :param f: Function to decorate
    :return: Decorated function
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'session_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def verify_session(table, user_id, session_id):
    """
    Verify if a session is valid.

    :param table: DynamoDB table object
    :param user_id: User ID
    :param session_id: Session ID
    :return: True if session is valid, False otherwise
    """
    try:
        user_id_with_prefix = f"USER#{user_id}" if not user_id.startswith("USER#") else user_id

        response = table.get_item(
            Key={
                'PK': user_id_with_prefix,
                'SK': f"SESSION#{session_id}"
            }
        )

        if 'Item' not in response:
            logger.warning(f"Session not found: {session_id}")
            return False

        session_data = response['Item']
        current_time = int(time.time())

        # Check if session is expired or invalid
        if session_data.get('expires_at', 0) < current_time or not session_data.get('valid', True):
            logger.warning(f"Session expired or invalid: {session_id}")
            return False

        return True
    except Exception as e:
        logger.exception(f"Error verifying session: {str(e)}")
        return False


def logout(table, user_id, session_id):
    """
    Invalidate a user session.

    :param table: DynamoDB table object
    :param user_id: User ID
    :param session_id: Session ID
    :return: True if successful, False otherwise
    """
    try:
        user_id_with_prefix = f"USER#{user_id}" if not user_id.startswith("USER#") else user_id

        table.update_item(
            Key={
                'PK': user_id_with_prefix,
                'SK': f"SESSION#{session_id}"
            },
            UpdateExpression="SET valid = :valid",
            ExpressionAttributeValues={
                ':valid': False
            }
        )
        return True
    except Exception as e:
        logger.exception(f"Error logging out: {str(e)}")
        return False


def validate_password(password):
    """
    Validate password strength.

    :param password: Password to validate
    :return: Tuple (is_valid, message)
    """
    if not password or len(password) < 12:
        return False, "Password must be at least 12 characters long"

    if len(password) > 128:
        return False, "Password must be less than 128 characters long"

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"

    # Check for common patterns
    common_patterns = ['123', '1234', '12345', 'abc', 'qwerty', 'password']
    if any(pattern in password.lower() for pattern in common_patterns):
        return False, "Password contains common patterns that are easily guessed"

    # Check for repeated characters
    if re.search(r'(.)\1{3,}', password):
        return False, "Password contains too many repeated characters"

    # Check for keyboard patterns
    keyboard_patterns = ['qwerty', 'asdfgh', 'zxcvbn', '123456']
    if any(pattern in password.lower() for pattern in keyboard_patterns):
        return False, "Password contains keyboard patterns that are easily guessed"

    return True, "Password meets requirements"


def password_strength_message():
    """
    Return a message describing password requirements.

    :return: String with password requirements
    """
    return """
    Password must:
    - Be 12-128 characters long
    - Contain at least one uppercase letter
    - Contain at least one lowercase letter
    - Contain at least one number
    - Contain at least one special character (!@#$%^&*(),.?":{}|<>)
    - Not contain common patterns (123, abc, etc.)
    - Not contain more than 3 repeated characters
    - Not contain keyboard patterns (qwerty, etc.)
    """



def get_email_config():
    """
    Get email configuration from AWS Secrets Manager or environment variables.

    :return: Dictionary with email configuration or None if failed
    """
    try:
        # Check if running in AWS Lambda
        if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
            try:
                secrets_client = boto3.client('secretsmanager')
                secret_response = secrets_client.get_secret_value(
                    SecretId='pylaform/email-config'
                )
                return json.loads(secret_response['SecretString'])
            except ClientError as e:
                logger.error(f"Error retrieving email configuration from Secrets Manager: {str(e)}")
                return None
        else:
            # Local development fallback
            return {
                'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
                'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
                'sender_email': os.environ.get('SENDER_EMAIL', 'noreply@pylaform.com'),
                'smtp_username': os.environ.get('SMTP_USERNAME', ''),
                'smtp_password': os.environ.get('SMTP_PASSWORD', '')
            }
    except Exception as e:
        logger.exception(f"Error getting email configuration: {str(e)}")
        return None


def get_user_by_id(table, user_id):
    """
    Get a user by ID.

    :param table: DynamoDB table object
    :param user_id: User ID to look up
    :return: User data if found, None otherwise
    """
    try:
        user_id_with_prefix = f"USER#{user_id}" if not user_id.startswith("USER#") else user_id

        response = table.get_item(
            Key={
                'PK': user_id_with_prefix,
                'SK': 'PROFILE'
            }
        )

        if 'Item' not in response:
            return None

        return response['Item']
    except Exception as e:
        logger.exception(f"Error getting user by ID: {str(e)}")
        return None


def change_password(table, user_id, current_password, new_password):
    """
    Change a user's password.

    :param table: DynamoDB table object
    :param user_id: User ID
    :param current_password: Current password (plaintext)
    :param new_password: New password (plaintext)
    :return: Tuple (success, message)
    """
    try:
        # Get user data
        user = get_user_by_id(table, user_id)
        if not user:
            return False, "User not found"

        # Verify current password
        if not verify_password(user['password'], current_password):
            return False, "Current password is incorrect"

        # Validate new password
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return False, message

        # Update password
        success = update_user_password(table, user['PK'], new_password)
        if not success:
            return False, "Failed to update password"

        return True, "Password changed successfully"
    except Exception as e:
        logger.exception(f"Error changing password: {str(e)}")
        return False, "An error occurred while changing your password"