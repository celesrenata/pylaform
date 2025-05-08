import json
import requests
from flask import current_app
from pylaform.services.config_service import ConfigService


class OllamaService:
    """Service to interact with Ollama API for resume improvements"""

    def __init__(self, host=None, port=None, model=None):
        """
        Initialize the OllamaService with the specified configuration parameters
        If parameters are not provided, they will be loaded from the config file

        :param host: The host of the Ollama server
        :param port: The port of the Ollama server
        :param model: The name of the model to use
        """
        # Get config from ConfigService
        config_service = ConfigService()
        ai_config = config_service.get_ai_config()

        # Use provided parameters or fall back to config values
        self.host = host or ai_config.get('ollama', {}).get('host', 'localhost')
        self.port = port or ai_config.get('ollama', {}).get('port', '11434')
        self.model = model or ai_config.get('ollama', {}).get('model', 'gemma3:1b')

        # Construct base URL
        self.base_url = f"http://{self.host}:{self.port}"

        # Add detailed logging on initialization
        print(f"OllamaService initialized with:")
        print(f"  - Host: {self.host}")
        print(f"  - Port: {self.port}")
        print(f"  - Model: {self.model}")
        print(f"  - Base URL: {self.base_url}")

    def test_connection(self):
        """
        Test the connection to the Ollama server

        :return: Dictionary with success status and error message if applicable
        """
        try:
            # Simple ping to the models endpoint
            response = requests.get(f"{self.base_url}/api/tags")

            if response.status_code == 200:
                # Check if our configured model is available
                models = response.json().get("models", [])
                model_names = [model.get("name") for model in models]

                if not models:
                    return {"success": False, "error": "No models found on the Ollama server"}

                if self.model not in model_names:
                    # Model not found, but connection works
                    return {
                        "success": False,
                        "error": f"Model '{self.model}' not found. Available models: {', '.join(model_names)}"
                    }

                return {"success": True}
            else:
                return {"success": False, "error": f"Server returned status code {response.status_code}"}

        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Could not connect to Ollama server"}
        except Exception as e:
            return {"success": False, "error": f"Error: {str(e)}"}

    def download_model(self, model_name):
        """
        Download a model from Ollama

        :param model_name: Name of the model to download
        :return: Dictionary with status information
        """
        try:
            # Prepare the request payload
            payload = {
                "name": model_name
            }

            # Send a POST request to the Ollama pull API
            response = requests.post(
                f"{self.base_url}/api/pull",
                json=payload,
                stream=True  # Use streaming for large downloads
            )

            # Check if the request was accepted
            if response.status_code == 200:
                # For streaming responses, we need to process line by line
                for line in response.iter_lines():
                    if line:
                        # Convert line to JSON
                        try:
                            line_data = json.loads(line.decode('utf-8'))
                            # Check if there's an error in the response
                            if 'error' in line_data:
                                return {"success": False, "error": line_data['error']}
                        except json.JSONDecodeError:
                            pass  # Skip lines that aren't valid JSON

                # If we got here with no errors, the download was initiated successfully
                return {"success": True, "message": f"Model download initiated for {model_name}"}
            else:
                # If there was an error, try to extract the error message
                try:
                    error_data = response.json()
                    error_message = error_data.get("error", f"Server returned status code {response.status_code}")
                except:
                    error_message = f"Server returned status code {response.status_code}"

                return {"success": False, "error": error_message}

        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Could not connect to Ollama server"}
        except Exception as e:
            return {"success": False, "error": f"Error: {str(e)}"}

    def get_status(self):
        """
        Get the status of the Ollama service

        :return: Dictionary with status information
        """
        model_status = self.get_model_status()

        if model_status.get("success"):
            # Connection successful, change the return format to match what frontend expects
            return {
                "status": "ok",
                "models": model_status.get("models", []),
                "message": "Connected to Ollama"
            }
        else:
            # Connection failed
            return {
                "status": "error",
                "models": [],
                "message": model_status.get("error", "Unknown error connecting to Ollama")
            }

    def get_model_status(self):
        """
        Get the status of available models

        :return: Dictionary with list of models and their details
        """
        try:
            # Send a request to the Ollama models API
            response = requests.get(f"{self.base_url}/api/tags")

            if response.status_code == 200:
                return {"success": True, "models": response.json().get("models", [])}
            else:
                return {"success": False, "error": f"Server returned status code {response.status_code}"}

        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Could not connect to Ollama server"}
        except Exception as e:
            return {"success": False, "error": f"Error: {str(e)}"}

    def customize_resume_content(self, section_type, entries, career_title, job_description, style):
        """
        Use AI to customize resume entries for a target career.

        Args:
            section_type: Type of section (summary, skills, etc.)
            entries: List of active entries to customize
            career_title: Target job title
            job_description: Job description or career details
            style: Customization style preference

        Returns:
            List of customized entries
        """
        customized_entries = []

        # Get the comprehensive context for the AI
        context = self.get_customization_context(career_title, job_description, style)

        # Try to analyze the job description for key requirements
        try:
            job_analysis = self.analyze_job_description(job_description, career_title)
            skills_str = ", ".join(job_analysis.get("skills", []))
            requirements_str = ", ".join(job_analysis.get("requirements", []))
            priorities_str = ", ".join(job_analysis.get("priorities", []))

            job_insights = f"""
            ## Job Analysis Insights:
            - Key skills: {skills_str}
            - Requirements: {requirements_str}
            - Priorities: {priorities_str}
            """
        except Exception as e:
            print(f"Error analyzing job: {e}")
            job_insights = ""

        for entry in entries:
            # Skip inactive entries
            if not entry.get("state", False):
                continue

            # Prepare prompt based on section type
            if section_type == "summary":
                prompt = f"""
                {context}

                {job_insights}

                ## Current Section: Professional Summary

                Original Summary:
                * Short description: {entry.get('shortdesc', '')}
                * Long description: {entry.get('longdesc', '')}

                ## Understanding Professional Tenets

                Professional tenets in a resume should be concise statements that highlight your core professional values and approaches. The ideal format is:

                "Short Actionable Phrase: One clear explanatory sentence."

                Guidelines:
                1. Begin with a short, powerful phrase (2-4 words) like "Excellence in Delivery" or "Strategic Problem-Solver"
                2. Follow with a colon and a SINGLE sentence (15-25 words) explaining how you embody this principle
                3. Ensure the sentence provides specific, tangible examples from your own experience
                4. Avoid generic statements that could apply to anyone
                5. Use third-person perspective without "I" statements

                Examples:
                - "Technical Innovation: Develops elegant, scalable solutions to complex problems using cutting-edge cloud technologies and automation."
                - "Client Partnership: Builds trusted relationships through transparent communication and consistent delivery of business value."
                - "Operational Excellence: Implements robust processes and monitoring systems that ensure 99.9% service reliability."

                ## Task
                1. Transform the short description into a concise tenet phrase (2-4 words)
                2. Create a SINGLE clear sentence (connected with a colon) that describes how you apply this principle
                3. Focus on YOUR actual experience, not generic job description requirements
                4. Keep the total length under 30 words
                5. Make sure it aligns with your experience as seen in your resume

                Return your response as valid JSON with 'shortdesc' containing the full tenet (phrase + colon + sentence).
                The 'longdesc' should remain empty as we're using the concise format.

                Example: {{"shortdesc": "Infrastructure Automation: Develops and implements CI/CD pipelines that reduce deployment time by 70% while improving reliability.", "longdesc": ""}}
                """
                default_values = {
                    'shortdesc': entry.get('shortdesc', ''),
                    'longdesc': ''  # We're setting this to empty as we want just the concise format
                }
            elif section_type == "skills":
                prompt = f"""
                {context}

                {job_insights}

                ## Current Section: Skills

                Original Skill:
                * Category: {entry.get('category', '')}
                * Skill Name: {entry.get('shortdesc', '')}
                * Description: {entry.get('longdesc', '')}

                ## Effective Skill Customization Guidelines

                1. Match terminology used in the job description exactly when appropriate
                2. Include proficiency level indicators (e.g., "Expert in", "Advanced knowledge of")
                3. Highlight specific applications or contexts relevant to the target role
                4. Mention impact (how this skill creates value) when possible
                5. Include relevant tools, methodologies, or technologies

                ## Task
                Customize this skill description to emphasize its relevance to the {career_title} position.
                Make it clear why this skill would be valuable for the specific role based on the job description.

                Return your response as valid JSON with 'shortdesc' and 'longdesc' fields containing the customized content.
                Example: {{"shortdesc": "Your customized skill name", "longdesc": "Your customized skill description"}}
                """
                default_values = {
                    'shortdesc': entry.get('shortdesc', ''),
                    'longdesc': entry.get('longdesc', '')
                }
            elif section_type == "employment":
                prompt = f"""
                {context}

                {job_insights}

                ## Current Section: Employment History

                Original Employment:
                * Position: {entry.get('positionname', '')}
                * Company: {entry.get('employername', '')}
                * Description: {entry.get('longdesc', '')}

                ## Effective Employment Customization Guidelines

                1. Begin each bullet point with a strong action verb
                2. Emphasize accomplishments and outcomes over duties
                3. Quantify achievements with metrics when possible (%, $, time saved, etc.)
                4. Highlight skills and experiences most relevant to the target position
                5. Use industry-specific terminology that appears in the job description
                6. Focus on transferable skills if this role differs from the target position

                ## Task
                Customize this employment description to showcase experiences most relevant to the {career_title} position.
                Transform duty-focused statements into achievement-focused bullet points when appropriate.

                Return your response as valid JSON with 'longdesc' field containing the customized description.
                Example: {{"longdesc": "Your customized employment description"}}
                """
                default_values = {
                    'longdesc': entry.get('longdesc', '')
                }
            elif section_type == "education":
                prompt = f"""
                {context}

                {job_insights}

                ## Current Section: Education

                Original Education:
                * School: {entry.get('schoolname', '')}
                * Degree/Focus: {entry.get('focusname', '')}

                ## Effective Education Customization Guidelines

                1. Emphasize coursework, projects, or research relevant to the target position
                2. Highlight academic achievements that demonstrate skills needed for the role
                3. Include relevant concentrations, minors, or specializations
                4. Mention specific software, tools, or methodologies learned if applicable
                5. Connect educational experiences to job requirements

                ## Task
                Customize this education description to emphasize aspects most relevant to a {career_title} position.
                Make it clear how this educational background prepares you for the target role.

                Return your response as valid JSON with 'focusname' field containing the customized degree description.
                Example: {{"focusname": "Your customized degree/focus description"}}
                """
                default_values = {
                    'focusname': entry.get('focusname', '')
                }
            elif section_type == "certifications":
                prompt = f"""
                {context}

                {job_insights}

                ## Current Section: Certifications

                Original Certification:
                * Certification: {entry.get('certification', '')}

                ## Effective Certification Customization Guidelines

                1. Emphasize the skills or knowledge validated by the certification
                2. Highlight how the certification is relevant to the target position
                3. Include details about the certification's reputation or difficulty if impressive
                4. Mention specific tools, technologies, or methodologies covered
                5. If appropriate, note recency of certification or continuing education

                ## Task
                Customize this certification description to highlight its relevance to the {career_title} position.
                Make it clear why this credential would be valuable for the specific role.

                Return your response as valid JSON with 'certification' field containing the customized certification description.
                Example: {{"certification": "Your customized certification description"}}
                """
                default_values = {
                    'certification': entry.get('certification', '')
                }
            elif section_type == "achievements":
                prompt = f"""
                {context}

                {job_insights}

                ## Current Section: Achievements

                Original Achievement:
                * Title: {entry.get('shortdesc', '')}
                * Description: {entry.get('longdesc', '')}

                ## Effective Achievement Customization Guidelines

                1. Lead with strong action verbs that demonstrate initiative and impact
                2. Quantify results with specific metrics when possible (%, $, time saved, etc.)
                3. Highlight skills and competencies valued in the target position
                4. Show problem-solving abilities and the challenges overcome
                5. Focus on achievements most relevant to the target role
                6. Include recognition or awards related to the achievement if applicable

                ## Task
                Customize this achievement to emphasize aspects most impressive for a {career_title} position.
                Make it clear why this accomplishment demonstrates your qualification for the target role.

                Return your response as valid JSON with 'shortdesc' and 'longdesc' fields containing the customized content.
                Example: {{"shortdesc": "Your customized achievement title", "longdesc": "Your customized achievement description"}}
                """
                default_values = {
                    'shortdesc': entry.get('shortdesc', ''),
                    'longdesc': entry.get('longdesc', '')
                }
            else:
                # Skip unknown section types
                continue

            try:
                # Call AI service with prompt
                response = self.generate(prompt)

                # Check if there was an error in the generate method
                if 'error' in response:
                    print(f"Error generating response: {response['error']}")
                    raise Exception(response['error'])

                # Parse JSON response
                import json
                try:
                    response_text = response.get('response', '{}')
                    # Try to extract JSON if it's embedded in text
                    if '{' in response_text and '}' in response_text:
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        json_str = response_text[json_start:json_end]
                        customized_content = json.loads(json_str)
                    else:
                        customized_content = json.loads(response_text)

                    # Ensure all expected fields are present
                    for key in default_values:
                        if key not in customized_content:
                            customized_content[key] = default_values[key]
                except json.JSONDecodeError:
                    print(f"Invalid JSON in response: {response_text}")
                    # Use the default values if JSON parsing fails
                    customized_content = default_values

                # Add to customized entries
                customized_entry = {
                    'id': entry.get('id'),
                    'original': entry,
                    'customized': customized_content
                }
                customized_entries.append(customized_entry)

            except Exception as e:
                print(f"Error customizing entry: {e}")
                # Add entry with original content as fallback
                customized_entry = {
                    'id': entry.get('id'),
                    'original': entry,
                    'customized': default_values
                }
                customized_entries.append(customized_entry)

        return customized_entries

    def generate(self, prompt):
        """
        Generate a response from the AI model using the given prompt
        Tries both /api/generate and /api/chat endpoints to support different Ollama versions

        :param prompt: The prompt to send to the AI model
        :return: Dictionary with the response or error
        """
        try:
            # First try the /api/chat endpoint (newer versions)
            chat_payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500
                }
            }

            headers = {"Content-Type": "application/json"}

            # Debug information
            chat_url = f"{self.base_url}/api/chat"
            generate_url = f"{self.base_url}/api/generate"

            print(f"DEBUG: Ollama Configuration:")
            print(f"DEBUG: Base URL: {self.base_url}")
            print(f"DEBUG: Model: {self.model}")
            print(f"DEBUG: Attempting to connect to chat endpoint: {chat_url}")
            print(f"DEBUG: Headers: {headers}")
            print(f"DEBUG: Payload (truncated): {str(chat_payload)[:200]}...")

            # Try with /api/chat first
            try:
                chat_response = requests.post(
                    chat_url,
                    headers=headers,
                    data=json.dumps(chat_payload),
                    timeout=15  # Increase timeout for better diagnostics
                )

                print(f"DEBUG: Chat endpoint response status: {chat_response.status_code}")
                print(f"DEBUG: Chat endpoint response headers: {dict(chat_response.headers)}")

                # Print a portion of the response content for debugging
                try:
                    response_preview = chat_response.text[:500] if chat_response.text else "Empty response"
                    print(f"DEBUG: Chat endpoint response preview: {response_preview}")
                except:
                    print("DEBUG: Unable to print response content")

                # If chat endpoint works
                if chat_response.status_code == 200:
                    try:
                        result = chat_response.json()
                        # Extract content from message for chat endpoint
                        message = result.get("message", {})
                        content = message.get("content", "")
                        print(f"DEBUG: Successfully processed chat response")
                        return {"response": content}
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: JSON decode error on chat response: {e}")
                        pass  # Continue to try generate endpoint
                else:
                    print(f"DEBUG: Chat endpoint failed with status {chat_response.status_code}")

            except requests.exceptions.RequestException as e:
                print(f"DEBUG: Request exception on chat endpoint: {e}")
                # Continue to try the generate endpoint
                pass

            # If chat didn't work, try the /api/generate endpoint (older versions)
            generate_payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500
                }
            }

            print(f"DEBUG: Falling back to generate endpoint: {generate_url}")
            print(f"DEBUG: Generate payload (truncated): {str(generate_payload)[:200]}...")

            try:
                generate_response = requests.post(
                    generate_url,
                    headers=headers,
                    data=json.dumps(generate_payload),
                    timeout=15
                )

                print(f"DEBUG: Generate endpoint response status: {generate_response.status_code}")
                print(f"DEBUG: Generate endpoint response headers: {dict(generate_response.headers)}")

                # Print a portion of the response content for debugging
                try:
                    response_preview = generate_response.text[:500] if generate_response.text else "Empty response"
                    print(f"DEBUG: Generate endpoint response preview: {response_preview}")
                except:
                    print("DEBUG: Unable to print response content")

                # Check if generate endpoint works
                if generate_response.status_code == 200:
                    try:
                        result = generate_response.json()
                        print(f"DEBUG: Successfully processed generate response")
                        return {"response": result.get("response", "")}
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: JSON decode error on generate response: {e}")
                        return {"error": "Failed to parse JSON response from both endpoints"}
                else:
                    print(f"DEBUG: Generate endpoint failed with status {generate_response.status_code}")

            except requests.exceptions.RequestException as e:
                print(f"DEBUG: Request exception on generate endpoint: {e}")
                # Fall through to the error handling below

            # If both endpoints failed
            chat_status = getattr(chat_response, 'status_code', 'N/A')
            generate_status = getattr(generate_response, 'status_code', 'N/A')

            error_msg = f"API Error: {generate_status}"
            details_msg = f"Chat endpoint: {chat_status}, Generate endpoint: {generate_status}"

            print(f"DEBUG: Both endpoints failed. Error: {error_msg}, Details: {details_msg}")

            return {
                "error": error_msg,
                "details": details_msg
            }

        except Exception as e:
            print(f"DEBUG: Unexpected exception in generate method: {str(e)}")
            print(f"DEBUG: Exception type: {type(e).__name__}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            return {"error": f"Connection error: {str(e)}"}

    def generate_improvement(self, text, improvement_type):
        """
        Generate an improvement for the given text based on the specified type
        Tries both /api/generate and /api/chat endpoints to support different Ollama versions

        :param text: Text to improve
        :param improvement_type: Type of improvement (tenet, list, sentence_restructure, sentence_summarization)
        :return: Improved text from the AI
        """
        # Detailed instructions for each improvement type
        system_instructions = {
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

        if improvement_type not in system_instructions:
            return {"error": "Invalid improvement type"}

        try:
            # First try the /api/chat endpoint (newer versions)
            chat_payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_instructions[improvement_type]},
                    {"role": "user", "content": f"Text to improve: {text}"}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 300
                }
            }

            headers = {"Content-Type": "application/json"}

            # Try with /api/chat first
            chat_response = requests.post(
                f"{self.base_url}/api/chat",
                headers=headers,
                data=json.dumps(chat_payload)
            )

            # If chat endpoint works
            if chat_response.status_code == 200:
                try:
                    result = chat_response.json()
                    # Extract content from message for chat endpoint
                    message = result.get("message", {})
                    content = message.get("content", "")
                    return {"response": content}
                except json.JSONDecodeError:
                    pass  # Continue to try generate endpoint

            # If chat didn't work, try the /api/generate endpoint (older versions)
            # Combine instructions and text for the generate endpoint
            prompt = f"{system_instructions[improvement_type]}\n\nText to improve: {text}"

            generate_payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 300
                }
            }

            generate_response = requests.post(
                f"{self.base_url}/api/generate",
                headers=headers,
                data=json.dumps(generate_payload)
            )

            # Check if generate endpoint works
            if generate_response.status_code == 200:
                try:
                    result = generate_response.json()
                    return {"response": result.get("response", "")}
                except json.JSONDecodeError:
                    return {"error": "Failed to parse JSON response from both endpoints"}

            # If both endpoints failed, return the details of the last attempt
            return {
                "error": f"API Error: {generate_response.status_code}",
                "details": generate_response.text
            }

        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def get_customization_context(self, career_title, job_description, style):
        """
        Generate a comprehensive context description for the AI model to understand
        its role in customizing a resume for a specific career opportunity.

        Args:
            career_title: Target job title
            job_description: Job description text
            style: Customization style preference

        Returns:
            String containing the context for the AI model
        """
        style_descriptions = {
            "professional": "formal, industry-standard language with emphasis on achievements and responsibilities",
            "achievement": "results-oriented language with metrics, outcomes, and impact highlighted",
            "technical": "detailed technical skills, tools, and methodologies with specific applications",
            "concise": "brief, impactful statements focusing on the most relevant qualifications and achievements"
        }

        style_desc = style_descriptions.get(style, "balanced professional content")

        context = f"""
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

        return context

    def analyze_job_description(self, job_description, career_title):
        """
        Analyze a job description to extract key skills, requirements, and priorities
        for better resume customization.

        Args:
            job_description: The job description text
            career_title: The target job title

        Returns:
            Dictionary containing analysis results or error
        """
        if not job_description:
            return {
                "skills": [],
                "requirements": [],
                "priorities": []
            }

        prompt = f"""
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
        {{
            "skills": ["skill1", "skill2", ...],
            "requirements": ["requirement1", "requirement2", ...],
            "priorities": ["priority1", "priority2", ...]
        }}

        Limit each array to the top 5-7 most important items.
        """

        try:
            response = self.generate(prompt)

            # Check if there was an error
            if 'error' in response:
                print(f"Error analyzing job description: {response['error']}")
                return {
                    "skills": [],
                    "requirements": [],
                    "priorities": []
                }

            # Parse JSON response
            import json
            try:
                response_text = response.get('response', '{}')
                # Try to extract JSON if it's embedded in text
                if '{' in response_text and '}' in response_text:
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    json_str = response_text[json_start:json_end]
                    analysis = json.loads(json_str)
                else:
                    analysis = json.loads(response_text)

                # Ensure expected fields are present
                expected_fields = ["skills", "requirements", "priorities"]
                for field in expected_fields:
                    if field not in analysis:
                        analysis[field] = []

                return analysis

            except json.JSONDecodeError:
                print(f"Invalid JSON in job analysis response: {response_text}")
                return {
                    "skills": [],
                    "requirements": [],
                    "priorities": []
                }

        except Exception as e:
            print(f"Error in job description analysis: {e}")
            return {
                "skills": [],
                "requirements": [],
                "priorities": []
            }