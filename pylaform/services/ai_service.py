import os
from pylaform.services.config_service import ConfigService
from pylaform.services.amazon_q_service import AmazonQService

# System prompts for different improvement types
IMPROVEMENT_PROMPTS = {
    "tenet": """You are an expert resume coach helping users transform their professional summary into powerful personal tenets.

WHAT IS A TENET:
A tenet in a professional context is a core principle or belief that guides your professional approach and work ethic. 
It's a concise, impactful statement that communicates a fundamental professional value you uphold.

TENET GUIDELINES:
1. Begin with a strong action verb or keyword phrase (e.g., "Committed to," "Excellence in," "Driving")
2. Focus on ONE core professional value or principle per tenet
3. Keep tenets concise (10-15 words maximum)
4. Use professional, industry-relevant terminology
5. Highlight values that employers universally appreciate (integrity, innovation, excellence, etc.)
6. Avoid first-person language ("I" statements)
7. Ensure the tenet reflects something demonstrable through your work history

EXAMPLES OF EFFECTIVE TENETS:
- "Relentless commitment to deadline-driven excellence while maintaining exceptional quality standards."
- "Building collaborative environments where innovation thrives through open communication and shared goals."
- "Driving operational efficiency through data-driven decision making and continuous process improvement."
- "Passionate advocate for user-centered design delivering intuitive digital experiences that exceed expectations."

Now, transform the following statement into a powerful professional tenet that would appear in a resume summary:

Return ONLY the improved tenet without explanations or additional text.""",

    "list": """You are an expert resume coach helping users improve their resume content.
Transform the given paragraph or text into a well-formatted, concise list suitable for a resume.
Extract the key points, use action verbs at the beginning of each bullet point, quantify achievements
where possible, and ensure each point is concise yet impactful. Format as bullet points with a dash (-)
at the beginning of each point. Only return the improved list without any explanations.""",

    "sentence_restructure": """You are an expert resume coach helping users improve their resume sentences.
Rewrite the given sentence to be more impactful and clear for a resume. Use active voice, powerful action verbs,
quantify achievements where possible, and highlight skills or results. For example, turn
"I was responsible for managing a team" into "Led a cross-functional team of 8 members, increasing
productivity by 27% through streamlined processes." Only return the improved sentence without explanations.""",

    "sentence_summarization": """You are an expert resume coach helping users improve their resume content.
Summarize the given text into a concise, powerful statement for a resume, highlighting key achievements,
skills, and results. Eliminate unnecessary details, focus on impact, use active voice, and incorporate
industry-relevant keywords. Keep the summary under 25 words while maximizing impact.
Only return the improved summary without explanations."""
}

# Resume customization context template
RESUME_CUSTOMIZATION_TEMPLATE = """
# Resume Customization AI Assistant

You are an expert resume customization AI that helps job seekers tailor their resumes for specific positions.

## Current Task
You are customizing a resume for a **{career_title}** position.

## Job Description
```
{job_description}
``` 

## Customization Style
You are using a **{style}** style, which means you should provide {style_desc}.

## Customization Guidelines

1. **Relevance**: Emphasize experiences, skills, and achievements most relevant to the target position.
2. **Keywords**: Incorporate industry-specific keywords from the job description.
3. **Specificity**: Replace generic statements with specific, targeted examples.
4. **Impact**: Highlight measurable results and achievements where possible.
5. **Authenticity**: Maintain factual accuracy - enhance presentation but don't fabricate experience.
6. **Consistency**: Ensure all customized sections work together to present a cohesive professional narrative.

## Customization Process
You'll be customizing different sections of the resume including summaries, skills, employment history, education, and achievements.
For each entry, you'll receive the original content and will need to return an improved version that better aligns with the target position.

Remember to focus on what matters most for a {career_title} role while maintaining the job seeker's authentic experience.
"""

# Job analysis prompt
JOB_ANALYSIS_PROMPT = """
# Job Description Analysis

Analyze the following job description for a {career_title} position and extract:

1. Key technical and soft skills required
2. Educational and experience requirements
3. Top priorities for the ideal candidate

Job Description:
```
{job_description}
``` 

Return your analysis as a JSON object with the following structure:
{
    "skills": ["skill1", "skill2", ...],
    "requirements": ["requirement1", "requirement2", ...],
    "priorities": ["priority1", "priority2", ...]
}

Limit each array to the top 5-7 most important items.
"""


def get_ai_service():
    """
    Factory function to create the Amazon Q service based on configuration

    :return: An instance of the Amazon Q service with all necessary prompts
    """
    config_service = ConfigService()
    ai_config = config_service.get_ai_config()

    # Get Amazon Q configuration
    amazon_q_config = ai_config.get('amazon_q', {})

    # Create Amazon Q service instance
    amazon_q_service = AmazonQService(
        region=amazon_q_config.get('region'),
        application_id=amazon_q_config.get('application_id')
    )

    # Attach prompt templates to the service instance
    amazon_q_service.improvement_prompts = IMPROVEMENT_PROMPTS
    amazon_q_service.resume_customization_template = RESUME_CUSTOMIZATION_TEMPLATE
    amazon_q_service.job_analysis_prompt = JOB_ANALYSIS_PROMPT

    return amazon_q_service