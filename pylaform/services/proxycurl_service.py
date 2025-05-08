import os
import logging
import requests
from pylaform.services.config_service import ConfigService


class ProxycurlService:
    """Service to interact with Proxycurl API for LinkedIn data"""

    def __init__(self):
        # Try to get API key from environment first
        self.api_key = os.environ.get('PROXYCURL_API_KEY', '')

        # If not found in environment, try to get from config file
        if not self.api_key:
            try:
                config_service = ConfigService()
                config = config_service._load_config()  # Use _load_config instead of load_config
                linkedin_config = config.get('linkedin', {})
                self.api_key = linkedin_config.get('proxycurl_api_key', '')

                # Also set in environment for future use
                if self.api_key:
                    os.environ['PROXYCURL_API_KEY'] = self.api_key
            except Exception as e:
                # Log error but continue
                logging.error(f"Error loading Proxycurl API key from config: {str(e)}")

        self.base_url = 'https://nubela.co/proxycurl/api/v2'
        self.logger = logging.getLogger(__name__)

    def get_profile_data(self, linkedin_profile_url):
        """
        Fetch LinkedIn profile data using Proxycurl API

        Args:
            linkedin_profile_url: URL of the LinkedIn profile to fetch

        Returns:
            dict: Parsed LinkedIn profile data or error information
        """
        if not self.api_key:
            self.logger.error("Proxycurl API key not configured")
            return {"error": "Proxycurl API key not configured"}

        # Ensure API key doesn't contain any non-ASCII characters
        try:
            clean_api_key = self.api_key.encode('ascii', 'ignore').decode('ascii')
            headers = {
                'Authorization': f'Bearer {clean_api_key}'
            }
        except Exception as e:
            self.logger.error(f"Error encoding API key: {str(e)}")
            return {"error": "Invalid API key format. Please check for special characters."}

        # URL encoding of parameters to handle special characters
        try:
            # Use a simple dictionary of parameters and let requests handle the encoding
            params = {
                'url': linkedin_profile_url.strip(),
                'skills': 'include',
                'education': 'include',
                'experience': 'include',
                'use_cache': 'if-present'
            }

            self.logger.info(f"Fetching LinkedIn profile data for {linkedin_profile_url}")
            self.logger.debug(f"Proxycurl API request: URL={self.base_url}/linkedin")

            # To debug encoding issues, let's log the actual values
            self.logger.debug(f"API key type: {type(clean_api_key)}, URL type: {type(linkedin_profile_url)}")

            # Use a session for better control and error handling
            session = requests.Session()

            # Make the request
            response = session.get(
                f"{self.base_url}/linkedin",
                params=params,
                headers=headers,
                timeout=30  # Adding a timeout
            )

            self.logger.debug(f"Proxycurl API response: Status={response.status_code}")

            if response.status_code == 200:
                try:
                    raw_data = response.json()
                    self.logger.debug(f"Proxycurl API raw response keys: {list(raw_data.keys())}")

                    # Debug specific sections as before...

                    formatted_data = self._format_profile_data(raw_data)
                    return formatted_data
                except ValueError as json_err:
                    error_msg = f"Error parsing JSON response: {str(json_err)}"
                    self.logger.error(error_msg)
                    return {"error": error_msg}
            else:
                error_msg = f"Proxycurl API request failed: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return {"error": error_msg}

        except requests.exceptions.RequestException as req_err:
            error_msg = f"Request error with Proxycurl API: {str(req_err)}"
            self.logger.error(error_msg)
            self.logger.exception("Request exception details:")
            return {"error": error_msg}

        except UnicodeError as unicode_err:
            error_msg = f"Unicode encoding error: {str(unicode_err)}"
            self.logger.error(error_msg)
            self.logger.exception("Unicode error details:")
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Error fetching profile data from Proxycurl: {str(e)}"
            self.logger.error(error_msg)
            self.logger.exception("Full exception details:")
            return {"error": error_msg}

    def _format_profile_data(self, raw_data):
        """
        Format Proxycurl API response to match expected format in our application

        Args:
            raw_data: Raw response from Proxycurl API

        Returns:
            dict: Formatted profile data
        """
        formatted_data = {}

        self.logger.debug("--- DEBUG: Formatting profile data ---")

        # Ensure raw_data is a dictionary
        if not isinstance(raw_data, dict):
            self.logger.error(f"Invalid raw_data type: {type(raw_data)}")
            return {
                "error": "Invalid data format received from Proxycurl API"
            }

        # Basic profile info with safe defaults
        formatted_data['firstName'] = raw_data.get('first_name', '') or ''
        formatted_data['lastName'] = raw_data.get('last_name', '') or ''
        formatted_data['headline'] = raw_data.get('headline', '') or ''
        formatted_data['summary'] = raw_data.get('summary', '') or ''

        # Email - Proxycurl doesn't provide email in standard response
        formatted_data['email'] = ''

        # Format experience/positions
        formatted_data['positions'] = []
        experiences = raw_data.get('experiences', []) or []
        self.logger.debug(f"--- DEBUG: Formatting {len(experiences)} experiences ---")

        for idx, exp in enumerate(experiences):
            try:
                # Safely get company information
                company_name = ''
                if isinstance(exp.get('company'), str):
                    company_name = exp.get('company', '')
                elif isinstance(exp.get('company'), dict):
                    company_name = exp.get('company', {}).get('name', '')

                # Ensure description is a string, not None
                description = exp.get('description', '')
                if description is None:
                    description = ''
                    self.logger.debug(f"Position #{idx + 1}: Description is None, using empty string")

                # Safely handle dates
                starts_at = exp.get('starts_at', {}) or {}
                if not isinstance(starts_at, dict):
                    starts_at = {}

                ends_at = exp.get('ends_at', {})  # Can be None for current positions
                is_current = ends_at is None

                # Create position object with safe values
                position = {
                    'company': {'name': company_name},
                    'title': exp.get('title', '') or '',
                    'summary': description,
                    'startDate': {
                        'month': self._extract_month(starts_at.get('day', '')),
                        'year': starts_at.get('year', '') or ''
                    },
                    'current': is_current
                }

                # Add end date if not current position and ends_at exists
                if not is_current and ends_at:
                    if not isinstance(ends_at, dict):
                        ends_at = {}

                    position['endDate'] = {
                        'month': self._extract_month(ends_at.get('day', '')),
                        'year': ends_at.get('year', '') or ''
                    }

                self.logger.debug(f"Position #{idx + 1}: {position['title']} at {position['company']['name']}, " +
                                  f"Start: {position['startDate']['year']}, Current: {position['current']}")

                formatted_data['positions'].append(position)
            except Exception as e:
                self.logger.error(f"Error formatting position #{idx + 1}: {str(e)}")
                # Continue with next position instead of failing completely

        # Format education
        formatted_data['education'] = []
        education_entries = raw_data.get('education', []) or []
        self.logger.debug(f"--- DEBUG: Formatting {len(education_entries)} education entries ---")

        for idx, edu in enumerate(education_entries):
            try:
                # Safely get education fields
                starts_at = edu.get('starts_at', {}) or {}
                if not isinstance(starts_at, dict):
                    starts_at = {}

                ends_at = edu.get('ends_at')  # Can be None for current education

                # Create education object with safe values
                education = {
                    'schoolName': edu.get('school', '') or '',
                    'degree': edu.get('degree_name', '') or '',
                    'fieldOfStudy': edu.get('field_of_study', '') or '',
                    'startDate': {'year': starts_at.get('year', '') or ''},
                }

                # Add end date if available and valid
                if ends_at and isinstance(ends_at, dict):
                    education['endDate'] = {'year': ends_at.get('year', '') or ''}

                self.logger.debug(
                    f"Education #{idx + 1}: {education['degree']} in {education['fieldOfStudy']} at {education['schoolName']}, " +
                    f"Start: {education['startDate']['year']}, End: {education.get('endDate', {}).get('year', 'Current')}")

                formatted_data['education'].append(education)
            except Exception as e:
                self.logger.error(f"Error formatting education #{idx + 1}: {str(e)}")
                # Continue with next education instead of failing completely

        # Format skills
        formatted_data['skills'] = []
        skills = raw_data.get('skills', []) or []
        self.logger.debug(f"--- DEBUG: Formatting {len(skills)} skills ---")

        for idx, skill in enumerate(skills):
            try:
                # Handle both string skills and object skills
                skill_name = ''
                if isinstance(skill, str):
                    skill_name = skill
                elif isinstance(skill, dict):
                    skill_name = skill.get('name', '')

                if skill_name:  # Only add if we have a valid skill name
                    formatted_data['skills'].append({'name': skill_name})
                    if idx < 5:  # Log just first 5 skills to avoid overwhelming logs
                        self.logger.debug(f"Skill #{idx + 1}: {skill_name}")
            except Exception as e:
                self.logger.error(f"Error formatting skill #{idx + 1}: {str(e)}")
                # Continue with next skill instead of failing completely

        if len(skills) > 5:
            self.logger.debug(f"... and {len(skills) - 5} more skills")

        # Final check for required fields
        if not formatted_data['firstName'] and not formatted_data['lastName']:
            self.logger.warning("Profile data missing both first and last name")

        # Count of formatted items for verification
        self.logger.debug(f"Formatted data summary: {len(formatted_data['positions'])} positions, "
                          f"{len(formatted_data['education'])} education entries, "
                          f"{len(formatted_data['skills'])} skills")

        return formatted_data

    def _extract_month(self, day_string):
        """Extract month from date string if available"""
        if not day_string:
            return ''
        try:
            # Proxycurl often provides date in format like "2022-01"
            if '-' in day_string:
                return day_string.split('-')[1]
            return ''
        except Exception as e:
            self.logger.debug(f"Error extracting month from {day_string}: {str(e)}")
            return ''