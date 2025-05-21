#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from pylaform.services.amazon_q_service import AmazonQService

# Load environment variables
load_dotenv()


def main():
    """Test Amazon Q functionality"""
    print("Testing Amazon Q integration...")

    # Create service instance
    service = AmazonQService(
        region=os.environ.get('AWS_REGION'),
        application_id=os.environ.get('AMAZON_Q_APP_ID')
    )

    # Test connection
    print("\nTesting connection:")
    success, message = service.check_connection()
    print(f"Connection success: {success}")
    print(f"Message: {message}")

    if not success:
        print("Connection failed, stopping tests")
        return

    # Test text improvement
    print("\nTesting text improvement:")
    test_text = "I designed and implemented database schemas and APIs for the company's main product."

    for improvement_type in ["tenet", "list", "sentence_restructure", "sentence_summarization"]:
        print(f"\nImprovement type: {improvement_type}")
        service.improvement_prompts = {
            "tenet": "Transform the following text into a compelling resume core principle/tenet:",
            "list": "Convert the following paragraph into a bulleted list for a resume:",
            "sentence_restructure": "Restructure this resume sentence to be more impactful:",
            "sentence_summarization": "Summarize this resume content into a concise statement:"
        }

        result = service.improve_text(test_text, improvement_type)
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Original: {test_text}")
            print(f"Improved: {result['response']}")


if __name__ == "__main__":
    main()