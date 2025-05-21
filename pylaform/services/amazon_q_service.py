import logging
import boto3
import json
import os
from botocore.exceptions import ClientError
from tenacity import retry, wait_exponential, stop_after_attempt


logger = logging.getLogger(__name__)

class AmazonQService:
    """
    Service class to interact with Amazon Q APIs
    """

    def __init__(self, region=None, application_id=None):
        """
        Initialize the Amazon Q service

        :param region: AWS region where Amazon Q is deployed
        :param application_id: Amazon Q application ID
        """
        self.region = region or os.environ.get('AWS_REGION', 'us-east-1')
        self.application_id = application_id or os.environ.get('AMAZON_Q_APP_ID')

        # Initialize AWS SDK client
        try:
            self.q_client = boto3.client('qbusiness', region_name=self.region)
            logger.info(f"Initialized Amazon Q client in region {self.region}")
        except Exception as e:
            logger.error(f"Failed to initialize Amazon Q client: {str(e)}")
            self.q_client = None

        # Placeholder for prompt templates (will be set by factory function)
        self.improvement_prompts = {}
        self.resume_customization_template = ""
        self.job_analysis_prompt = ""

    def check_connection(self):
        """
        Check if the Amazon Q service is properly connected and configured

        :return: A tuple (bool, str) indicating success status and message
        """
        if not self.q_client:
            return False, "Amazon Q client not initialized"

        if not self.application_id:
            return False, "Amazon Q application ID not configured"

        try:
            # Try a simple operation to verify connection
            response = self.q_client.list_applications(maxResults=1)
            return True, "Connected to Amazon Q service"
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
            logger.error(f"Amazon Q connection error: {error_code} - {error_message}")
            return False, f"Amazon Q connection error: {error_code}"
        except Exception as e:
            logger.error(f"Error checking Amazon Q connection: {str(e)}")
            return False, f"Error checking Amazon Q connection: {str(e)}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def improve_text(self, text, improvement_type):
        """
        Improve text content using Amazon Q according to specified improvement type

        :param text: The text to improve
        :param improvement_type: Type of improvement to apply
        :return: Improved text or error message
        """
        if not self.q_client:
            return {"error": "Amazon Q service not available"}

        # Get the appropriate prompt for the improvement type
        prompt_template = self.improvement_prompts.get(improvement_type)
        if not prompt_template:
            return {"error": f"Unknown improvement type: {improvement_type}"}

        # Combine the prompt with the user's text
        prompt = f"{prompt_template}\n\n{text}"

        try:
            response = self.q_client.chat(
                applicationId=self.application_id,
                userMessage=prompt
            )

            # Extract the response text
            response_text = response.get('systemMessage', {}).get('text', '')
            if not response_text:
                return {"error": "No response generated"}

            return {"response": response_text}

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
            logger.error(f"Amazon Q chat error: {error_code} - {error_message}")
            return {"error": f"Amazon Q error: {error_message}"}
        except Exception as e:
            logger.error(f"Error generating improvement: {str(e)}")
            return {"error": f"Error: {str(e)}"}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def analyze_job_description(self, job_title, job_description):
        """
        Analyze a job description to extract key skills and requirements

        :param job_title: The job title
        :param job_description: The full job description
        :return: Dictionary with analysis results or error
        """
        if not self.q_client:
            return {"error": "Amazon Q service not available"}

        # Format the prompt with job details
        prompt = self.job_analysis_prompt.format(
            career_title=job_title,
            job_description=job_description
        )

        try:
            response = self.q_client.chat(
                applicationId=self.application_id,
                userMessage=prompt
            )

            # Extract the response text
            response_text = response.get('systemMessage', {}).get('text', '')
            if not response_text:
                return {"error": "No analysis generated"}

            # Try to parse the JSON response
            try:
                # Find JSON object in the response text
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    analysis = json.loads(json_str)
                    return {"analysis": analysis}
                else:
                    return {"error": "Failed to extract JSON from response"}
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {response_text}")
                return {"error": "Invalid JSON response", "raw_response": response_text}

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
            logger.error(f"Amazon Q chat error: {error_code} - {error_message}")
            return {"error": f"Amazon Q error: {error_message}"}
        except Exception as e:
            logger.error(f"Error analyzing job description: {str(e)}")
            return {"error": f"Error: {str(e)}"}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def customize_resume_content(self, content_type, original_content, job_title, job_description, style="balanced"):
        """
        Customize resume content for a specific job

        :param content_type: Type of content (summary, skill, achievement, etc.)
        :param original_content: The original content text
        :param job_title: The target job title
        :param job_description: The job description
        :param style: Customization style (balanced, conservative, aggressive)
        :return: Dictionary with customized content or error
        """
        if not self.q_client:
            return {"error": "Amazon Q service not available"}

        # Define style descriptions
        style_descriptions = {
            "balanced": "moderate customization that maintains your voice while aligning with the job requirements",
            "conservative": "subtle refinements that maintain most of your original content with minimal changes",
            "aggressive": "significant customization that maximizes alignment with the job description"
        }

        # Format the system prompt with job details
        system_prompt = self.resume_customization_template.format(
            career_title=job_title,
            job_description=job_description,
            style=style,
            style_desc=style_descriptions.get(style, style_descriptions["balanced"])
        )

        # Create the specific task prompt
        task_prompt = f"""Please customize the following {content_type} for a {job_title} position:

Original {content_type}:
```
{original_content}
``` 

Return only the improved {content_type} without explanations."""

        try:
            # Send the system prompt first to set context
            context_response = self.q_client.chat(
                applicationId=self.application_id,
                userMessage=system_prompt
            )

            # Now send the specific task with the original content
            response = self.q_client.chat(
                applicationId=self.application_id,
                userMessage=task_prompt,
                conversationId=context_response.get('conversationId')
            )

            # Extract the response text
            response_text = response.get('systemMessage', {}).get('text', '')
            if not response_text:
                return {"error": "No customization generated"}

            # Clean up any code block formatting that might be in the response
            cleaned_response = response_text.replace('```', '').strip()

            return {"customized_content": cleaned_response}

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
            logger.error(f"Amazon Q chat error: {error_code} - {error_message}")
            return {"error": f"Amazon Q error: {error_message}"}
        except Exception as e:
            logger.error(f"Error customizing resume content: {str(e)}")
            return {"error": f"Error: {str(e)}"}