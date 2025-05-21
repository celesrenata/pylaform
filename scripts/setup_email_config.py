#!/usr/bin/env python3
import boto3
import json
import argparse
import getpass


def setup_email_config():
    """
    Set up email configuration in AWS Secrets Manager.
    """
    parser = argparse.ArgumentParser(description='Set up email configuration for Pylaform')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    args = parser.parse_args()

    print("Setting up email configuration for Pylaform password reset emails")
    print("This will store your email credentials in AWS Secrets Manager")
    print("-----------------------------------------------------------")

    # Get email configuration
    sender_email = input("Sender email address: ")
    smtp_server = input("SMTP server (default: smtp.gmail.com): ") or "smtp.gmail.com"
    smtp_port = input("SMTP port (default: 587): ") or "587"
    smtp_username = input("SMTP username (default: same as sender email): ") or sender_email
    smtp_password = getpass.getpass("SMTP password: ")

    # Create the secret
    email_config = {
        'sender_email': sender_email,
        'smtp_server': smtp_server,
        'smtp_port': smtp_port,
        'smtp_username': smtp_username,
        'smtp_password': smtp_password
    }

    # Create AWS Secrets Manager client
    client = boto3.client('secretsmanager', region_name=args.region)

    try:
        # Check if secret already exists
        try:
            client.describe_secret(SecretId='pylaform/email-config')
            update = input("Email configuration already exists. Update it? (y/n): ")
            if update.lower() != 'y':
                print("Aborted.")
                return

            # Update existing secret
            client.update_secret(
                SecretId='pylaform/email-config',
                SecretString=json.dumps(email_config)
            )
            print("Email configuration updated successfully.")
        except client.exceptions.ResourceNotFoundException:
            # Create new secret
            client.create_secret(
                Name='pylaform/email-config',
                Description='Pylaform email configuration for password reset emails',
                SecretString=json.dumps(email_config)
            )
            print("Email configuration created successfully.")
    except Exception as e:
        print(f"Error setting up email configuration: {str(e)}")


if __name__ == "__main__":
    setup_email_config()