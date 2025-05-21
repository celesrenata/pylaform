# pylaform/services/ai_factory.py
from pylaform.services.amazon_q_service import AmazonQService
import os


def get_ai_service():
    """
    Factory function to create and configure an AI service instance

    :return: Configured AI service instance
    """
    # Get environment variables
    region = os.environ.get('AWS_REGION', 'us-east-1')
    application_id = os.environ.get('AMAZON_Q_APP_ID')

    # Create service
    service = AmazonQService(region=region, application_id=application_id)

    # Configure prompt templates
    service.improvement_prompts = {
        "tenet": "Transform the following text into a compelling resume core principle/tenet that demonstrates your professional value. Focus on making it concise, impactful, and reflective of your professional identity:",

        "list": "Convert the following paragraph into a bulleted list format suitable for a resume. Each item should be concise and start with a strong action verb:",

        "sentence_restructure": "Restructure the following resume sentence to make it more impactful and professional while keeping the key information. Focus on using strong action verbs and quantifying achievements where possible:",

        "sentence_summarization": "Summarize the following resume content into a concise, impactful statement that maintains the key points while reducing the overall length by approximately 30%. Ensure it remains professional and effective:"
    }

    service.resume_customization_template = """
    You are a professional resume customization expert. Your task is to customize resume content 
    for a {career_title} position with the following job description:

    ---
    {job_description}
    ---

    Please provide a {style} {style_desc}.
    """

    service.job_analysis_prompt = """
    Analyze this job description for a {career_title} position:

    ---
    {job_description}
    ---

    Extract the following information and format as JSON:
    1. Key skills required
    2. Technical requirements
    3. Education requirements
    4. Experience level
    5. Soft skills valued
    6. Primary responsibilities

    Return ONLY valid JSON with these fields.
    """

    return service